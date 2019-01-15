import logging
import logging.config
import time
import datetime
from dateutil import tz

import schedule

logger = logging.getLogger()

class Switch():
    def __init__(self, tags, mqttClient):

        # Aux variables
        self.tags = tags
        self.deviceTopicHeader = "v1/{locationId}/{deviceId}/".format(locationId=tags["locationId"],
                                                                      deviceId=tags["deviceId"])
        self.topicHeader = self.deviceTopicHeader+tags["sensorId"]+"/"

        # Runtime variables
        self.state = False
        self.schedule = schedule.Schedule(self.setState)
        self.metadata = {}
        self.aux = {}

        # Subscribe to the relevant topics
        mqttClient.subscribe(self.deviceTopicHeader+"status")
        mqttClient.subscribe(self.topicHeader+"state")
        mqttClient.subscribe(self.topicHeader+"updatedSensor")

    def updateSettings(self, mqttClient, metadata):
        self.metadata = metadata
        try:
            self.schedule.schedule = metadata['schedule']
            logger.info("schedule updated: %s" % self.schedule.schedule)
        except:
            pass

    def updateAux(self, mqttClient, aux):
        self.aux = aux

    def setState(self, mqttClient, state):
        mqttClient.publish(self.topicHeader+"setState", state, qos=1, retain=True)

    def engine(self, mqttClient, values):

        # Check the schedule
        self.schedule.runSchedule(mqttClient)