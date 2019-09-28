import logging
import logging.config
import time
import datetime
from dateutil import tz

import schedule
import timer

logger = logging.getLogger()

class Toogle():
    def __init__(self, tags, mqttClient, subscriptionsList):

        # Aux variables
        self.tags = tags
        self.deviceTopicHeader = "v1/{locationId}/{deviceId}/".format(locationId=tags["locationId"],
                                                                      deviceId=tags["deviceId"])
        self.topicHeader = self.deviceTopicHeader+tags["sensorId"]+"/"

        # Runtime variables
        self.state = False
        self.schedule = schedule.Schedule(tags["locationId"], self.setState)
        self.metadata = {}
        self.aux = {}

        # Subscribe to the relevant topics
        mqttClient.subscribe(self.deviceTopicHeader+"status")
        subscriptionsList.append(self.deviceTopicHeader+"status")
        mqttClient.subscribe(self.topicHeader+"updatedSensor")
        subscriptionsList.append(self.topicHeader+"updatedSensor")

    def updateSettings(self, mqttClient, metadata):
        self.metadata = metadata
        try:
            self.schedule.importSchedule(metadata)
            logger.info("%s: schedule updated: %s" % (self.deviceTopicHeader, self.schedule.schedule))
        except:
            pass

    def updateAux(self, mqttClient, aux):
        self.aux = aux

    def setState(self, mqttClient, state):
        if state:
            action = "up"
        else:
            action = "down"

        mqttClient.publish(self.topicHeader+"aux/setToogle", action, qos=1, retain=False)

    def engine(self, mqttClient, values):

        # Check the schedule
        self.schedule.runSchedule(mqttClient)