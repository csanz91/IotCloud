import logging
import logging.config
import os
from collections import defaultdict
from threading import Timer, Thread
import queue
import time

import paho.mqtt.client as mqtt
import influx
from docker_secrets import getDocketSecrets
import utils
import thermostat_gw
import totalizer_gw

# Logging setup
logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler(
    "../logs/influx_gateway.log", mode="a", maxBytes=1024 * 1024 * 10, backupCount=2
)
formatter = logging.Formatter(
    "%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s"
)
logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

####################################
# Global variables
####################################

# Stores the list of threads started
threads = []

# Maximum number of retries if a network depending function fails
maxRetries = 5

# Configure the number of workers
onStatusNumWorkerThreads = 2
onStateNumWorkerThreads = 2
onToogleNumWorkerThreads = 2
onValueNumWorkerThreads = 10
onIPNumWorkerThreads = 2

####################################
# Status message processing
####################################
statusQueue = queue.Queue()


def statusWorker():
    while True:
        item = statusQueue.get()
        if item is None:
            statusQueue.task_done()
            break
        onStatusWork(item)
        statusQueue.task_done()


def onStatusWork(msg):
    try:
        msg.payload = msg.payload.decode("utf-8")
        status = utils.decodeStatus(msg.payload)
        tags = utils.getTags(msg.topic)
    except:
        logger.error(
            f'The message: "{msg.payload}" cannot be processed. Topic: "{msg.topic}" is malformed. Ignoring data',
            extra={"area": "status"},
        )
        return

    try:
        fields = {"status": status}
        tagsToSave = ["locationId", "deviceId"]
        measurement = "sensorsData"
        influxDb.writeData(
            measurement,
            utils.selectTags(tagsToSave, tags),
            fields,
            retentionPolicy="3years",
        )
    except:
        logger.error(
            f"onStatusWork message failed. message: {msg.payload}. Exception: ",
            exc_info=True,
            extra={"area": "status"},
        )


####################################
# State message processing
####################################
stateQueue = queue.Queue()


def stateWorker():
    while True:
        item = stateQueue.get()
        if item is None:
            stateQueue.task_done()
            break
        onStateWork(item)
        stateQueue.task_done()


def onStateWork(msg):

    try:
        msg.payload = msg.payload.decode("utf-8")
        state = utils.decodeBoolean(msg.payload)
        tags = utils.getTags(msg.topic)
    except:
        logger.error(
            f'The message: "{msg.payload}" cannot be processed. Topic: "{msg.topic}" is malformed. Ignoring data',
            extra={"area": "state"},
        )
        return

    try:
        fields = {"state": state}
        tagsToSave = ["locationId", "sensorId"]
        measurement = "sensorsData"
        influxDb.writeData(
            measurement,
            utils.selectTags(tagsToSave, tags),
            fields,
            retentionPolicy="3years",
        )
    except:
        logger.error(
            f"onStateWork message failed. message: {msg.payload}. Exception: ",
            exc_info=True,
            extra={"area": "state"},
        )


####################################
# Toogle message processing
####################################
toogleQueue = queue.Queue()


def toogleWorker():
    while True:
        item = toogleQueue.get()
        if item is None:
            toogleQueue.task_done()
            break
        onToogleWork(item)
        toogleQueue.task_done()


def onToogleWork(msg):

    try:
        msg.payload = msg.payload.decode("utf-8")
        toogle = msg.payload
        tags = utils.getTags(msg.topic)
    except:
        logger.error(
            f'The message: "{msg.payload}" cannot be processed. Topic: "{msg.topic}" is malformed. Ignoring data',
            extra={"area": "toogle"},
        )
        return

    try:
        fields = {"setToogle": toogle}
        tagsToSave = ["locationId", "sensorId"]
        measurement = "sensorsData"
        influxDb.writeData(
            measurement,
            utils.selectTags(tagsToSave, tags),
            fields,
            retentionPolicy="3years",
        )
    except:
        logger.error(
            f"onToogleWork message failed. message: {msg.payload}. Exception: ",
            exc_info=True,
            extra={"area": "toogle"},
        )


####################################
# Value message processing
####################################
valueQueue = queue.Queue()


def valueWorker():
    while True:
        item = valueQueue.get()
        if item is None:
            valueQueue.task_done()
            break
        onValueWork(item)
        valueQueue.task_done()


def onValueWork(msg):
    # Avoid string values as mathematical operations cant
    # be made afterwards
    try:
        msg.payload = msg.payload.decode("utf-8")
        value = utils.parseFloat(msg.payload)
        tags = utils.getTags(msg.topic)
    except:
        logger.error(
            f'The message: "{msg.payload}" cannot be processed. Topic: "{msg.topic}" is malformed. Ignoring data',
            extra={"area": "value"},
        )
        return

    try:
        fields = {"value": value}
        tagsToSave = ["locationId", "sensorId"]
        measurement = "sensorsData"
        influxDb.writeData(
            measurement,
            utils.selectTags(tagsToSave, tags),
            fields,
            retentionPolicy="raw",
        )

    except:
        logger.error(
            f"onValueWork message failed. message: {msg.payload}. Exception: ",
            exc_info=True,
            extra={"area": "value"},
        )


####################################
# IP message processing
####################################
IPQueue = queue.Queue()


def IPWorker():
    while True:
        item = IPQueue.get()
        if item is None:
            IPQueue.task_done()
            break
        onIPWork(item)
        IPQueue.task_done()


def onIPWork(msg):
    try:
        msg.payload = msg.payload.decode("utf-8")
        IP = msg.payload
        assert IP
        tags = utils.getTags(msg.topic)
    except:
        logger.error(
            f'The message: "{msg.payload}" cannot be processed. Topic: "{msg.topic}" is malformed. Ignoring data',
            extra={"area": "IP"},
        )
        return

    try:
        fields = {"IP": IP}
        tagsToSave = ["locationId", "deviceId"]
        measurement = "devicesIPs"
        influxDb.writeData(
            measurement,
            utils.selectTags(tagsToSave, tags),
            fields,
            retentionPolicy="raw",
        )
    except:
        logger.error(
            f"onIPWork message failed. message: {msg.payload}. Exception: ",
            exc_info=True,
            extra={"area": "IP"},
        )


def init(influxDb):
    """
    From the docs: If you attempt to create a retention policy identical to one that 
        already exists, InfluxDB does not return an error. If you attempt to create a 
        retention policy with the same name as an existing retention policy but with 
        differing attributes, InfluxDB returns an error.
    -i.e. If we want to edit some of the following values, do it in the Influx cli.

    The values received will be stored for 45 days at their original resolution, 
        and they are aggregated every:
            -hour and stored for 1 year,
            -day and stored for 3 years,
    """
    # Setup the retention policies
    influxDb.client.create_retention_policy("raw", "45d", 1, default=True)
    influxDb.client.create_retention_policy("1year", "365d", 1)
    influxDb.client.create_retention_policy("3years", "1080d", 1)

    influxDb.client.query(
        f""" DROP CONTINUOUS QUERY "sensorsData_1h" ON {os.environ['INFLUXDB_DB']};"""
    )
    influxDb.client.query(
        f""" CREATE CONTINUOUS QUERY "sensorsData_1h" ON {os.environ['INFLUXDB_DB']} BEGIN
                                SELECT mean("value") AS "value",
                                       max("value") AS "max_value",
                                       min("value") AS "min_value"
                                INTO "1year"."downsampled_sensorsData_1h"
                                FROM "raw"."sensorsData"
                                GROUP BY time(1h), *
                              END """
    )

    influxDb.client.query(
        f""" DROP CONTINUOUS QUERY "sensorsData_1d" ON {os.environ['INFLUXDB_DB']};"""
    )
    influxDb.client.query(
        f""" CREATE CONTINUOUS QUERY "sensorsData_1d" ON {os.environ['INFLUXDB_DB']} BEGIN
                                SELECT mean("value") AS "value",
                                       max("max_value") AS "max_value",
                                       min("min_value") AS "min_value"
                                INTO "3years"."downsampled_sensorsData_1d"
                                FROM "1year"."downsampled_sensorsData_1h"
                                GROUP BY time(1d), *
                              END """
    )


# Mqtt callbacks
def onStatus(client, userdata, msg):
    statusQueue.put(msg)


def onState(client, userdata, msg):
    stateQueue.put(msg)


def onToogle(client, userdata, msg):
    toogleQueue.put(msg)


def onValue(client, userdata, msg):
    valueQueue.put(msg)


def onIP(client, userdata, msg):
    IPQueue.put(msg)


def startThreads():
    for i in range(onStatusNumWorkerThreads):
        t = Thread(target=statusWorker)
        t.name = "Status%d" % i
        t.start()
        threads.append(t)

    for i in range(onStateNumWorkerThreads):
        t = Thread(target=stateWorker)
        t.name = "State%d" % i
        t.start()
        threads.append(t)

    for i in range(onToogleNumWorkerThreads):
        t = Thread(target=toogleWorker)
        t.name = "Toogle%d" % i
        t.start()
        threads.append(t)

    for i in range(onValueNumWorkerThreads):
        t = Thread(target=valueWorker)
        t.name = "Value%d" % i
        t.start()
        threads.append(t)

    for i in range(onIPNumWorkerThreads):
        t = Thread(target=IPWorker)
        t.name = "IP%d" % i
        t.start()
        threads.append(t)


def stopThreads():
    for _ in range(onStatusNumWorkerThreads):
        statusQueue.put(None)

    for _ in range(onStateNumWorkerThreads):
        stateQueue.put(None)

    for _ in range(onToogleNumWorkerThreads):
        toogleQueue.put(None)

    for _ in range(onValueNumWorkerThreads):
        valueQueue.put(None)

    for _ in range(onIPNumWorkerThreads):
        IPQueue.put(None)

    for t in threads:
        t.join()


logger.info("Starting...",)

# Influx databse setup
influxDb = influx.InfluxClient(
    "influxdb", database=os.environ["INFLUXDB_DB"], username="", password=""
)

# Initialize the database

init(influxDb)

# MQTT constants
version = "v1"
topicHeader = "{version}/+/+/".format(version=version)
valuesTopic = topicHeader + "+/value"
stateTopic = topicHeader + "+/state"
toogleTopic = topicHeader + "+/aux/setToogle"
statusTopic = topicHeader + "status"
IPTopic = topicHeader + "ip"

# Setup MQTT client
mqttclient = mqtt.Client()
token = getDocketSecrets("mqtt_token")
mqttclient.username_pw_set(token, "_")


def onConnect(self, mosq, obj, rc):
    # Setup subscriptions
    mqttclient.subscribe(valuesTopic)
    mqttclient.message_callback_add(valuesTopic, onValue)

    mqttclient.subscribe(stateTopic)
    mqttclient.message_callback_add(stateTopic, onState)

    mqttclient.subscribe(toogleTopic)
    mqttclient.message_callback_add(toogleTopic, onToogle)

    mqttclient.subscribe(statusTopic)
    mqttclient.message_callback_add(statusTopic, onStatus)

    mqttclient.subscribe(IPTopic)
    mqttclient.message_callback_add(IPTopic, onIP)

    thermostat_gw.onConnect(mqttclient, influxDb)
    totalizer_gw.onConnect(mqttclient, influxDb)


mqttclient.on_connect = onConnect

# Connect
mqttclient.connect("mosquitto")

startThreads()
totalizer_gw.startThreads()
thermostat_gw.startThreads()

mqttclient.loop_forever(retry_first_connection=True)

influxDb.close()
stopThreads()
totalizer_gw.stopThreads()
thermostat_gw.stopThreads()

logger.info("Exiting...")
