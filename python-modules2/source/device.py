import logging
import logging.config
from threading import Lock, Thread
import time
import typing

from paho.mqtt.client import Client as MqttClient

from iotcloud_api import IotCloudApi
from locationdatamanager import LocationDataManager
from sensor import Sensor
from switch import Switch
from thermostat import Thermostat
from toogle import Toogle
from notifier import Notifier
from utils import MqttActions, decodeStatus, retryFunc

logger = logging.getLogger()


class Device:
    def __init__(self, locationId, deviceId, sensorsData, mqttclient: MqttClient, locationData: LocationDataManager):

        self.locationId = locationId
        self.deviceId = deviceId
        self.status = False

        self.sensors: typing.Dict[str, Sensor] = {}
        self.sensorsLock = Lock()

        self.locationData = locationData

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
            self.status = decodeStatus(msg.payload)
            logger.debug(
                f"Device {self.deviceId} status changed to {self.status}")
        except:
            logger.error(f"The status received: {msg.payload} is not valid")

    def addSensor(
        self,
        sensorId: str,
        sensorType: str,
        sensorName: str,
        metadata: typing.Dict,
        mqttClient: MqttClient,
    ):
        baseTopic = f"v1/{self.locationId}/{self.deviceId}/"

        sensorType = sensorType.lower()
        if sensorType in Switch.SENSOR_TYPES:
            sensor = Switch(baseTopic, sensorId, sensorName, metadata,
                            mqttClient, self.locationData)
        elif sensorType in Thermostat.SENSOR_TYPES:
            sensor = Thermostat(baseTopic, sensorId, sensorName, metadata,
                                mqttClient, self.locationData)
        elif sensorType in Toogle.SENSOR_TYPES:
            sensor = Toogle(baseTopic, sensorId, sensorName, metadata,
                            mqttClient, self.locationData)
        elif sensorType in Notifier.SENSOR_TYPES:
            sensor = Notifier(baseTopic, sensorId, sensorName, metadata,
                              mqttClient, self.locationData)
        else:
            logger.info(f"Sensor type {sensorType} not supported.")
            return

        with self.sensorsLock:
            sensor.subscribe(mqttClient)
            self.sensors[sensorId] = sensor

    def setDeviceData(self, sensorsData: typing.Dict, mqttclient: MqttClient):

        for sensorData in sensorsData:
            sensorId = sensorData["sensorId"]
            sensorType = sensorData["sensorType"]
            sensorName = sensorData["sensorName"]
            metadata = sensorData["sensorMetadata"]

            try:
                with self.sensorsLock:
                    sensor = self.sensors[sensorId]
                    sensor.setSensorData(sensorName, metadata, mqttclient)
            except KeyError:
                self.addSensor(sensorId, sensorType, sensorName, metadata, mqttclient)

    @retryFunc
    def updateSensor(self, sensorId: str, mqttclient: MqttClient, api: IotCloudApi):
        sensorData = api.getSensor(self.locationId, self.deviceId, sensorId)
        try:
            sensor = self.sensors[sensorId]
        except KeyError:
            logger.error(
                f"Sensor: {sensorId} not found in the device: {self.deviceId}. "
                "It was not possible to update it."
            )
            logger.info(f"Sensors: {list(self.sensors.keys())}")
            return

        metadata = sensorData["sensorMetadata"]
        sensorName = sensorData["sensorName"]
        with self.sensorsLock:
            sensor.setSensorData(sensorName, metadata, mqttclient)

    def onSensorUpdated(self, mqttclient: MqttClient, userdata, msg):
        action = msg.payload.decode("utf-8")
        sensorId = msg.topic.split("/")[-2]
        logger.debug(
            f"Received: {action} from location: {self.locationId} and device: {self.deviceId}"
        )
        api = userdata["api"]
        if action == MqttActions.UPDATED:
            Thread(
                target=self.updateSensor,
                args=(sensorId, mqttclient, api),
                daemon=True,
            ).start()

    def run(self, mqttclient: MqttClient, locationData: LocationDataManager):

        # Only run if the device is active
        if not self.status:
            return

        with self.sensorsLock:
            for sensor in self.sensors.values():
                sensor.run(mqttclient, locationData)
