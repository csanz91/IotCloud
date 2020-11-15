import logging
import logging.config
import time
import datetime
from dateutil import tz

import schedule
import timer

logger = logging.getLogger()


class Toogle:
    def __init__(self, tags, mqttClient, subscriptionsList):

        # Aux variables
        self.tags = tags
        self.deviceTopicHeader = f"v1/{tags['locationId']}/{tags['deviceId']}/"
        self.topicHeader = self.deviceTopicHeader + tags["sensorId"] + "/"

        # Runtime variables
        self.state = False
        self.schedule = schedule.Schedule(tags["locationId"], self.setState)
        self.metadata = {}
        self.aux = {}
        self.postalCode = None
        self.timeZone = None

        # Subscribe to the relevant topics
        mqttClient.subscribe(self.topicHeader + "updatedSensor")
        subscriptionsList.append(self.topicHeader + "updatedSensor")

    def updateSettings(self, mqttClient, metadata):
        self.metadata = metadata
        try:
            self.schedule.importSchedule(metadata)
            logger.info(
                f"{self.deviceTopicHeader}: schedule updated: {self.schedule.schedule}",
                extra={"area": "toogle"},
            )
        except:
            pass

    def updateAux(self, mqttClient, aux):
        self.aux = aux

    def updatePostalCode(self, postalCode):
        self.postalCode = postalCode

    def updateTimeZone(self, timeZone):
        self.timeZone = timeZone

    def setState(self, mqttClient, state):
        if state:
            action = "up"
        else:
            action = "down"

        mqttClient.publish(
            self.topicHeader + "aux/setToogle", action, qos=1, retain=False
        )

    def engine(self, mqttClient, values):

        # Check the schedule
        self.schedule.runSchedule(mqttClient, self.timeZone)
