import logging
import logging.config
import typing

from paho.mqtt.client import Client as MqttClient

from locationdatamanager import LocationDataManager
from schedule import Schedule
from sensor import Sensor

logger = logging.getLogger()


class Toogle(Sensor, Schedule):

    SENSOR_TYPES = ["toogle"]

    def __init__(
        self,
        baseTopic: str,
        sensorId: str,
        metadata: typing.Dict,
        mqttclient: MqttClient,
        locationData: LocationDataManager
    ) -> None:
        super().__init__(baseTopic, sensorId, metadata, mqttclient, locationData)

        self.setSensorData(metadata, mqttclient)

        # Set up the relevant MQTT topics
        self.setStateTopic = f"{baseTopic}{sensorId}/aux/setToogle"

        # Enable the retrieval of the sun schedule
        locationData.registerSunSchedule()

    def setState(self,  mqttclient: MqttClient, state) -> None:
        action = "up" if state else "down"
        mqttclient.publish(self.setStateTopic, action, qos=1, retain=False)

    # Requiered by the Schedule class
    def setValue(self,  mqttclient: MqttClient, value) -> None:
        pass

    def run(self, mqttclient: MqttClient, locationData: LocationDataManager) -> None:
        self.runSchedule(mqttclient, locationData)
