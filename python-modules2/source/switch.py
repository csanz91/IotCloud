import logging
import logging.config
import typing

from paho.mqtt.client import Client as MqttClient

from locationdatamanager import LocationDataManager
from sensor import Sensor
from timer import Timer
from schedule import Schedule
import utils

logger = logging.getLogger()


class Switch(Sensor, Timer, Schedule):

    SENSOR_TYPES = ["switch", "led", "ledrgb"]

    def __init__(
        self,
        baseTopic: str,
        sensorId: str,
        sensorName: str,
        metadata: typing.Dict,
        mqttclient: MqttClient,
        locationData: LocationDataManager
    ) -> None:
        super().__init__(baseTopic, sensorId, sensorName, metadata, mqttclient, locationData)

        self.state = False

        self.setSensorData(sensorName, metadata, mqttclient)

        # Set up the relevant MQTT topics
        self.stateTopic = f"{baseTopic}{sensorId}/state"
        self.setStateTopic = f"{baseTopic}{sensorId}/setState"
        mqttclient.message_callback_add(self.stateTopic, self.onDeviceState)

        # Enable the retrieval of the sun schedule
        locationData.registerSunSchedule()

    def subscribe(self, mqttclient: MqttClient) -> None:
        super().subscribe(mqttclient)
        mqttclient.subscribe(self.stateTopic)

    def unsubscribe(self, mqttclient: MqttClient) -> None:
        super().unsubscribe(mqttclient)
        mqttclient.unsubscribe(self.stateTopic)

    def onDeviceState(self, mqttclient: MqttClient, userdata, msg) -> None:
        try:
            self.state = utils.decodeBoolean(msg.payload)
        except:
            logger.error(f"The state received: {msg.payload} is not valid")

    def setState(self,  mqttclient: MqttClient, state) -> None:
        mqttclient.publish(self.setStateTopic, state, qos=1, retain=False)

    # Requiered by the Schedule class
    def setValue(self,  mqttclient: MqttClient, value) -> None:
        pass

    def run(self, mqttclient: MqttClient, locationData: LocationDataManager) -> None:
        self.runTimer(mqttclient)
        self.runSchedule(mqttclient, locationData)
