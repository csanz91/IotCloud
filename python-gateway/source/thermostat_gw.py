import logging
import logging.config
from threading import Timer, Thread
import queue

import utils

logger = logging.getLogger(__name__)

##################
# Global values
##################
influxDb = None

# Stores the list of threads started
threads = []

# Maximum number of retries if a network depending function fails
maxRetries = 5

# Configure the number of workers
onThermostatValueNumWorkerThreads = 3
onHeatingNumWorkerThreads = 3

# MQTT constants
version = 'v1'
topicHeader = "{version}/+/+/+/aux/".format(version=version)
tempReferenceTopic = topicHeader + "tempReference"
heatingTopic = topicHeader + "heating"
setpointTopic = topicHeader + "setpoint"


def onConnect(mqttclient, influxClient):
    global influxDb
    influxDb = influxClient

    mqttclient.subscribe(tempReferenceTopic)
    mqttclient.message_callback_add(tempReferenceTopic, onThermostatValue)

    mqttclient.subscribe(setpointTopic)
    mqttclient.message_callback_add(setpointTopic, onThermostatValue)

    mqttclient.subscribe(heatingTopic)
    mqttclient.message_callback_add(heatingTopic, onHeating)


#############################################
# Thermostat value message processing
#############################################
thermostatValueQueue = queue.Queue()


def thermostatValueWorker():
    while True:
        item = thermostatValueQueue.get()
        if item is None:
            break
        onThermostatValueWork(item)
        thermostatValueQueue.task_done()


def onThermostatValueWork(msg):
    try:
        value = utils.parseFloat(msg.payload)
        tags = utils.selectTags(msg.topic)
    except:
        logger.error(
            f'The message: "{msg.payload}" cannot be processed. Topic: "{msg.topic}" is malformed. Ignoring data')
        return

    try:
        fields = {tags["endpoint"]: value}
        tagsToSave = ["locationId", "sensorId"]
        measurement = "thermostatData"
        influxDb.writeData(measurement, utils.selectTags(
            tagsToSave, tags), fields, retentionPolicy="3years")
    except:
        logger.error(
            f'onThermostatValueWork message failed. message: {msg.payload}. Exception: ', exc_info=True)


for i in range(onThermostatValueNumWorkerThreads):
    t = Thread(target=thermostatValueWorker)
    t.start()
    threads.append(t)

#############################################
# Heating message processing
#############################################
heatingQueue = queue.Queue()


def heatingWorker():
    while True:
        item = heatingQueue.get()
        if item is None:
            break
        onHeatingWork(item)
        heatingQueue.task_done()


def onHeatingWork(msg):
    try:
        heating = utils.decodeBoolean(msg.payload)
        tags = utils.selectTags(msg.topic)
    except:
        logger.error(
            f'The message: "{msg.payload}" cannot be processed. Topic: "{msg.topic}" is malformed. Ignoring data')
        return

    try:
        fields = {"heating": heating}
        tagsToSave = ["locationId", "sensorId"]
        measurement = "thermostatData"
        influxDb.writeData(measurement, utils.selectTags(
            tagsToSave, tags), fields, retentionPolicy="3years")
    except:
        logger.error(
            f'onHeatingWork message failed. message: {msg.payload}. Exception: ', exc_info=True)


for i in range(onHeatingNumWorkerThreads):
    t = Thread(target=heatingWorker)
    t.start()
    threads.append(t)


def onThermostatValue(client, userdata, msg):
    thermostatValueQueue.put(msg)


def onHeating(client, userdata, msg):
    heatingQueue.put(msg)
