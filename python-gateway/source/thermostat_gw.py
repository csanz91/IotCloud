import logging
import logging.config

import utils

logger = logging.getLogger(__name__)

##################
# Global values
##################
influxDb = None

# MQTT constants
version = 'v1'
topicHeader= "{version}/+/+/+/aux/".format(version=version)
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

def onThermostatValue(client, userdata, msg):
    try:
        value = float(msg.payload)
        tags, endpoint = utils.decodeTopic(msg.topic)
    except:
        logger.error('The message: "%s" cannot be processed. Topic: "%s" is malformed. Ignoring data' % (msg.payload, msg.topic))
        return

    fields = {endpoint: value}
    tagsToSave =  ["locationId", "sensorId"]
    measurement = "thermostatData"
    influxDb.writeData(measurement, utils.selectTags(tagsToSave, tags), fields, retentionPolicy="3years")

def onHeating(client, userdata, msg):
    try:
        heating = utils.decodeBoolean(msg.payload)
        tags, _ = utils.decodeTopic(msg.topic)
    except:
        logger.error('The message: "%s" cannot be processed. Topic: "%s" is malformed. Ignoring data' % (msg.payload, msg.topic))
        return

    fields = {"heating": heating}
    tagsToSave =  ["locationId", "sensorId"]
    measurement = "thermostatData"
    influxDb.writeData(measurement, utils.selectTags(tagsToSave, tags), fields, retentionPolicy="3years")
