import logging
import logging.config
import os
import time
import json
from collections import defaultdict
from threading import Timer, Thread
import queue
import time


import paho.mqtt.client as mqtt
from docker_secrets import getDocketSecrets
import thermostat_logic
import switch_logic
import toogle_logic
import iothub_api
import utils
import location_status

# Logging setup
logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler('../logs/modules.log', mode='a', maxBytes=1024*1024*10, backupCount=2)
formatter = logging.Formatter('%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s')
logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

####################################
# Helper classes
####################################
class Device():
    def __init__(self):
        self.sensors = defaultdict(Sensor)
        self.status = False


class Value():
    def __init__(self, value):
        self.value = value
        self.timestamp = int(time.time())


class Sensor():
    def __init__(self):
        self.state = False
        self.instance = None
        self.metadata = None
        self.aux = {}

####################################
# Helper functions
####################################
def calculateDeviceHash(topic):
    """ Calculate the device hash from the topic
    """
    subtopics = topic.split('/')
    deviceHash = "|".join(subtopics[0:3])
    return deviceHash


def getTags(topic):
    subtopics = topic.split("/")
    tags = {"locationId": subtopics[1],
            "deviceId": subtopics[2],
            "sensorId": subtopics[3],
            "endpoint": subtopics[-1]
            }
    return tags

def addToQueueDelayed(queue, items, delay):
    time.sleep(delay)
    logger.info(f"Element has been put back into the queue after {delay} seconds")
    queue.put(items)

####################################
# Global variables
####################################

# This variables keeps a snapshot of the current state of all the things 
# of the platform
locationsStatus = defaultdict(location_status.LocationStatus)
devices = defaultdict(Device)
values = defaultdict(Value)

modules = {"switch": switch_logic.Switch,
           "thermostat": thermostat_logic.Thermostat,
           "Toogle": toogle_logic.Toogle}

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
        devices[deviceHash].status = deviceStatus

        # Save the device status
        tags = getTags(msg.topic)
        locationId = tags["locationId"]
        locationsStatus[locationId].setDeviceStatus(deviceHash, deviceStatus)

    except:
        logger.error(f'onStatus message failed. message: {msg.payload}. Exception: ', exc_info=True)

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
        devices[deviceHash].sensors[sensorId].state = utils.decodeBoolean(msg.payload)
    except:
        logger.error(f'onState message failed. message: {msg.payload}. Exception: ', exc_info=True)

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
        logger.error('The value received: %s is not valid' % value)

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
                delay = numRetries**2+10
                logger.info(f'retrying onSensorUpdateWork {numRetries}/{maxRetries} after {delay} seconds')
                Thread(target=addToQueueDelayed, args=(auxQueue, (item, numRetries), delay)).start()
        
        sensorUpdateQueue.task_done()

def onSensorUpdateWork(msg):
    """The sensor has been updated, retrieve the new data
    """

    try:
        deviceHash = calculateDeviceHash(msg.topic)
        tags = getTags(msg.topic)
        userId = json.loads(msg.payload)
        sensorData = api.getUserSensor(userId, tags["locationId"], tags["deviceId"], tags["sensorId"])

        devices[deviceHash].sensors[tags["sensorId"]].metadata = sensorData['sensorMetadata']
    except:
        logger.error("Cant retrieve the metadata for the topic: %s" % msg.topic, exc_info=True)
        raise

for i in range(onSensorUpdateNumWorkerThreads):
    t = Thread(target=sensorUpdateWorker)
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
            logger.error('onAux message failed. Exception: ', exc_info=True)
            numRetries += 1
            if numRetries < maxRetries:
                delay = numRetries**2+10
                logger.info(f'retrying onAux {numRetries}/{maxRetries} after {delay} seconds')
                Thread(target=addToQueueDelayed, args=(auxQueue, (item, numRetries), delay)).start()

        auxQueue.task_done()

def onAuxWork(client, msg):

    deviceHash = calculateDeviceHash(msg.topic)
    tags = getTags(msg.topic)

    # New module. Create the instance and get the metadata from the api
    if tags["endpoint"] in modules.keys():
        if not devices[deviceHash].sensors[tags["sensorId"]].instance:
            devices[deviceHash].sensors[tags["sensorId"]].instance = modules[tags["endpoint"]](tags, client, subscriptionsList)
            sensorData = api.getSensor(tags["locationId"], tags["deviceId"], tags["sensorId"])
            if not sensorData:
                return
            devices[deviceHash].sensors[tags["sensorId"]].metadata = sensorData['sensorMetadata']

    # Add the value received to the aux dict
    else:
        devices[deviceHash].sensors[tags["sensorId"]].aux[tags["endpoint"]] = msg.payload

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
    sensorUpdateQueue.put((msg, numRetries:=0))

def onAux(client, userdata, msg):
    auxQueue.put(((client,msg), numRetries:=0))


logger.info("Starting...")

# IotHub api setup
api = iothub_api.IothubApi()

# MQTT constants
version = 'v1'
topicHeader = f"{version}/+/+/"
statusTopic = topicHeader + "status"
valuesTopic = topicHeader + "+/value"
stateTopic = topicHeader + "+/state"
sensorUpdateTopic = topicHeader + "+/updatedSensor"
auxTopic = topicHeader + "+/aux/+"

# Setup MQTT client
mqttclient = mqtt.Client()
token = getDocketSecrets('mqtt_token')
mqttclient.username_pw_set(token, "_")


def run(mqttClient):
    for device in devices.values():
        # Only run the sensors that are online
        if device.status:
            for sensor in device.sensors.values():
                # The instance needs to be initialized
                if sensor.instance:
                    # Pass all the states to the instance
                    sensor.instance.state = sensor.state
                    if sensor.metadata != sensor.instance.metadata:
                        sensor.instance.updateSettings(mqttClient, sensor.metadata)
                    if sensor.aux != sensor.instance.aux:
                        sensor.instance.updateAux(mqttClient, sensor.aux)
                    # Run the engine
                    sensor.instance.engine(mqttClient, values)

    for locationId, locationStatus in locationsStatus.items():
        locationStatus.checkLocationStatus(api, locationId)

    Timer(1.0, run, [mqttClient]).start()


run(mqttclient)


def onConnect(self, mosq, obj, rc):
    logger.info("connected")
    # Setup subscriptions
    mqttclient.subscribe(auxTopic)
    # Restore the subscriptions
    for subscription in subscriptionsList:
        mqttclient.subscribe(subscription)

    mqttclient.message_callback_add(statusTopic, onStatus)
    mqttclient.message_callback_add(valuesTopic, onValue)
    mqttclient.message_callback_add(stateTopic, onState)
    mqttclient.message_callback_add(sensorUpdateTopic, onSensorUpdated)
    mqttclient.message_callback_add(auxTopic, onAux)


mqttclient.on_connect = onConnect

# Connect
mqttclient.connect('mosquitto')
mqttclient.loop_forever(retry_first_connection=True)

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

logger.info("Exiting...")
