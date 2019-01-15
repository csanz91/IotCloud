import logging
import logging.config

logger = logging.getLogger()

def decodeBoolean(value):
    assert value.lower() in ["true", "false"]
    state = value.lower()=="true"
    return state

def decodeStatus(value):
    assert value.lower() in ["online", "offline"]
    status = value.lower()=="online"
    return status

def pushValue(mqttClient, tags, endpoint, value):
    try:
        topic = "v1/{locationId}/{deviceId}/{sensorId}/aux/{endpoint}".format(locationId=tags["locationId"],
                                                                              deviceId=tags["deviceId"],
                                                                              sensorId=tags["sensorId"],
                                                                              endpoint=endpoint)
        mqttClient.publish(topic, value)
    except:
        logger.error("Cant publish the value: %s in the endpoint: %s" % (value, endpoint))