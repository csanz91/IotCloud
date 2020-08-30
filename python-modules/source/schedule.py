import logging
import logging.config
import datetime
import time
from dateutil import tz

import iothub_api
import utils

logger = logging.getLogger()

# IotHub api setup
api = iothub_api.IothubApi()

class Schedule():
    def __init__(self, locationId, setState, setValue=lambda a,b: None):
        self.schedule = [[], [], [], [], [], [], []]
        self.solarSchedule = [[], [], [], [], [], [], []]
        self.sunScheduleInfo = {"timestamp": 0, "sunrise": 0, "sunset": 0}
        self.scheduleRunning = False
        self.sunScheduleRunning = False
        self.setState = setState
        self.setValue = setValue

        self.locationId = locationId

    def importSchedule(self, metadata):
        # [start, duration, value]
        self.schedule = metadata['schedule']['manualSchedule']
        # [state, offset, value, isSunrise]
        self.solarSchedule = metadata['schedule']['solarSchedule']

    def runSunSchedule(self, mqttClient, today, currentMinute, timeZoneId):
        todaySchedule = self.solarSchedule[today]
        
        for scheduleElement in todaySchedule:

            state, offset, value, isSunrise = scheduleElement
            if isSunrise:
                sunHour = utils.getMinutesConverted(self.sunScheduleInfo["sunrise"], timeZoneId)
            else:
                sunHour = utils.getMinutesConverted(self.sunScheduleInfo["sunset"], timeZoneId)

            # If the schedule is activated:
            if currentMinute == sunHour+offset:
                # If the state is different from the setpoint
                if not self.sunScheduleRunning:
                    logger.info(f"Setting sun schedule to {state}")
                    self.sunScheduleRunning = True
                    self.setState(mqttClient, state)
                    self.setValue(mqttClient, value)
                return

        # Reset the mem
        if self.sunScheduleRunning:
            self.sunScheduleRunning = False

    def runManualSchedule(self, mqttClient, today, currentMinute, timeZoneId):
        todaySchedule = self.schedule[today]
        for scheduleElement in todaySchedule:
            # If schedule is activated
            start = utils.getMinutesConverted(scheduleElement[0], timeZoneId)
            #logger.info(f"{currentMinute=}, {start=}")

            if currentMinute >= start and currentMinute < start + scheduleElement[1]:
                # If the schedule wasnt active
                if not self.scheduleRunning:
                    logger.info("Running manual schedule")
                    self.scheduleRunning = True
                    self.setState(mqttClient, True)
                    self.setValue(mqttClient, scheduleElement[2])
                return

        # If the schudele is not active anymore, shut it down
        if self.scheduleRunning:
            self.scheduleRunning = False
            self.setState(mqttClient, False)


    def runSchedule(self, mqttClient, timeZoneId):

        if not timeZoneId:
            logger.warning("Time zone not available")
            return

        now = utils.getLocalTime(timeZoneId)
        currentMinute = utils.getCurrentMinute(timeZoneId)
        today = now.weekday() # Mon: 0, Sun: 6

        # Even if we have the function cached everywhere, this check in memory can
        # improve things slightly because this function can be called many times
        utcSunScheduleTimestamp = datetime.datetime.utcfromtimestamp(self.sunScheduleInfo["timestamp"]).replace(tzinfo=tz.UTC)
        utcSunScheduleExpireTimestamp = utcSunScheduleTimestamp + datetime.timedelta(hours=24)
        if now > utcSunScheduleExpireTimestamp:
            try:
                newSunScheduleInfo = api.getLocationSunSchedule(self.locationId)
                assert float(newSunScheduleInfo["sunrise"])
                assert float(newSunScheduleInfo["sunset"])
                self.sunScheduleInfo = newSunScheduleInfo
            except:
                logger.warning("Unable to recover the sunschedule. Extending the current one.")
                # In case we are not able to recover the sun schedule:
                # 
                # If we have previous data stored, make it last more
                if self.sunScheduleInfo["timestamp"]:
                    self.sunScheduleInfo["timestamp"] += 3600
                # If we dont have any data:
                else:
                    # Set the timestamp so the data will be fetched again in 1 hour
                    self.sunScheduleInfo["timestamp"] = int(time.time()) - 23*3600
                    # Set the sunrise at 08:00
                    self.sunScheduleInfo["sunrise"] = 60 * 8
                    # Set the sunset at 19:00
                    self.sunScheduleInfo["sunset"] = 60 * 19

                logger.info(f"New sunschedule: {self.sunScheduleInfo}")

        self.runSunSchedule(mqttClient, today, currentMinute, timeZoneId)
        self.runManualSchedule(mqttClient, today, currentMinute, timeZoneId)
        