import logging
import logging.config
import time
import datetime
from dateutil import tz

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

def getLocalTime(timeZoneId):
    localZone = tz.gettz(timeZoneId)
    now = datetime.datetime.now(tz=localZone)
    return now

def getCurrentMinute(timeZoneId):
    now = getLocalTime(timeZoneId)
    currentMinute = now.hour * 60 + now.minute
    return currentMinute

def getMinutesConverted(minutes, timeZoneId):
    localZone = tz.gettz(timeZoneId)
    now = datetime.datetime.now(tz=tz.UTC)
    hour = int(minutes / 60)
    minute = minutes % 60
    now = now.replace(hour=hour, minute=minute)
    now = now.astimezone(tz=localZone)
    minutesConverted = now.hour * 60 + now.minute
    return minutesConverted
