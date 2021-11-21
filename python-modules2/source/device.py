import logging
import logging.config
import time
from threading import Thread, Lock
import typing

from iotcloud_api import IotCloudApi
from paho.mqtt.client import Client as MqttClient

from sensor import Sensor
from switch import Switch
from utils import MqttActions, retryFunc, decodeBoolean

logger = logging.getLogger()


class Device:
    def __init__(self, locationId, deviceId, sensorsData, mqttclient: MqttClient):

        self.locationId = locationId
        self.deviceId = deviceId
        self.status = False

        self.sensors: typing.Dict[str, Sensor] = {}
        self.sensorsLock = Lock()

        # Set location data
        self.setDeviceData(sensorsData, mqttclient)

        self.statusTopic = f"v1/{locationId}/{deviceId}/status"
        self.updatedSensorTopic = f"v1/{self.locationId}/{deviceId}/+/updatedSensor"
        mqttclient.message_callback_add(
            self.updatedSensorTopic, self.onSensorUpdated)
        mqttclient.message_callback_add(self.statusTopic, self.onDeviceStatus)

        logger.info(f"Created device with {len(self.sensors)} sensors")

    def subscribe(self, mqttclient: MqttClient):
        mqttclient.subscribe(self.statusTopic)
        mqttclient.subscribe(self.updatedSensorTopic)
        logger.info(
            f"Subscribed to {self.statusTopic} and {self.updatedSensorTopic}")

        with self.sensorsLock:
            for sensor in self.sensors.values():
                sensor.subscribe(mqttclient)

    def unsubscribe(self, mqttclient: MqttClient):
        mqttclient.unsubscribe(self.statusTopic)
        mqttclient.unsubscribe(self.updatedSensorTopic)

        with self.sensorsLock:
            for sensor in self.sensors.values():
                sensor.unsubscribe(mqttclient)

    def onDeviceStatus(self, mqttclient: MqttClient, userdata, msg) -> None:
        try:
            self.status = decodeBoolean(msg.payload)
            logger.info(
                f"Device {self.deviceId} status changed to {self.status}")
        except:
            logger.error(f"The status received: {msg.payload} is not valid")

    def addSensor(
        self,
        sensorId: str,
        sensorType: str,
        metadata: typing.Dict,
        mqttClient: MqttClient,
    ):
        baseTopic = f"v1/{self.locationId}/{self.deviceId}/"

        if sensorType == "switch":
            sensor = Switch(baseTopic, sensorId, metadata, mqttClient)
        else:
            sensor = Sensor(baseTopic, sensorId, metadata, mqttClient)

        with self.sensorsLock:
            sensor.subscribe(mqttClient)
            self.sensors[sensorId] = sensor

    def setDeviceData(self, sensorsData: typing.Dict, mqttclient: MqttClient):

        for sensorData in sensorsData:
            sensorId = sensorData["sensorId"]
            sensorType = sensorData["sensorType"]
            metadata = sensorData["sensorMetadata"]

            try:
                with self.sensorsLock:
                    sensor = self.sensors[sensorId]
                    sensor.setSensorData(sensorData)
            except KeyError:
                self.addSensor(sensorId, sensorType, metadata, mqttclient)

    @retryFunc
    def updateSensor(self, sensorId: str, api: IotCloudApi):
        sensorData = api.getSensor(self.locationId, self.deviceId, sensorId)
        try:
            sensor = self.sensors[sensorId]
        except KeyError:
            logger.error(
                f"Sensor: {sensorId} not found in the device location: {self.deviceId}."
                "It was not possible to update it."
            )
            return

        metadata = sensorData["sensorMetadata"]
        with self.sensorsLock:
            sensor.setSensorData(metadata)

    def onSensorUpdated(self, mqttclient: MqttClient, userdata, msg):
        action = msg.payload.decode("utf-8")
        sensorId = msg.topic.split("/")[-2]
        logger.info(
            f"Received: {action} from location: {self.locationId} and device: {self.deviceId}"
        )
        api = userdata["api"]
        if action == MqttActions.UPDATED:
            Thread(
                target=self.updateSensor,
                args=(sensorId, api),
                daemon=True,
            ).start()

    def run(self, mqttclient: MqttClient):

        # Only run if the device is active
        if not self.status:
            return

        with self.sensorsLock:
            for sensor in self.sensors.values():
                sensor.run(mqttclient)
