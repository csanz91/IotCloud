import logging
import logging.config
import time
import datetime


logger = logging.getLogger()


def getTags(topic):
    subtopics = topic.split("/")
    return {
        "locationId": subtopics[1],
        "deviceId": subtopics[2],
        "sensorId": subtopics[3],
        "endpoint": subtopics[-1],
    }


def decodeBoolean(value: bytes):# -> bool | Any:
    decoded_value = value.decode()
    assert decoded_value.lower() in ["true", "false"]
    state = decoded_value.lower() == "true"
    return state


def decodeStatus(value: bytes):
    decoded_value = value.decode().strip()
    # handle repr wrapper like b'offline'
    if decoded_value.startswith("b'") and decoded_value.endswith("'"):
        decoded_value = decoded_value[2:-1]
    assert decoded_value.lower() in ["online", "offline"]
    status = decoded_value.lower() == "online"
    return status


def notIsNaN(num):
    assert num == num


def parseFloat(value: bytes):
    parsedFloat = float(value)
    notIsNaN(parsedFloat)
    return parsedFloat


def retryFunc(func):
    def wrapper(*args, **kwargs):

        maxRetries = 10
        numRetries = 1

        while True:
            try:
                return func(*args, **kwargs)
            except:
                logger.error(
                    "%s: Unable the complete the task. Retries %s/%s."
                    % (func.__name__, numRetries, maxRetries)
                )

            if numRetries >= maxRetries:
                return
            time.sleep(numRetries**2 + 10)
            numRetries += 1

    return wrapper
