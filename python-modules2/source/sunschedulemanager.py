from datetime import datetime, timedelta
import logging
import logging.config
from threading import Event, Thread

import iotcloud_api

logger = logging.getLogger()


class SunScheduleData:
    def __init__(self, sunrise: int, sunset: int, timestamp: int = 0) -> None:
        assert sunrise
        assert sunset

        self.sunrise = int(sunrise)
        self.sunset = int(sunset)
        self.timestamp = int(timestamp)
        self.utcSunScheduleExpireDate: datetime = datetime.utcnow()


class SunScheduleDataManager:

    # define just for typing
    locationId: str
    api: iotcloud_api.IotCloudApi

    def __init__(self):
        self.enableSunSchedule = False
        # By default set the sunrise at 08:00 and sunset at 20:00
        self.sunSchedule: SunScheduleData = SunScheduleData(60 * 8, 60 * 19)

        self.retrievingData = Event()

    def registerSunSchedule(self):
        self.enableSunSchedule = True

    def unregisterSunSchedule(self):
        self.enableSunSchedule = False

    def renewSunSchedule(self, hours):
        self.sunSchedule.utcSunScheduleExpireDate = datetime.utcnow() + \
            timedelta(hours=hours)

    def retrieveSunSchedule(self):
        try:
            sunScheduleData = self.api.getLocationSunSchedule(self.locationId)

            self.sunSchedule = SunScheduleData(
                sunScheduleData["sunrise"],
                sunScheduleData["sunset"],
                sunScheduleData["timestamp"])
            self.renewSunSchedule(11)

        except:
            logger.error(
                "It was not possible to retrieve the sun schedule.", exc_info=True)
            self.renewSunSchedule(1)
        finally:
            self.retrievingData.clear()

    def updateSunSchedule(self):

        if not self.enableSunSchedule:
            return

        now = datetime.utcnow()
        if now > self.sunSchedule.utcSunScheduleExpireDate and not self.retrievingData.is_set():
            self.retrievingData.set()
            Thread(target=self.retrieveSunSchedule).start()

    def getSunSchedule(self) -> SunScheduleData:
        return self.sunSchedule
