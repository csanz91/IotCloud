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


class Thermostat:
    def __init__(self, tags, mqttClient, subscriptionsList):

        # Aux variables
        self.tags = tags
        self.deviceTopicHeader = f"v1/{tags['locationId']}/{tags['deviceId']}/"
        self.topicHeader = self.deviceTopicHeader + tags["sensorId"] + "/"

        # Runtime variables
        self.temperatureReferences = {}
        self.heating = False
        self.setHeatingMem = False
        self.alarm = False
        self.state = False
        self.schedule = schedule.Schedule(
            tags["locationId"], self.setState, self.setSetpoint
        )
        self.timer = timer.Timer(self.setState)

        # Default settings
        self.startHeatingAt = int(time.time())
        self.setpoint = 0.0
        self.hysteresisHigh = -0.1
        self.hysteresisLow = -0.8
        self.maxHeatingTime = 3600 * 8  # 8 hours
        self.metadata = {}
        self.aux = {}
        self.tempReferenceMem = 0.0
        self.progThermostatShutdownEnabled = False
        self.progThermostatShutdownTime = 0
        self.progThermostatShutdownMem = False
        self.postalCode = None
        self.timeZone = None
        self.pwnONTime = 0
        self.pwmCycleMem = None
        self.pwmActive = False

        self.subscriptionsList = subscriptionsList

        # Subscribe to the relevant topics
        self.addTempReference(mqttClient, self.topicHeader + "value", 2)
        mqttClient.subscribe(self.topicHeader + "state")
        subscriptionsList.append(self.topicHeader + "state")
        mqttClient.subscribe(self.topicHeader + "updatedSensor")
        subscriptionsList.append(self.topicHeader + "updatedSensor")

    def addTempReference(self, mqttClient, temperatureReferenceTopic, factor):
        if temperatureReferenceTopic not in self.temperatureReferences:
            mqttClient.subscribe(temperatureReferenceTopic)
            self.subscriptionsList.append(temperatureReferenceTopic)
        self.temperatureReferences[temperatureReferenceTopic] = factor

    def updateSettings(self, mqttClient, metadata):
        try:
            self.hysteresisHigh = float(metadata["hysteresisHigh"])
        except:
            pass

        try:
            self.hysteresisLow = float(metadata["hysteresisLow"])
        except:
            pass

        try:
            self.maxHeatingTime = int(metadata["maxHeatingTime"])
        except:
            pass

        try:
            self.schedule.importSchedule(metadata)
        except:
            pass

        try:
            for temperatureReferenceTopic, factor in metadata[
                "temperatureReferences"
            ].items():
                self.addTempReference(mqttClient, temperatureReferenceTopic, factor)
        except:
            logger.error(
                "Excepcion: ", exc_info=True,
            )
            pass

        try:
            self.timer.importSettings(metadata["timer"])
            logger.info(f"timer updated: {metadata['timer']}")
        except:
            pass

        try:
            self.progThermostatShutdownEnabled = bool(
                metadata["progThermostatShutdownEnabled"]
            )
        except:
            pass

        try:
            self.progThermostatShutdownTime = int(
                metadata["progThermostatShutdownTime"]
            )
        except:
            pass

        self.metadata = copy.deepcopy(metadata)

    def updateAux(self, mqttClient, aux):
        try:
            self.heating = utils.decodeBoolean(aux["heating"])
        except:
            pass

        try:
            self.setpoint = float(aux["setpoint"])
            logger.debug(f"Received setpoint: {self.setpoint}")
        except:
            pass

        try:
            assert aux["ackAlarm"]
            self.setAlarm(mqttClient, False)
            del aux["ackAlarm"]
        except:
            pass

        self.aux = copy.deepcopy(aux)

    def updatePostalCode(self, postalCode):
        self.postalCode = postalCode

    def updateTimeZone(self, timeZone):
        self.timeZone = timeZone

    def calculateTempReference(self, values):
        tempReference = 0.0
        factorsSum = 0.0
        for temperatureReferenceTopic, factor in self.temperatureReferences.items():
            if not factor:
                continue
            try:
                temperature = values[temperatureReferenceTopic]
                # If the temperature value was received more than 15 minutes ago, discard it
                if temperature.timestamp + 60 * 15 < int(time.time()):
                    logger.warn(
                        "Expired temperature value from the topic: %s"
                        % temperatureReferenceTopic
                    )
                    continue
                factorsSum += factor
                tempReference += temperature.value * factor
            # The sensor was not found
            except (KeyError, TypeError):
                logger.warning(
                    f"Temperature value from the topic:{temperatureReferenceTopic} not available",
                )
        if tempReference and factorsSum:
            tempReference = tempReference / factorsSum

        return tempReference

    def setHeating(self, mqttClient, heating):
        self.setHeatingMem = heating
        mqttClient.publish(
            self.topicHeader + "aux/setHeating", heating, qos=1, retain=True
        )

    def setAlarm(self, mqttClient, alarm):
        self.alarm = alarm
        mqttClient.publish(self.topicHeader + "aux/alarm", alarm, qos=1, retain=True)

    def setState(self, mqttClient, state):
        mqttClient.publish(self.topicHeader + "setState", state, qos=1, retain=True)

    def setSetpoint(self, mqttClient, setpoint):
        mqttClient.publish(
            self.topicHeader + "aux/setpoint", setpoint, qos=1, retain=True
        )

    def progThermostatShutdown(self, mqttClient):
        if self.progThermostatShutdownEnabled:

            if not self.timeZone:
                logger.warning("Time zone not available",)
                return

            minutesConverted = utils.getMinutesConverted(
                self.progThermostatShutdownTime, self.timeZone
            )
            currentMinute = utils.getCurrentMinute(self.timeZone)

            # logger.info(f"{currentMinute=}, {minutesConverted=}")
            if currentMinute == minutesConverted:
                if not self.progThermostatShutdownMem:
                    logger.info("Shuthing down the thermostat")
                    self.progThermostatShutdownMem = True
                    self.state = False
                    self.setState(mqttClient, self.state)
            else:
                self.progThermostatShutdownMem = False

    def engine(self, mqttClient, values):
        # Check the schedule
        self.schedule.runSchedule(mqttClient, self.timeZone)
        # Check the timer
        self.timer.runTimer(mqttClient)
        # Check the programmed shutdown
        self.progThermostatShutdown(mqttClient)

        # The thermostat cannot run if there is an active alarm or if it is not active
        if self.alarm or not self.state:
            logger.debug(
                f"Thermostat: {self.topicHeader} not running because is stopped or an alarm is set",
            )
            # Delete the retentive heating. The device also evaluates this condition
            if self.heating or self.setHeatingMem:
                self.pwmActive = False
                self.setHeating(mqttClient, False)
            return

        tempReference = self.calculateTempReference(values)
        # logger.info(f"{tempReference=}, {self.setpoint=}, {self.heating=}")

        # These values are needed to be able to run the algorithm
        if not tempReference or not self.setpoint:
            logger.warning(
                f"Some of the core values are not valid. tempReference: {tempReference}, setpoint: {self.setpoint}",
            )
            return

        if self.tempReferenceMem != tempReference:
            utils.pushValue(
                mqttClient, self.tags, "tempReference", tempReference, retain=True
            )
            self.tempReferenceMem = tempReference

        runningTime = int(time.time()) - self.startHeatingAt

        # If the heating has been running for more than [maxHeatingTime] there could be
        # something wrong. Trigger the alarm to protect the instalation.
        if self.heating and runningTime > self.maxHeatingTime:
            logger.warning(
                f"Heating running for more than {self.maxHeatingTime} sec. in {self.deviceTopicHeader}. Triggering alarm",
            )
            self.setHeating(mqttClient, False)
            self.setAlarm(mqttClient, True)
            return

        # The reference temperature is below the setpoint -> start heating
        if not self.pwmActive and tempReference <= self.setpoint + self.hysteresisLow:
            self.startHeatingAt = int(time.time())
            self.pwmActive = True
        # The reference temperature is above the setpoint -> stop heating
        elif self.pwmActive and tempReference >= self.setpoint + self.hysteresisHigh:
            self.pwmActive = False

        # PWM period 10 minutes
        cycleTime = 600

        pwmCurrentCycle = runningTime // cycleTime
        if self.pwmCycleMem != pwmCurrentCycle:
            # Proportional error correction
            pAction = 400.0
            self.pwnONTime = abs(self.setpoint - tempReference) * pAction
            # Limit ON time between 2 minutes and 6 minutes
            self.pwnONTime = max(self.pwnONTime, 120)
            self.pwnONTime = min(self.pwnONTime, 360)

            logger.info(
                f"New duty cycle: {self.pwnONTime} for: {self.deviceTopicHeader}"
            )

            self.pwmCycleMem = pwmCurrentCycle

        pwmON = runningTime % cycleTime < self.pwnONTime

        if self.pwmActive and not self.heating and pwmON:
            self.setHeating(mqttClient, True)
            logger.info(f"Start heating for: {self.deviceTopicHeader}")
        elif self.heating and (not self.pwmActive or self.pwmActive and not pwmON):
            self.setHeating(mqttClient, False)
            logger.info(f"Stop heating for: {self.deviceTopicHeader}",)

