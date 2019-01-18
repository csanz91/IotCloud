def decodeBoolean(value):
    assert value.lower() in ["true", "false"]
    state = value.lower()=="true"
    return state

def decodeStatus(value):
    assert value.lower() in ["online", "offline"]
    status = value.lower()=="online"
    return status

def decodeTopic(topic):
    subtopics = topic.split('/')
    endpoint = subtopics[-1]
    tags = {"locationId": subtopics[1],
            "deviceId": subtopics[2]}

    if endpoint == "status":
        return tags, endpoint

    tags["sensorId"] = subtopics[3]

    return tags, endpoint

def calculateSensorHash(topic):
    """ Calculate the sensor hash from the topic
    """
    subtopics = topic.split('/')
    sensorHash = "|".join(subtopics[0:4])
    return sensorHash