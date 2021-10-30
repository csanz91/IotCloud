import time
import logging
import logging.config

# Logging setup
logger = logging.getLogger(__name__)


def decodeBoolean(value):
    assert value.lower() in ["true", "false"]
    state = value.lower() == "true"
    return state


def decodeStatus(value):
    assert value.lower() in ["online", "offline"]
    status = value.lower() == "online"
    return status


def getTags(topic):
    subtopics = topic.split("/")
    return {
        "locationId": subtopics[1],
        "deviceId": subtopics[2],
        "sensorId": subtopics[3],
        "endpoint": subtopics[-1],
    }


def selectTags(selectedTags, tags):
    tagsToSave = {tag: tags[tag] for tag in selectedTags if tag in tags}
    return tagsToSave


def calculateSensorHash(topic):
    """ Calculate the sensor hash from the topic
    """
    subtopics = topic.split("/")
    sensorHash = "|".join(subtopics[0:4])
    return sensorHash


def notIsNaN(num):
    assert num == num


def parseFloat(value):
    parsedFloat = float(value)
    notIsNaN(parsedFloat)
    return parsedFloat


def addToQueueDelayed(queue, items, delay):
    time.sleep(delay)
    logger.info(f"Element has been put back into the queue after {delay} seconds")
    queue.put(items)
