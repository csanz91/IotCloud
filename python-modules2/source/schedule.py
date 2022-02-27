import logging
import logging.config
from typing import Callable

from paho.mqtt.client import Client as MqttClient

from locationdatamanager import LocationDataManager
from sunschedulemanager import SunScheduleData
import utils

logger = logging.getLogger()


class Schedule(object):

    # Just for type hinting
    metadata: dict
    setState: Callable
    setValue: Callable

    def __init__(self):
        super().__init__()

        self.scheduleRunning = False
        self.sunScheduleRunning = False
        self.doNotTurnOffEndSchudule = False
        self.lastValue = None

    def runSunSchedule(self,  mqttclient: MqttClient, today, currentMinute, timeZoneId, sunSchedule: SunScheduleData):
        try:
            solarSchedule = self.metadata["schedule"]["solarSchedule"]
        except KeyError:
            return

        todaySchedule = solarSchedule[today]

        for scheduleElement in todaySchedule:

            state, offset, value, isSunrise = scheduleElement
            if isSunrise:
                sunHour = utils.getMinutesConverted(
                    sunSchedule.sunrise, timeZoneId
                )
            else:
                sunHour = utils.getMinutesConverted(
                    sunSchedule.sunset, timeZoneId
                )

            # If the schedule is activated:
            logger.debug(
                f"Current minute: {currentMinute}, sunschedule: {sunHour}, offset: {offset}")
            if currentMinute == sunHour + offset:
                # If the state is different from the setpoint
                if not self.sunScheduleRunning:
                    logger.info(f"Setting sun schedule to {state}")
                    self.sunScheduleRunning = True
                    self.setState(mqttclient, state)
                    self.setValue(mqttclient, value)
                return

        # Reset the mem
        if self.sunScheduleRunning:
            self.sunScheduleRunning = False

    def runManualSchedule(self,  mqttclient: MqttClient, today, currentMinute):
        try:
            manualSchedule = self.metadata["schedule"]["manualSchedule"]
        except KeyError:
            return

        todaySchedule = manualSchedule[today]
        for scheduleElement in todaySchedule:
            # If schedule is activated
            start, duration, value, doNotTurnOffEndSchudule = scheduleElement

            if currentMinute >= start and currentMinute < start + duration:
                # If the schedule wasnt active
                if not self.scheduleRunning:
                    logger.debug("Running manual schedule")
                    self.doNotTurnOffEndSchudule = doNotTurnOffEndSchudule
                    self.scheduleRunning = True
                    self.setState(mqttclient, True)
                    self.setValue(mqttclient, value)
                elif self.lastValue != value:
                    logger.debug(
                        f"Changing value from: {self.lastValue} to {value}")
                    self.setValue(mqttclient, value)

                self.lastValue = value
                return

        # If the schudele is not active anymore, shut it down
        if self.scheduleRunning:
            self.scheduleRunning = False
            if self.doNotTurnOffEndSchudule:
                return
            self.setState(mqttclient, False)

    def runSchedule(self, mqttclient: MqttClient, locationData: LocationDataManager):

        try:
            enabled = self.metadata["schedule"]["enabled"]
        except KeyError:
            enabled = True

        if not enabled:
            self.scheduleRunning = False
            self.sunScheduleRunning = False
            return

        timeZone = locationData.timeZone
        if not timeZone:
            logger.warning("Time zone not available")
            return

        now = utils.getLocalTime(timeZone)
        currentMinute = utils.getCurrentMinute(timeZone)
        today = now.weekday()  # Mon: 0, Sun: 6
        sunSchedule = locationData.getSunSchedule()

        self.runSunSchedule(mqttclient, today,
                            currentMinute, timeZone, sunSchedule)
        self.runManualSchedule(mqttclient, today, currentMinute)
