import logging
import logging.config
import time

logger = logging.getLogger()


class LocationStatus:
    def __init__(self):
        self.offlineInitialTimestamp = 0
        self.timeFilter = 50  # Seconds
        self.devicesStatus = {}
        self.notificationSent = False
        self.previousState = False

    def setDeviceStatus(self, deviceHash, newStatus):
        self.devicesStatus[deviceHash] = newStatus

    def checkLocationStatus(self, api, locationId):
        currentTimestamp = int(time.time())

        if not self.offlineInitialTimestamp:
            self.offlineInitialTimestamp = currentTimestamp

        if not self.devicesStatus or any(self.devicesStatus.values()):
            self.offlineInitialTimestamp = currentTimestamp
            self.notificationSent = False
            self.previousState = True

        if (
            self.previousState
            and not self.notificationSent
            and currentTimestamp - self.offlineInitialTimestamp > self.timeFilter
        ):
            self.notificationSent = True
            self.previousState = False

            try:
                logger.info(
                    "Sending notification for the location:%s is offline" % locationId
                )
                api.notifyLocationOffline(locationId)
            except:
                logger.info(
                    "Error while sending notification for the location:%s" % locationId,
                    exc_info=True,
                )
                return
