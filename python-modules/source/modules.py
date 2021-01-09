import logging
import logging.config
import os
import time
import json
from collections import defaultdict
from threading import Timer, Thread, Lock
import queue
import time

import paho.mqtt.client as mqtt
from docker_secrets import getDocketSecrets
import thermostat_logic
import switch_logic
import toogle_logic
import iotcloud_api
import utils
import location_status

# Logging setup
logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler(
    "../logs/modules.log", mode="a", maxBytes=1024 * 1024 * 10, backupCount=2
)
formatter = logging.Formatter(
    "%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s"
)
logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

####################################
# Helper classes
####################################
class Device:
    def __init__(self):
        self.sensors = defaultdict(Sensor)
        self.status = False


class Value:
    def __init__(self, value):
        self.value = value
        self.timestamp = int(time.time())


class Sensor:
    def __init__(self):
        self.state = False
        self.instance = None
        self.metadata = None
        self.postalCode = None
        self.timeZone = None
        self.aux = {}


####################################
# Helper functions
####################################
def calculateDeviceHash(topic):
    """ Calculate the device hash from the topic
    """
    subtopics = topic.split("/")
    deviceHash = "|".join(subtopics[0:3])
    return deviceHash


def getTags(topic):
    subtopics = topic.split("/")
    tags = {
        "locationId": subtopics[1],
        "deviceId": subtopics[2],
        "sensorId": subtopics[3],
        "endpoint": subtopics[-1],
    }
    return tags


def addToQueueDelayed(queue, items, delay):
    time.sleep(delay)
    logger.info(
        f"Element has been put back into the queue after {delay} seconds",
        extra={"area": "main"},
    )
    queue.put(items)


####################################
# Global variables
####################################

# This variables keeps a snapshot of the current state of all the things
# of the platform
locationsStatus = defaultdict(location_status.LocationStatus)
devices = defaultdict(Device)
values = defaultdict(Value)
deviceslock = Lock()
locationsStatuslock = Lock()

modules = {
    "switch": switch_logic.Switch,
    "thermostat": thermostat_logic.Thermostat,
    "Toogle": toogle_logic.Toogle,
}

# Keep track of all the subscriptions. In case of reconnection they
# will be necessary to restore the subscriptions.
# I do not trust the clean_session=False because it does not
# guarantee that all the subscriptions will be restored, this wrong
# behaviour has been proved by stoping the broker and restart it again
subscriptionsList = []

# Stores the list of threads started
threads = []

# Maximum number of retries if a network depending function fails
maxRetries = 5

# Configure the number of workers
onStatusNumWorkerThreads = 3
onStateNumWorkerThreads = 3
onValueNumWorkerThreads = 5
onSensorUpdateNumWorkerThreads = 5
onLocationUpdateNumWorkerThreads = 2
onAuxNumWorkerThreads = 5

####################################
# Status message processing
####################################
statusQueue = queue.Queue()


def statusWorker():
    while True:
        item = statusQueue.get()
        if item is None:
            break
        onStatusWork(item)
        statusQueue.task_done()


def onStatusWork(msg):
    try:
        deviceHash = calculateDeviceHash(msg.topic)
        deviceStatus = utils.decodeStatus(msg.payload)
        with deviceslock:
            devices[deviceHash].status = deviceStatus

        # Save the device status
        tags = getTags(msg.topic)
        locationId = tags["locationId"]
        with locationsStatuslock:
            locationsStatus[locationId].setDeviceStatus(deviceHash, deviceStatus)

    except:
        logger.error(
            f"onStatus message failed. message: {msg.payload}. Exception: ",
            exc_info=True,
            extra={"area": "status"},
        )


for i in range(onStatusNumWorkerThreads):
    t = Thread(target=statusWorker)
    t.start()
    threads.append(t)


####################################
# State message processing
####################################
stateQueue = queue.Queue()


def stateWorker():
    while True:
        item = stateQueue.get()
        if item is None:

            break
        onStateWork(item)
        stateQueue.task_done()


def onStateWork(msg):
    try:
        deviceHash = calculateDeviceHash(msg.topic)
        sensorId = getTags(msg.topic)["sensorId"]
        with deviceslock:
            devices[deviceHash].sensors[sensorId].state = utils.decodeBoolean(
                msg.payload
            )
    except:
        logger.error(
            f"onState message failed. message: {msg.payload}. Exception: ",
            exc_info=True,
            extra={"area": "state"},
        )


for i in range(onStateNumWorkerThreads):
    t = Thread(target=stateWorker)
    t.start()
    threads.append(t)


####################################
# Value message processing
####################################
valueQueue = queue.Queue()


def valueWorker():
    while True:
        item = valueQueue.get()
        if item is None:
            break
        onValueWork(item)
        valueQueue.task_done()


def onValueWork(msg):
    try:
        value = float(msg.payload)
        # Just remember the latest value
        values[msg.topic] = Value(value)
    except ValueError:
        logger.error(f"The value received: {msg.payload} is not valid",)


for i in range(onValueNumWorkerThreads):
    t = Thread(target=valueWorker)
    t.start()
    threads.append(t)


####################################
# Sensor update message processing
####################################
sensorUpdateQueue = queue.Queue()


def sensorUpdateWorker():
    while True:
        items = sensorUpdateQueue.get()
        if items is None:
            break

        item, numRetries = items
        try:
            onSensorUpdateWork(item)
        except:
            numRetries += 1
            if numRetries < maxRetries:
                delay = numRetries ** 2 + 10
                logger.info(
                    f"retrying onSensorUpdateWork {numRetries}/{maxRetries} after {delay} seconds",
                    extra={"area": "sensor"},
                )
                Thread(
                    target=addToQueueDelayed,
                    args=(sensorUpdateQueue, (item, numRetries), delay),
                ).start()

        sensorUpdateQueue.task_done()


def onSensorUpdateWork(msg):
    """The sensor has been updated, retrieve the new data
    """

    try:
        deviceHash = calculateDeviceHash(msg.topic)
        tags = getTags(msg.topic)
        userId = json.loads(msg.payload)
        sensorData = api.getUserSensor(
            userId, tags["locationId"], tags["deviceId"], tags["sensorId"]
        )
        with deviceslock:
            sensor = devices[deviceHash].sensors[tags["sensorId"]]
            sensor.metadata = sensorData["sensorMetadata"]
    except:
        logger.error(
            "Cant retrieve the metadata for the topic: %s" % msg.topic,
            exc_info=True,
            extra={"area": "sensor"},
        )
        raise


for i in range(onSensorUpdateNumWorkerThreads):
    t = Thread(target=sensorUpdateWorker)
    t.start()
    threads.append(t)

####################################
# Location update message processing
####################################
locationUpdateQueue = queue.Queue()


def locationUpdateWorker():
    while True:
        items = locationUpdateQueue.get()
        if items is None:
            break

        item, numRetries = items
        try:
            onLocationUpdateWork(item)
        except:
            numRetries += 1
            if numRetries < maxRetries:
                delay = numRetries ** 2 + 10
                logger.info(
                    f"retrying onLocationUpdateWork {numRetries}/{maxRetries} after {delay} seconds",
                    extra={"area": "location"},
                )
                Thread(
                    target=addToQueueDelayed,
                    args=(locationUpdateQueue, (item, numRetries), delay),
                ).start()

        locationUpdateQueue.task_done()


def onLocationUpdateWork(msg):
    """The location has been updated, retrieve the new data
    """

    try:
        subtopics = msg.topic.split("/")
        locationId = subtopics[1]
        location = api.getLocation(locationId)

        for device in location["devices"]:
            deviceId = device["deviceId"]
            deviceHash = calculateDeviceHash(f"{version}/{locationId}/{deviceId}")

            with deviceslock:
                for sensorId, sensor in devices[deviceHash].sensors.items():
                    # Find the sensor in the list received from the api and update the metadata
                    for apiSensor in device["sensors"]:
                        if apiSensor["sensorId"] == sensorId:
                            sensor.metadata = apiSensor["sensorMetadata"]
                            break

                    # Update the time data from the location
                    sensor.postalCode = location["postalCode"]
                    sensor.timeZone = location["timeZone"]

    except:
        logger.error(
            "Cant retrieve the metadata for the topic: %s" % msg.topic,
            exc_info=True,
            extra={"area": "location"},
        )
        raise


for i in range(onLocationUpdateNumWorkerThreads):
    t = Thread(target=locationUpdateWorker)
    t.start()
    threads.append(t)

####################################
# Aux update message processing
####################################
auxQueue = queue.Queue()


def auxWorker():
    while True:
        items = auxQueue.get()
        if items is None:
            break
        item, numRetries = items
        try:
            onAuxWork(*item)
        except:
            logger.error(
                "onAux message failed. Exception: ",
                exc_info=True,
                extra={"area": "aux"},
            )
            numRetries += 1
            if numRetries < maxRetries:
                delay = numRetries ** 2 + 10
                logger.info(
                    f"retrying onAux {numRetries}/{maxRetries} after {delay} seconds",
                    extra={"area": "aux"},
                )
                Thread(
                    target=addToQueueDelayed, args=(auxQueue, (item, numRetries), delay)
                ).start()

        auxQueue.task_done()


def onAuxWork(client, msg):

    deviceHash = calculateDeviceHash(msg.topic)
    tags = getTags(msg.topic)

    # New module. Create the instance and get the metadata from the api
    if tags["endpoint"] in modules.keys():
        with deviceslock:
            # Create instance if it does not exist
            if not devices[deviceHash].sensors[tags["sensorId"]].instance:
                devices[deviceHash].sensors[tags["sensorId"]].instance = modules[
                    tags["endpoint"]
                ](tags, client, subscriptionsList)
            # Retrieve data from the api
            sensorData = api.getSensor(
                tags["locationId"], tags["deviceId"], tags["sensorId"]
            )
            if not sensorData:
                return

            sensor = devices[deviceHash].sensors[tags["sensorId"]]
            sensor.metadata = sensorData["sensorMetadata"]
            sensor.postalCode = sensorData["postalCode"]
            sensor.timeZone = sensorData["timeZone"]

    # Add the value received to the aux dict
    else:
        with deviceslock:
            devices[deviceHash].sensors[tags["sensorId"]].aux[
                tags["endpoint"]
            ] = msg.payload


for i in range(onAuxNumWorkerThreads):
    t = Thread(target=auxWorker)
    t.start()
    threads.append(t)


# Mqtt callbacks
def onStatus(client, userdata, msg):
    statusQueue.put(msg)


def onState(client, userdata, msg):
    stateQueue.put(msg)


def onValue(client, userdata, msg):
    valueQueue.put(msg)


def onSensorUpdated(client, userdata, msg):
    sensorUpdateQueue.put((msg, numRetries := 0))


def onLocationUpdated(client, userdata, msg):
    locationUpdateQueue.put((msg, numRetries := 0))


def onAux(client, userdata, msg):
    auxQueue.put(((client, msg), numRetries := 0))


logger.info("Starting...",)

# IotHub api setup
api = iotcloud_api.IotCloudApi()

# MQTT constants
version = "v1"
topicHeader = f"{version}/+/+/"
statusTopic = topicHeader + "status"
valuesTopic = topicHeader + "+/value"
stateTopic = topicHeader + "+/state"
sensorUpdateTopic = topicHeader + "+/updatedSensor"
locationUpdatedTopic = f"{version}/+/updatedLocation"
auxTopic = topicHeader + "+/aux/+"

# Setup MQTT client
mqttclient = mqtt.Client()
token = getDocketSecrets("mqtt_token")
mqttclient.username_pw_set(token, "_")


def onConnect(self, mosq, obj, rc):
    logger.info("connected",)
    # Setup subscriptions
    mqttclient.subscribe(auxTopic)
    mqttclient.subscribe(statusTopic)
    mqttclient.subscribe(locationUpdatedTopic)

    # Restore the subscriptions
    for subscription in subscriptionsList:
        mqttclient.subscribe(subscription)

    mqttclient.message_callback_add(statusTopic, onStatus)
    mqttclient.message_callback_add(valuesTopic, onValue)
    mqttclient.message_callback_add(stateTopic, onState)
    mqttclient.message_callback_add(sensorUpdateTopic, onSensorUpdated)
    mqttclient.message_callback_add(locationUpdatedTopic, onLocationUpdated)
    mqttclient.message_callback_add(auxTopic, onAux)


mqttclient.on_connect = onConnect

# Connect
mqttclient.connect("mosquitto")
mqttclient.loop_start()

while True:

    with deviceslock:
        for device in devices.values():
            # Only run the sensors that are online
            if device.status:
                for sensor in device.sensors.values():
                    # The instance needs to be initialized
                    if sensor.instance:
                        # Pass all the states to the instance
                        sensor.instance.state = sensor.state
                        if sensor.metadata != sensor.instance.metadata:
                            sensor.instance.updateSettings(mqttclient, sensor.metadata)
                        if sensor.aux != sensor.instance.aux:
                            sensor.instance.updateAux(mqttclient, sensor.aux)
                        if sensor.postalCode != sensor.instance.postalCode:
                            sensor.instance.updatePostalCode(sensor.postalCode)
                        if sensor.timeZone != sensor.instance.timeZone:
                            sensor.instance.updateTimeZone(sensor.timeZone)
                        # Run the engine
                        sensor.instance.engine(mqttclient, values)

    with locationsStatuslock:
        for locationId, locationStatus in locationsStatus.items():
            locationStatus.checkLocationStatus(api, locationId)

    time.sleep(1.0)


mqttclient.loop_stop()
# Block until all tasks are done
statusQueue.join()
stateQueue.join()
valueQueue.join()
sensorUpdateQueue.join()
auxQueue.join()

# Stop workers
for i in range(onStatusNumWorkerThreads):
    statusQueue.put(None)

for i in range(onStateNumWorkerThreads):
    stateQueue.put(None)

for i in range(onValueNumWorkerThreads):
    valueQueue.put(None)

for i in range(onSensorUpdateNumWorkerThreads):
    sensorUpdateQueue.put(None)

for i in range(onAuxNumWorkerThreads):
    auxQueue.put(None)

for t in threads:
    t.join()

logger.info("Exiting...",)

