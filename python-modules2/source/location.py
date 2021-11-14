import logging
import logging.config
import time
from threading import Thread, Lock
import typing

from paho.mqtt.client import Client as MqttClient

from iotcloud_api import IotCloudApi
from sensor import Sensor
from utils import MqttActions, retryFunc

logger = logging.getLogger()


class Location:
    def __init__(self, locationData, mqttclient: MqttClient, api: IotCloudApi):
        self.locationId = ""
        self.locationName = ""
        self.postalCode = 0
        self.timeZone = ""
        self.sensors: typing.Dict[str, Sensor] = {}
        self.sensorsLock = Lock()
        self.sunSchedule = []

        # Location status check data
        self.offlineInitialTimestamp = 0
        self.timeFilter = 50  # Seconds
        self.notificationSent = False
        self.api = api

        # Set location data
        self.setLocationData(locationData)

        # Set MQTT topics and handlers
        self.updatedDeviceTopic = f"v1/{self.locationId}/+/updatedDevice"
        mqttclient.message_callback_add(self.updatedDeviceTopic, self.onDeviceUpdated)
        self.updatedSensorTopic = f"v1/{self.locationId}/+/+/updatedSensor"
        mqttclient.message_callback_add(self.updatedSensorTopic, self.onSensorUpdated)

    def getSunSchedule(self):
        self.sunSchedule = self.api.getLocationSunSchedule(self.locationId)

    def subscribe(self, mqttclient: MqttClient):
        mqttclient.subscribe(self.updatedDeviceTopic)
        mqttclient.subscribe(self.updatedSensorTopic)
        with self.sensorsLock:
            for device in self.sensors.values():
                device.subscribe(mqttclient)

    def unsubscribe(self, mqttclient: MqttClient):
        mqttclient.unsubscribe(self.updatedDeviceTopic)
        mqttclient.unsubscribe(self.updatedSensorTopic)
        with self.sensorsLock:
            for device in self.sensors.values():
                device.unsubscribe(mqttclient)

    def addSensor(
        self,
        sensorId: str,
        deviceId: str,
        metadata: typing.Dict,
        mqttClient: MqttClient,
    ):
        baseTopic = f"v1/{self.locationId}/{deviceId}/{sensorId}/"
        sensor = Sensor(baseTopic, sensorId, metadata, mqttClient)
        with self.sensorsLock:
            sensor.subscribe(mqttClient)
            self.sensors[sensorId] = sensor

    def setLocationData(self, locationData: typing.Dict, mqttclient: MqttClient):
        self.locationName = locationData["locationName"]
        self.postalCode = locationData["postalCode"]
        self.timeZone = locationData["timeZone"]

        # Add or update the sensors
        for deviceData in locationData["devices"]:
            deviceId = deviceData["deviceId"]
            for sensorData in deviceData["sensors"]:
                sensorId = sensorData["sensorId"]
                metadata = sensorData["sensorMetadata"]

                try:
                    with self.sensorsLock:
                        sensor = self.sensors[sensorId]
                        sensor.setSensorData(sensorData)
                except KeyError:
                    self.addSensor(sensorId, deviceId, metadata, mqttclient)

    def onLocationUpdated(self, mqttclient: MqttClient, msg):
        action = msg.payload
        logger.info(f"Received: {action} from location: {self.locationId}")

    @retryFunc
    def updateSensor(self, locationId: str, deviceId: str, sensorId: str):
        sensorData = self.api.getSensor(locationId, deviceId, sensorId)
        try:
            sensor = self.sensors[deviceId]
        except KeyError:
            logger.error(
                f"Device: {deviceId} not found in location: {self.locationId}."
                "It was not possible to update it."
            )
            return

        metadata = sensorData["sensorMetadata"]
        with self.sensorsLock:
            sensor.setSensorData(metadata)

    def onDeviceUpdated(self, mqttclient: MqttClient, userdata, msg):
        action = msg.payload
        deviceId = msg.topic.split("/")[2]
        logger.info(
            f"Received: {action} from location: {self.locationId} and device: {deviceId}"
        )
        if action == MqttActions.DELETED:
            with self.sensorsLock:
                self.sensors[deviceId].unsubscribe(mqttclient)
                del self.sensors[deviceId]

    def onSensorUpdated(self, mqttclient: MqttClient, userdata, msg):
        action = msg.payload
        _, locationId, deviceId, sensorId, _ = msg.topic.split("/")
        logger.info(
            f"Received: {action} from location: {self.locationId} and device: {deviceId}"
        )

        if action == MqttActions.UPDATED:
            Thread(
                target=self.updateSensor,
                args=(locationId, deviceId, sensorId),
                daemon=True,
            ).start()

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
                self.api.notifyLocationOffline(self.locationId)
            except:
                logger.error(
                    f"Error while sending notification for the location: {self.locationId}",
                    exc_info=True,
                )

    def run(self):

        devicesStatus = None
        with self.sensorsLock:
            for device in self.sensors:
                device.run()
                devicesStatus = devicesStatus or device.status

        self.checkLocationStatus(devicesStatus)
