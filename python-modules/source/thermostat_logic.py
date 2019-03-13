import logging
import logging.config
import time
import datetime
from dateutil import tz
import copy

import schedule
import timer
import utils

logger = logging.getLogger()


class Thermostat():
    def __init__(self, tags, mqttClient, subscriptionsList):

        # Aux variables
        self.tags = tags
        self.deviceTopicHeader = "v1/{locationId}/{deviceId}/".format(locationId=tags["locationId"],
                                                                           deviceId=tags["deviceId"])
        self.topicHeader = self.deviceTopicHeader+tags["sensorId"]+"/"

        # Runtime variables
        self.temperatureReferences = {}
        self.heating = False
        self.setHeatingMem = False
        self.alarm = False
        self.state = False
        self.schedule = schedule.Schedule(tags["locationId"], self.setState, self.setSetpoint)
        self.timer = timer.Timer(self.setState)

        # Default settings
        self.startHeatingAt = int(time.time())
        self.setpoint = 0.0
        self.hysteresisHigh = -0.1
        self.hysteresisLow = -0.8
        self.maxHeatingTime = 3600 * 8 # 8 hours
        self.metadata = {}
        self.aux = {}
        self.tempReferenceMem = 0.0

        self.subscriptionsList = subscriptionsList

        # Subscribe to the relevant topics
        self.addTempReference(mqttClient, self.topicHeader+"value", 2)
        mqttClient.subscribe(self.topicHeader+"state")
        subscriptionsList.append(self.topicHeader+"state")
        mqttClient.subscribe(self.deviceTopicHeader+"status")
        subscriptionsList.append(self.deviceTopicHeader+"status")
        mqttClient.subscribe(self.topicHeader+"updatedSensor")
        subscriptionsList.append(self.topicHeader+"updatedSensor")

    def addTempReference(self, mqttClient, temperatureReferenceTopic, factor):
        if not temperatureReferenceTopic in self.temperatureReferences:
            mqttClient.subscribe(temperatureReferenceTopic)
            self.subscriptionsList.append(temperatureReferenceTopic)
        self.temperatureReferences[temperatureReferenceTopic] = factor

    def updateSettings(self, mqttClient, metadata):
        try:
            self.hysteresisHigh = float(metadata['hysteresisHigh'])
        except:
            pass

        try:
            self.hysteresisLow = float(metadata['hysteresisLow'])
        except:
            pass

        try:
            self.maxHeatingTime = int(metadata['maxHeatingTime'])
        except:
            pass

        try:
            self.schedule.importSchedule(metadata)
        except:
            pass

        try:
            for temperatureReferenceTopic, factor in metadata['temperatureReferences'].items():
                self.addTempReference(mqttClient, temperatureReferenceTopic, factor)
        except:
            logger.error("Excepcion: ", exc_info=True)
            pass

        try:
            self.timer.importSettings(metadata['timer']) 
            logger.info("timer updated: %s" % metadata['timer'])
        except:
            pass

        self.metadata = copy.deepcopy(metadata)

    def updateAux(self, mqttClient, aux):
        try:
            self.heating = utils.decodeBoolean(aux['heating'])
        except:
            pass

        try:
            self.setpoint = float(aux['setpoint'])
        except:
            pass

        try:
            assert aux["ackAlarm"]
            self.setAlarm(mqttClient, False)
            del aux["ackAlarm"]
        except:
            pass
        
        self.aux = copy.deepcopy(aux)

    def calculateTempReference(self, values):
        tempReference = 0.0
        factorsSum = 0.0
        for temperatureReferenceTopic, factor in self.temperatureReferences.items():
            if not factor:
                continue
            try:
                temperature = values[temperatureReferenceTopic]
                # If the temperature value was received more than 15 minutes ago, discard it
                if temperature.timestamp+60*15 < int(time.time()):
                    logger.warn("Expired temperature value from the topic: %s" % temperatureReferenceTopic)
                    continue
                factorsSum += factor
                tempReference += temperature.value*factor
            # The sensor was not found
            except (KeyError, TypeError):
                logger.warning("Temperature value from the topic: %s not available" % temperatureReferenceTopic)
        if tempReference and factorsSum:
            tempReference = tempReference / factorsSum

        return tempReference

    def setHeating(self, mqttClient, heating):
        self.setHeatingMem = heating
        mqttClient.publish(self.topicHeader+"aux/setHeating", heating, qos=1, retain=True)

    def setAlarm(self, mqttClient, alarm):
        self.alarm = alarm
        mqttClient.publish(self.topicHeader+"aux/alarm", alarm, qos=1, retain=True)

    def setState(self, mqttClient, state):
        mqttClient.publish(self.topicHeader+"setState", state, qos=1, retain=True)

    def setSetpoint(self, mqttClient, setpoint):
        mqttClient.publish(self.topicHeader+"aux/setpoint", setpoint, qos=1, retain=True)

    def engine(self, mqttClient, values):
        # Check the schedule
        self.schedule.runSchedule(mqttClient)
        # Check the timer
        self.timer.runTimer(mqttClient)

        # The thermostat cannot run if there is an active alarm or if it is not active
        if self.alarm or not self.state:
            logger.debug("Thermostat: %s not running because is stopped or an alarm is set" % self.topicHeader)
            # Delete the retentive heating. The device also evaluates this condition
            if self.heating or self.setHeatingMem:
                self.setHeating(mqttClient, False)
            return

        tempReference = self.calculateTempReference(values)
        logger.debug("tempReference: %s, setpoint: %s" % (tempReference, self.setpoint))

        # These values are needed to be able to run the algorithm
        if not tempReference or not self.setpoint:
            logger.warning("Some of the core values are not valid. tempReference: %s, setpoint: %s" % (tempReference, self.setpoint))
            return

        if self.tempReferenceMem != tempReference:
            utils.pushValue(mqttClient, self.tags, "tempReference", tempReference, retain=True)
            self.tempReferenceMem = tempReference

        # If the heating has been running for more than [maxHeatingTime] there could be
        # something wrong. Trigger the alarm to protect the instalation.
        if self.heating and self.startHeatingAt+self.maxHeatingTime < int(time.time()):
            logger.warning("Heating running for more than %s seconds. Triggering alarm" % self.maxHeatingTime)
            self.setHeating(mqttClient, False)
            self.setAlarm(mqttClient, True)
            return
        
        # The reference temperature is below the setpoint -> start heating
        if not self.heating and tempReference <= self.setpoint+self.hysteresisLow:
            self.setHeating(mqttClient, True)
            self.startHeatingAt = int(time.time())
            logger.info("Start heating")
        # The reference temperature is above the setpoint -> stop heating
        elif self.heating and tempReference >= self.setpoint+self.hysteresisHigh:
            self.setHeating(mqttClient, False)
            logger.info("Stop heating")