import logging
import logging.config
import time
import datetime
from dateutil import tz

import schedule
import timer

logger = logging.getLogger()


class Switch:
    def __init__(self, tags, mqttClient, subscriptionsList):

        # Aux variables
        self.tags = tags
        self.deviceTopicHeader = "v1/{locationId}/{deviceId}/".format(
            locationId=tags["locationId"], deviceId=tags["deviceId"]
        )
        self.topicHeader = self.deviceTopicHeader + tags["sensorId"] + "/"

        # Runtime variables
        self.state = False
        self.schedule = schedule.Schedule(tags["locationId"], self.setState)
        self.timer = timer.Timer(self.setState)
        self.metadata = {}
        self.aux = {}
        self.postalCode = None
        self.timeZone = None

        # Subscribe to the relevant topics
        mqttClient.subscribe(self.topicHeader + "state")
        subscriptionsList.append(self.topicHeader + "state")
        mqttClient.subscribe(self.topicHeader + "updatedSensor")
        subscriptionsList.append(self.topicHeader + "updatedSensor")

    def updateSettings(self, mqttClient, metadata):
        self.metadata = metadata
        try:
            self.schedule.importSchedule(metadata)
            logger.info(
                f"{self.deviceTopicHeader}: schedule updated: {self.schedule.schedule}",
                extra={"area": "switch"},
            )
        except:
            pass

        try:
            self.timer.importSettings(metadata["timer"])
            logger.info(f"timer updated: {metadata['timer']}",)
        except:
            pass

    def updateAux(self, mqttClient, aux):
        self.aux = aux

    def updatePostalCode(self, postalCode):
        self.postalCode = postalCode

    def updateTimeZone(self, timeZone):
        self.timeZone = timeZone

    def setState(self, mqttClient, state):
        mqttClient.publish(self.topicHeader + "setState", state, qos=1, retain=True)

    def engine(self, mqttClient, values):

        # Check the schedule
        self.schedule.runSchedule(mqttClient, self.timeZone)
        # Check the timer
        self.timer.runTimer(mqttClient)
