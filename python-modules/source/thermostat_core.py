import logging
import logging.config
import os
import time
import json
from threading import Timer

import paho.mqtt.client as mqtt
import gateway
import influx
from docker_secrets import getDocketSecrets
import thermostat_logic
import iothub_api

# Logging setup
logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler('../logs/thermostat.log', mode='a', maxBytes=1024*1024*10, backupCount=2)
formatter = logging.Formatter('%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s')
logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

def decodeBoolean(value):
    assert value.lower() in ["true", "false"]
    state = value.lower()=="true"
    return state

def decodeTopic(topic):
    subtopics = topic.split('/')
    endpoint = subtopics[-1]
    if endpoint == "status":
        version, locationId, deviceId, _ = subtopics
        tags = {"version": version,
            "locationId": locationId,
            "deviceId": deviceId}

    elif endpoint in ["state", "value", "updatedSensor"]:
        version, locationId, deviceId, sensorId, _ = subtopics
        tags = {"version": version,
            "locationId": locationId,
            "deviceId": deviceId,
            "sensorId": sensorId}
    else:
        version, locationId, deviceId, sensorId, aux, _ = subtopics
        if aux != "aux":
            raise ValueError("The endpoint: %s is not recognized" % endpoint)

        tags = {"version": version,
            "locationId": locationId,
            "deviceId": deviceId,
            "sensorId": sensorId,
            "endpoint": endpoint}

    hash = "|".join(tags.values()[0:4])

    return tags, hash

# Mqtt callbacks
def onValue(client, userdata, msg):
    value = msg.payload
    try:
        value = float(value)
    except ValueError:
        logger.error('The value received: %s is not valid' % value)
        return
    thermostat_logic.thermostatsValues[msg.topic] = {"value": value, "timestamp": int(time.time())}


def onState(client, userdata, msg):

    try:
        tags, hash = decodeTopic(msg.topic)
    except (ValueError, AttributeError):
        logger.error('The topic: %s is malformed. Ignoring data' % msg.topic)
        return

    try:
        # Check the value received and save it in their thermostat
        state = decodeBoolean(msg.payload)
        thermostat_logic.thermostats[hash].state = state
    # The thermostat doesnt exists. This should not happen. Behave nice
    except KeyError:
        thermostat_logic.thermostats[hash] = thermostat_logic.Thermostat(tags, client)
        thermostat_logic.thermostats[hash].state = state
    # The value cant be parsed as a float
    except (AssertionError, AttributeError):
        logging.error('The value received: %s is not valid' % msg.payload)


def onSensorUpdated(client, userdata, msg):

    try:
        tags, hash = decodeTopic(msg.topic)
    except (ValueError, AttributeError):
        logger.error('The topic: %s is malformed. Ignoring data' % msg.topic)
        return

    # The sensor has been updated, retrieve the new data

    try:
        userId = json.loads(msg.payload)
        sensorData = api.getSensor(userId, tags['locationId'], tags['deviceId'], tags['sensorId'])
        metadata = sensorData['sensorMetadata']
    except:
        logger.error("Cant retrieve the metadata for the topic: %s" % msg.topic, exc_info=True)
        return
    
    try:
        thermostat_logic.thermostats[hash].updateSettings(client, metadata)
    # The thermostat doesnt exists. This should not happen. Behave nice
    except KeyError:
        thermostat_logic.thermostats[hash] = thermostat_logic.Thermostat(tags, client)
        thermostat_logic.thermostats[hash].updateSettings(client, metadata)
    # The value cant be parsed as a float
    except ValueError:
        logger.warning("Cannot set the metadata: %s for the thermostat: %s" % (msg.payload, msg.topic))

def onAux(client, userdata, msg):

    try:
        tags, hash = decodeTopic(msg.topic)
    except (ValueError, AttributeError):
        logger.error('The topic: %s is malformed. Ignoring data' % msg.topic)
        return

    if tags['endpoint'] == 'thermostat' and hash not in thermostat_logic.thermostats:
        thermostat_logic.thermostats[hash] = thermostat_logic.Thermostat(tags, client)

    elif tags['endpoint'] == 'setpoint':
        try:
            setpoint = float(msg.payload)
            # Save the new setpoint in the database
            gateway.saveSetpoint(influxDb, tags, setpoint)
            thermostat_logic.thermostats[hash].setpoint = setpoint
        # The thermostat doesnt exists. This should not happen. Behave nice
        except KeyError:
            thermostat_logic.thermostats[hash] = thermostat_logic.Thermostat(tags, client)
            thermostat_logic.thermostats[hash].setpoint = setpoint
        # The value cant be parsed as a float
        except ValueError:
            logger.warning("Cannot set the setpoint: %s for the thermostat: %s" % (msg.payload, msg.topic))

    elif tags['endpoint'] == 'ackAlarm':
        try:
            thermostat_logic.thermostats[hash].setAlarm(client, False)
        # The thermostat doesnt exists. This should not happen. Behave nice
        except KeyError:
            thermostat_logic.thermostats[hash] = thermostat_logic.Thermostat(tags, client)
            thermostat_logic.thermostats[hash].setAlarm(client, False)
        # The value cant be parsed as a float
        except (AssertionError, ValueError):
            logger.warning("Cannot ackwnoldge the alarm for the thermostat: %s" % (msg.topic))


    elif tags['endpoint'] == 'heating':
        try:
            heating = decodeBoolean(msg.payload)
            # Save the new heating state in the database
            gateway.saveHeatingState(influxDb, tags, heating)
            thermostat_logic.thermostats[hash].heating = heating
        # The thermostat doesnt exists. This should not happen. Behave nice
        except KeyError:
            thermostat_logic.thermostats[hash] = thermostat_logic.Thermostat(tags, client)
            thermostat_logic.thermostats[hash].heating = heating
        # The value cant be parsed as a float
        except (AssertionError, ValueError):
            logger.warning("Cannot set the heating: %s for the thermostat: %s" % (heating, msg.topic))


logger.info("Starting...")

# Influx databse setup
influxDb = influx.InfluxClient('influxdb', database=os.environ['INFLUXDB_DB'], username='', password='')

# IotHub api setup
api = iothub_api.IothubApi()

# MQTT constants
version = 'v1'
topicHeader = "{version}/+/+/".format(version=version)
valuesTopic = topicHeader + "+/value"
stateTopic = topicHeader + "+/state"
sensorUpdateTopic = topicHeader + "+/updatedSensor"
auxTopic = topicHeader + "+/aux/+"

# Setup MQTT client
mqttclient = mqtt.Client()
token = getDocketSecrets('mqtt_token')
mqttclient.username_pw_set(token, "_")

def processThermostats(mqttClient):
    for thermostat in thermostat_logic.thermostats.values():
        thermostat.engine(mqttClient, influxDb)
    Timer(10.0, processThermostats,[mqttClient]).start()

processThermostats(mqttclient)

def onConnect(self, mosq, obj, rc):
    logger.info("connected")
    # Setup subscriptions
    mqttclient.subscribe(auxTopic)
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
