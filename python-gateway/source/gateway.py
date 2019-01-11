import logging
import logging.config
import os
import paho.mqtt.client as mqtt

import influx
from docker_secrets import getDocketSecrets


# Logging setup
logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler('../logs/influx_gateway.log', mode='a', maxBytes=1024*1024*10, backupCount=2)
formatter = logging.Formatter('%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s')
logger.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)

def decodeTopic(topic):
    subtopics = topic.split('/')
    endpoint = subtopics[-1]
    if endpoint == "status":
        version, locationId, deviceId, _ = subtopics
        tags = {"version": version,
            "locationId": locationId,
            "deviceId": deviceId}

    elif endpoint in ["state", "value"]:
        version, locationId, deviceId, sensorId, _ = subtopics
        tags = {"version": version,
            "locationId": locationId,
            "deviceId": deviceId,
            "sensorId": sensorId}
    else:
        raise ValueError("The endpoint: %s is not recognized" % endpoint)

    return tags

# Mqtt callbacks
def onValue(client, userdata, msg):
    # Avoid string values as mathematical operations cant
    # be made afterwards
    value = msg.payload
    try:
        value = float(value)
    except ValueError:
        logger.error('The value received: %s is not valid' % value)
        return

    try:
        tags = decodeTopic(msg.topic)
    except (ValueError, AttributeError):
        logger.error('The topic: %s is malformed. Ignoring data' % msg.topic)
        return

    fields = {"value": value}
    measurement = "sensorsData"
    influxDb.writeData(measurement, tags, fields)

def onState(client, userdata, msg):

    value = msg.payload
    try:
        assert value.lower() in ["true", "false"]
    except (AssertionError, AttributeError):
        logging.error('The value received: %s is not valid' % value)
        return

    try:
        tags = decodeTopic(msg.topic)
    except (ValueError, AttributeError):
        logger.error('The topic: %s is malformed. Ignoring data' % msg.topic)
        return

    state = value.lower()=="true"
    fields = {"state": state}
    measurement = "sensorsData"
    influxDb.writeData(measurement, tags, fields)

def onStatus(client, userdata, msg):

    value = msg.payload
    try:
        assert value.lower() in ["online", "offline"]
    except (AssertionError, AttributeError):
        logging.error('The value received: %s is not valid' % value)
        return

    try:
        tags = decodeTopic(msg.topic)
    except (ValueError, AttributeError):
        logger.error('The topic: %s is malformed. Ignoring data' % msg.topic)
        return

    status = value.lower()=="online"
    logger.info("Saving status: %s from the topic: %s" % (status, msg.topic))
    fields = {"status": status}
    measurement = "sensorsData"
    influxDb.writeData(measurement, tags, fields)


def onMessage(client, userdata, msg):
    logger.info('Received data from the topic: %s' % msg.topic)

logger.info("Starting...")

# Influx databse setup
influxDb = influx.InfluxClient('influxdb', database=os.environ['INFLUXDB_DB'], username='', password='')

# MQTT constants
version = 'v1'
topicHeader= "{version}/+/+/".format(version=version)
valuesTopic = topicHeader + "+/value"
stateTopic = topicHeader + "+/state"
statusTopic = topicHeader + "status"

# Setup MQTT client
mqttclient = mqtt.Client()
token = getDocketSecrets('mqtt_token')
mqttclient.username_pw_set(token, "_")

def onConnect(self, mosq, obj, rc):
    # Setup subscriptions
    mqttclient.subscribe(valuesTopic)
    mqttclient.subscribe("#")
    mqttclient.message_callback_add(valuesTopic, onValue)
    mqttclient.message_callback_add(stateTopic, onState)
    mqttclient.message_callback_add(statusTopic, onStatus)
    
mqttclient.on_connect = onConnect

# Connect
mqttclient.connect('mosquitto')
mqttclient.loop_forever(retry_first_connection=True)

influxDb.close()

logger.info("Exiting...")