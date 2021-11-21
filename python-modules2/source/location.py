import logging
import logging.config
import time
from threading import Lock
import typing

from paho.mqtt.client import Client as MqttClient

from iotcloud_api import IotCloudApi
from device import Device
from utils import MqttActions

logger = logging.getLogger()


class Location:
    def __init__(
        self, locationId, locationData, mqttclient: MqttClient, api: IotCloudApi
    ):
        self.locationId = locationId
        self.locationName = ""
        self.postalCode = 0
        self.timeZone = ""
        self.devices: typing.Dict[str, Device] = {}
        self.devicesLock = Lock()
        self.sunSchedule = []

        # Location status check data
        self.offlineInitialTimestamp = 0
        self.timeFilter = 50  # Seconds
        self.notificationSent = False
        self.api = api

        # Set location data
        self.setLocationData(locationData, mqttclient)

        # Set MQTT topics and handlers
        self.updatedDeviceTopic = f"v1/{self.locationId}/+/updatedDevice"
        mqttclient.message_callback_add(
            self.updatedDeviceTopic, self.onDeviceUpdated)

        logger.info(
            f"Created location: {self.locationName} with {len(self.devices)} devices")

    def getSunSchedule(self):
        self.sunSchedule = self.api.getLocationSunSchedule(self.locationId)

    def subscribe(self, mqttclient: MqttClient):
        mqttclient.subscribe(self.updatedDeviceTopic)
        with self.devicesLock:
            for device in self.devices.values():
                device.subscribe(mqttclient)

    def unsubscribe(self, mqttclient: MqttClient):
        mqttclient.unsubscribe(self.updatedDeviceTopic)
        with self.devicesLock:
            for device in self.devices.values():
                device.unsubscribe(mqttclient)

    def setLocationData(self, locationData: typing.Dict, mqttclient: MqttClient):
        self.locationName = locationData["locationName"]
        self.postalCode = locationData["postalCode"]
        self.timeZone = locationData["timeZone"]

        # Add or update the devices
        for deviceData in locationData["devices"]:
            deviceId = deviceData["deviceId"]
            sensorsData = deviceData["sensors"]

            try:
                with self.devicesLock:
                    device = self.devices[deviceId]
                    device.setDeviceData(sensorsData, mqttclient)
            except KeyError:
                with self.devicesLock:
                    device = Device(self.locationId, deviceId,
                                    sensorsData, mqttclient)
                    self.devices[deviceId] = device

    def onLocationUpdated(self, mqttclient: MqttClient, msg):
        action = msg.payload.decode("utf-8")
        logger.info(f"Received: {action} from location: {self.locationId}")

    def onDeviceUpdated(self, mqttclient: MqttClient, userdata, msg):
        action = msg.payload.decode("utf-8")
        deviceId = msg.topic.split("/")[2]
        logger.info(
            f"Received: {action} from location: {self.locationId} and device: {deviceId}"
        )
        if action == MqttActions.DELETED:
            with self.devicesLock:
                self.devices[deviceId].unsubscribe(mqttclient)
                del self.devices[deviceId]

    def checkLocationStatus(self, devicesStatus: bool):
        currentTimestamp = int(time.time())

        if not self.offlineInitialTimestamp:
            self.offlineInitialTimestamp = currentTimestamp

        if devicesStatus:
            self.offlineInitialTimestamp = currentTimestamp
            self.notificationSent = False

        elif (
            not self.notificationSent
            and currentTimestamp - self.offlineInitialTimestamp > self.timeFilter
        ):
            self.notificationSent = True

            try:
                logger.info(
                    f"Sending notification for the location: {self.locationId} is offline"
                )
                self.api.notifyLocationOffline(
                    self.locationId, self.locationName)
            except:
                logger.error(
                    f"Error while sending notification for the location: {self.locationId}",
                    exc_info=True,
                )

    def run(self, mqttclient: MqttClient):

        devicesStatus = False
        with self.devicesLock:
            for device in self.devices.values():
                device.run(mqttclient)
                devicesStatus = devicesStatus or device.status

        self.checkLocationStatus(devicesStatus)
