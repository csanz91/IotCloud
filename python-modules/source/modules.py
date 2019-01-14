import logging
import logging.config
import os
import time
import json
from collections import defaultdict
from threading import Timer

import paho.mqtt.client as mqtt
import gateway
import influx
from docker_secrets import getDocketSecrets
import thermostat_logic
import switch_logic
import iothub_api
import utils

# Logging setup
logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler('../logs/modules.log', mode='a', maxBytes=1024*1024*10, backupCount=2)
formatter = logging.Formatter('%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s')
logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

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

devices = defaultdict(Device)
values = defaultdict(Value)
modules = {"switch": switch_logic.Switch,
           "thermostat": thermostat_logic.Thermostat}

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

# Mqtt callbacks
def onStatus(client, userdata, msg):
    try:
        deviceHash = calculateDeviceHash(msg.topic)
        devices[deviceHash].status = utils.decodeStatus(msg.payload)
    except:
        logger.error('onStatus message failed. Exception: ', exc_info=True)
    
def onState(client, userdata, msg):
    try:
        deviceHash = calculateDeviceHash(msg.topic)
        sensorId = getTags(msg.topic)["sensorId"]
        devices[deviceHash].sensors[sensorId].state = utils.decodeBoolean(msg.payload)
    except:
        logger.error('onState message failed. Exception: ', exc_info=True)

def onValue(client, userdata, msg):
    try:
        value = float(msg.payload)
        values[msg.topic] = Value(value)
    except ValueError:
        logger.error('The value received: %s is not valid' % value)
        return
    
def onSensorUpdated(client, userdata, msg):
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
        return

def onAux(client, userdata, msg):

    try:
        deviceHash = calculateDeviceHash(msg.topic)
        tags = getTags(msg.topic)
    
        # New module. Create the instance and get the metadata from the api
        if tags["endpoint"] in modules.keys():
            if not devices[deviceHash].sensors[tags["sensorId"]].instance:
                devices[deviceHash].sensors[tags["sensorId"]].instance = modules[tags["endpoint"]](tags, client)
                sensorData = api.getSensor(tags["locationId"], tags["deviceId"], tags["sensorId"])
                devices[deviceHash].sensors[tags["sensorId"]].metadata = sensorData['sensorMetadata']

        # Add the value received to the aux dict
        else:
            devices[deviceHash].sensors[tags["sensorId"]].aux[tags["endpoint"]] = msg.payload
    except:
        logger.error('onAux message failed. Exception: ', exc_info=True)

    
logger.info("Starting...")

# Influx databse setup
influxDb = influx.InfluxClient('influxdb', database=os.environ['INFLUXDB_DB'], username='', password='')

# IotHub api setup
api = iothub_api.IothubApi()

# MQTT constants
version = 'v1'
topicHeader = "{version}/+/+/".format(version=version)
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
                    
                    if "ackAlarm" in sensor.aux:
                        logger.info("ackAlarm: %s" % sensor.aux["ackAlarm"])
                    if sensor.aux != sensor.instance.aux:
                        sensor.instance.updateAux(mqttClient, sensor.aux)
                    # Run the engine
                    sensor.instance.engine(mqttClient, influxDb, values)

    Timer(10.0, run, [mqttClient]).start()

run(mqttclient)

def onConnect(self, mosq, obj, rc):
    logger.info("connected")
    # Setup subscriptions
    mqttclient.subscribe(auxTopic)
    mqttclient.message_callback_add(statusTopic, onStatus)
    mqttclient.message_callback_add(valuesTopic, onValue)
    mqttclient.message_callback_add(stateTopic, onState)
    mqttclient.message_callback_add(sensorUpdateTopic, onSensorUpdated)
    mqttclient.message_callback_add(auxTopic, onAux)

mqttclient.on_connect = onConnect

# Connect
mqttclient.connect('mosquitto')
mqttclient.loop_forever(retry_first_connection=True)

influxDb.close()

logger.info("Exiting...")
