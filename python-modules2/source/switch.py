import logging
import logging.config
import typing

from paho.mqtt.client import Client as MqttClient

from sensor import Sensor
from timer import Timer
import utils

logger = logging.getLogger()


class Switch(Sensor, Timer):
    def __init__(
        self,
        baseTopic: str,
        sensorId: str,
        metadata: typing.Dict,
        mqttclient: MqttClient,
    ) -> None:
        super().__init__(baseTopic, sensorId, metadata, mqttclient)

        self.state = False

        self.stateTopic = f"{baseTopic}{sensorId}/state"
        self.setStateTopic = f"{baseTopic}{sensorId}/setState"
        mqttclient.message_callback_add(self.stateTopic, self.onDeviceState)

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

    def setState(self, mqttClient, state):
        mqttClient.publish(self.setStateTopic, state, qos=1, retain=True)

    def run(self, mqttclient: MqttClient) -> None:
        self.runTimer(mqttclient)
