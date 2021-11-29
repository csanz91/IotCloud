from dataclasses import dataclass, field
import logging
import logging.config
import time
import typing

from paho.mqtt.client import Client as MqttClient

from locationdatamanager import LocationDataManager
from schedule import Schedule
from sensor import Sensor
from timer import Timer
import utils

logger = logging.getLogger()


class AbortException(Exception):
    pass


@dataclass(frozen=True)
class TempValue():
    value: float
    timestamp: int = field(default_factory=lambda: int(time.time()))


class Thermostat(Sensor, Timer, Schedule):

    SENSOR_TYPES = ["thermostat"]

    def __init__(
        self,
        baseTopic: str,
        sensorId: str,
        metadata: typing.Dict,
        mqttclient: MqttClient,
        locationData: LocationDataManager
    ) -> None:
        super().__init__(baseTopic, sensorId, metadata, mqttclient, locationData)

        # Runtime variables
        self.state = False
        self.tempReferences: dict[str, float] = {}
        self.tempRefValues: dict[str, TempValue] = {}
        self.heating = False
        self.setHeatingMem = False
        self.alarm = False

        # Default settings
        self.startHeatingAt = int(time.time())
        self.setpoint = 0.0
        self.stateChanged = False
        self.hysteresisHigh = -0.1
        self.hysteresisLow = -0.8
        self.maxHeatingTime = 3600 * 8  # 8 hours
        self.tempReferenceMem = 0.0
        self.progThermostatShutdownEnabled = False
        self.progThermostatShutdownTime = 0
        self.progThermostatShutdownMem = False
        self.filterTime = 90  # seconds
        self.filterTimeMem = 0

        self.setSensorData(metadata, mqttclient)

        # Set up the relevant MQTT topics
        self.stateTopic = f"{baseTopic}{sensorId}/state"
        self.auxTopic = f"{baseTopic}{sensorId}/aux/"
        self.heatingTopic = self.auxTopic + "heating"
        self.setpointTopic = self.auxTopic + "setpoint"
        self.ackAlarmTopic = self.auxTopic + "ackAlarm"
        self.setStateTopic = f"{baseTopic}{sensorId}/setState"
        mqttclient.message_callback_add(self.stateTopic, self.onDeviceState)
        mqttclient.message_callback_add(self.heatingTopic, self.onHeating)
        mqttclient.message_callback_add(self.setpointTopic, self.onSetpoint)
        mqttclient.message_callback_add(self.ackAlarmTopic, self.onAckAlarm)

        self.addTempReference(mqttclient, f"{baseTopic}{sensorId}/value", 2.0)

        # Enable the retrieval of the sun schedule
        locationData.registerSunSchedule()

    def subscribe(self, mqttclient: MqttClient) -> None:
        super().subscribe(mqttclient)
        mqttclient.subscribe(self.stateTopic)
        mqttclient.subscribe(self.heatingTopic)
        mqttclient.subscribe(self.setpointTopic)
        mqttclient.subscribe(self.ackAlarmTopic)
        for topic in self.tempReferences:
            mqttclient.subscribe(topic)

    def unsubscribe(self, mqttclient: MqttClient) -> None:
        super().unsubscribe(mqttclient)
        mqttclient.unsubscribe(self.stateTopic)
        mqttclient.unsubscribe(self.heatingTopic)
        mqttclient.unsubscribe(self.setpointTopic)
        mqttclient.unsubscribe(self.ackAlarmTopic)
        for topic in self.tempReferences:
            mqttclient.unsubscribe(topic)

    def onTempRefValue(self, mqttclient: MqttClient, userdata, msg) -> None:
        try:
            self.tempRefValues[msg.topic] = TempValue(
                utils.parseFloat(msg.payload))
        except:
            logger.error(
                f"The temp value received: {msg.payload} is not valid")

    def addTempReference(self, mqttclient: MqttClient, tempRefTopic: str, factor: float):
        if tempRefTopic not in self.tempReferences:
            mqttclient.message_callback_add(tempRefTopic, self.onTempRefValue)
            mqttclient.subscribe(tempRefTopic)
        self.tempReferences[tempRefTopic] = factor

    def setSensorData(self, metadata: typing.Dict, mqttclient: MqttClient) -> None:
        super().setSensorData(metadata, mqttclient)
        try:
            self.hysteresisHigh = utils.parseFloat(metadata["hysteresisHigh"])
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
            self.progThermostatShutdownTime = int(
                metadata["progThermostatShutdownTime"])
        except:
            pass

        try:
            self.progThermostatShutdownEnabled = bool(
                metadata["progThermostatShutdownEnabled"])
        except:
            pass

        try:
            tempReferences = metadata["temperatureReferences"]
            for topic, factor in tempReferences:
                self.addTempReference(mqttclient, topic, factor)
        except:
            pass

    def onDeviceState(self, mqttclient: MqttClient, userdata, msg) -> None:
        try:
            self.state = utils.decodeBoolean(msg.payload)
            self.stateChanged = self.state
        except:
            logger.error(f"The state received: {msg.payload} is not valid")

    def setState(self,  mqttclient: MqttClient, state) -> None:
        logger.debug(f"Setting state : {state}")
        mqttclient.publish(self.setStateTopic, state, qos=1)

    def setValue(self,  mqttclient: MqttClient, setpoint) -> None:
        mqttclient.publish(self.auxTopic + "setpoint",
                           setpoint, qos=1, retain=True)

    def setAlarm(self, mqttclient: MqttClient, alarm: bool) -> None:
        self.alarm = alarm
        mqttclient.publish(self.auxTopic + "alarm", alarm, qos=1, retain=True)

    def setHeating(self, mqttclient: MqttClient, heating: bool) -> None:
        self.setHeatingMem = heating
        mqttclient.publish(self.auxTopic + "setHeating", heating, qos=1)

    def onHeating(self, mqttclient: MqttClient, userdata, msg) -> None:
        try:
            self.heating = utils.decodeBoolean(msg.payload)
        except:
            logger.error(
                f"The heating state received: {msg.payload} is not valid")

    def onSetpoint(self, mqttclient: MqttClient, userdata, msg) -> None:
        try:
            self.setpoint = utils.parseFloat(msg.payload)
            self.stateChanged = True
        except:
            logger.error(f"The setpoint received: {msg.payload} is not valid")

    def onAckAlarm(self, mqttclient: MqttClient, userdata, msg) -> None:
        try:
            ackAlarm = utils.decodeBoolean(msg.payload)
            assert ackAlarm
            self.setAlarm(mqttclient, False)
            self.stateChanged = True
        except:
            logger.error(f"The alarm ACK received: {msg.payload} is not valid")

    def progThermostatShutdown(self, timeZone: str, mqttclient: MqttClient) -> None:
        if not self.progThermostatShutdownEnabled:
            return

        if not timeZone:
            logger.warning("Time zone not available",)
            return

        minutesConverted = utils.getMinutesConverted(
            self.progThermostatShutdownTime, timeZone)
        currentMinute = utils.getCurrentMinute(timeZone)

        if currentMinute == minutesConverted:
            if not self.progThermostatShutdownMem:
                logger.debug("Shuthing down the thermostat")
                self.progThermostatShutdownMem = True
                self.state = False
                self.setState(mqttclient, self.state)
        else:
            self.progThermostatShutdownMem = False

    def calculateTempReference(self, currentTime: int):
        tempReference = 0.0
        factorsSum = 0.0
        expirationTime = currentTime - 60 * 15  # 15 minutes ago
        for tempRefTopic, factor in self.tempReferences.items():
            if not factor:
                continue
            try:
                temperature = self.tempRefValues[tempRefTopic]
                # If the temperature value is expired, discard it
                if temperature.timestamp < expirationTime:
                    logger.warn(
                        f"Expired temperature value from the topic: {tempRefTopic}")
                    continue
                factorsSum += factor
                tempReference += temperature.value * factor
            # The sensor was not found
            except (KeyError, TypeError):
                logger.warning(
                    f"Temperature value from the topic: {tempRefTopic} is not available",
                )
        if tempReference and factorsSum:
            tempReference /= factorsSum

        return tempReference

    def isThermostatEnabled(self, mqttclient: MqttClient) -> None:
        # The thermostat cannot run if there is an active alarm or if it is not active
        if self.alarm or not self.state:
            logger.debug(
                f"Thermostat: {self.baseTopic} not running because is stopped or an alarm is set",
            )
            # Delete the retentive heating. The device also evaluates this condition
            if self.heating or self.setHeatingMem:
                self.setHeating(mqttclient, False)
            raise AbortException

    def reportReferenceTemperature(self, tempReference: float, mqttclient: MqttClient) -> None:
        if self.tempReferenceMem != tempReference:
            mqttclient.publish(self.auxTopic + "tempReference",
                               tempReference, retain=True)
            self.tempReferenceMem = tempReference

    def checkMaxHeatingTime(self, currentTime: int, mqttclient: MqttClient) -> None:
        # If the heating has been running for more than [maxHeatingTime] there could be
        # something wrong. Trigger the alarm to protect the instalation.
        runningTime = currentTime - self.startHeatingAt
        if self.heating and runningTime > self.maxHeatingTime:
            logger.warning(
                f"Heating running for more than {self.maxHeatingTime} sec. in {self.baseTopic}. Triggering alarm",
            )
            self.setHeating(mqttclient, False)
            self.setAlarm(mqttclient, True)
            raise AbortException

    def heatingLogic(self, tempReference: float, currentTime: int, mqttclient: MqttClient) -> None:
        # The reference temperature is below the hysteris window
        tempBelowRef = tempReference <= self.setpoint + self.hysteresisLow

        # Start heating after the filter time has elapsed
        if tempBelowRef and self.filterTimeMem == 0:
            self.filterTimeMem = currentTime
        elif not tempBelowRef:
            self.filterTimeMem = 0
        startHeating = tempBelowRef and currentTime > self.filterTimeMem + self.filterTime

        # Start heating if the user changed some parameter and temperature is within the hysteresis range
        startHeatingWithUserInput = self.stateChanged and tempReference < self.setpoint + self.hysteresisHigh

        # The heating is not active and the reference temperature is below the setpoint
        if not self.heating and (startHeating or startHeatingWithUserInput):
            self.setHeating(mqttclient, True)
            self.startHeatingAt = currentTime
            logger.info(f"Start heating for: {self.baseTopic}")
        # The reference temperature is above the setpoint -> stop heating
        elif self.heating and tempReference >= self.setpoint + self.hysteresisHigh:
            self.setHeating(mqttclient, False)
            logger.info(f"Stop heating for: {self.baseTopic}")

        self.stateChanged = False

    def run(self, mqttclient: MqttClient, locationData: LocationDataManager) -> None:
        # Check the timer
        self.runTimer(mqttclient)
        # Check the schedule
        self.runSchedule(mqttclient, locationData)
        # Check the programmed shutdown
        self.progThermostatShutdown(locationData.timeZone, mqttclient)

        try:
            self.isThermostatEnabled(mqttclient)
        except AbortException:
            return

        currentTime = int(time.time())
        tempReference = self.calculateTempReference(currentTime)
        logger.debug(f"{tempReference=}, {self.setpoint=}, {self.heating=}")
        # These values are needed to be able to run the algorithm
        if not tempReference or not self.setpoint:
            logger.warning(
                f"Some of the core values are not valid. tempReference: {tempReference}, setpoint: {self.setpoint}",
            )
            return

        # Report the reference temperature
        self.reportReferenceTemperature(tempReference, mqttclient)

        # Check the max heating time
        try:
            self.checkMaxHeatingTime(currentTime, mqttclient)
        except AbortException:
            return

        # Run the thermostat logic
        self.heatingLogic(tempReference, currentTime, mqttclient)
