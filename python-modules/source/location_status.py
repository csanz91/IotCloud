import logging
import logging.config
import time

logger = logging.getLogger()


class LocationStatus():
    def __init__(self):
        self.offlineInitialTimestamp = 0
        self.timeFilter = 600  # Seconds
        self.devicesStatus = {}
        self.notificationSent = False
        self.previousState = False

    def setDeviceStatus(self, deviceHash, newStatus):
        self.devicesStatus[deviceHash] = newStatus

    def checkLocationStatus(self, api, locationId):
        currentTimestamp = int(time.time())

        if not self.offlineInitialTimestamp:
            self.offlineInitialTimestamp = currentTimestamp

        if not self.devicesStatus or any(deviceStatus for deviceStatus in self.devicesStatus.values()):
            self.offlineInitialTimestamp = currentTimestamp
            self.notificationSent = False
            self.previousState = True

        if self.previousState and not self.notificationSent and currentTimestamp - self.offlineInitialTimestamp > self.timeFilter:
            self.notificationSent = True
            self.previousState = False
            logger.info("The location:%s is offline" % locationId)
            api.notifyLocationOffline(locationId)
