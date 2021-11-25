import logging
import logging.config
import typing

from paho.mqtt.client import Client as MqttClient

from locationdatamanager import LocationDataManager

logger = logging.getLogger()


class Sensor:

    SENSOR_TYPES = ["generic"]

    def __init__(
        self,
        baseTopic: str,
        sensorId: str,
        metadata: typing.Dict,
        mqttclient: MqttClient,
        locationData: LocationDataManager
    ) -> None:
        super().__init__()
        self.baseTopic = baseTopic
        self.sensorId = sensorId
        self.metadata = metadata

        logger.info(f"Created sensor with id: {self.sensorId}")

    def subscribe(self, mqttclient: MqttClient) -> None:
        pass

    def unsubscribe(self, mqttclient: MqttClient) -> None:
        pass

    def setSensorData(self, metadata: typing.Dict, mqttclient: MqttClient) -> None:
        logger.info(f"Setting sensor data for {self.sensorId}, metadata: {metadata}", )
        self.metadata = metadata

    def run(self, mqttclient: MqttClient, locationData: LocationDataManager) -> None:
        pass
