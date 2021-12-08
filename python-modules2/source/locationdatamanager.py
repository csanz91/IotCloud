import logging
import logging.config

import iotcloud_api
from sunschedulemanager import SunScheduleDataManager

logger = logging.getLogger()


class LocationDataManager(SunScheduleDataManager):
    def __init__(self, locationId: str, api: iotcloud_api.IotCloudApi):
        super().__init__()
        self.locationId = locationId
        self.timeZone = ""
        self.api = api

    def run(self):
        self.updateSunSchedule()
