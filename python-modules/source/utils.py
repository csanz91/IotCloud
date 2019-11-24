import logging
import logging.config
import time

logger = logging.getLogger()

def decodeBoolean(value):
    value = value.decode()
    assert value.lower() in ["true", "false"]
    state = value.lower()=="true"
    return state

def decodeStatus(value):
    value = value.decode()
    assert value.lower() in ["online", "offline"]
    status = value.lower()=="online"
    return status

def pushValue(mqttClient, tags, endpoint, value, retain=False):
    try:
        topic = "v1/{locationId}/{deviceId}/{sensorId}/aux/{endpoint}".format(locationId=tags["locationId"],
                                                                              deviceId=tags["deviceId"],
                                                                              sensorId=tags["sensorId"],
                                                                              endpoint=endpoint)
        mqttClient.publish(topic, value, retain=retain)
    except:
        logger.error("Cant publish the value: %s in the endpoint: %s" % (value, endpoint))

def retryFunc(func):
    def wrapper(*args, **kwargs):
    
        maxRetries = 10
        numRetries = 1

        while True:
            try:
                result = func(*args, **kwargs)
                return result
            except:
                logger.error('%s: Unable the complete the task. Retries %s/%s.' % (func.__name__, numRetries, maxRetries))

            if numRetries >= maxRetries:
                return result
            time.sleep(numRetries**2+10)
            numRetries += 1

    return wrapper