import logging
import logging.config
import typing

from paho.mqtt.client import Client as MqttClient

import utils

logger = logging.getLogger()


class Sensor:
    def __init__(
        self,
        baseTopic: str,
        sensorId: str,
        metadata: typing.Dict,
        mqttclient: MqttClient,
    ) -> None:

        self.baseTopic = baseTopic
        self.sensorId = sensorId
        self.metadata = metadata
        self.status = False

        self.statusTopic = baseTopic + "/status"
        mqttclient.message_callback_add(self.statusTopic, self.onDeviceStatus)

    def subscribe(self, mqttclient: MqttClient) -> None:
        mqttclient.subscribe(self.statusTopic)

    def unsubscribe(self, mqttclient: MqttClient) -> None:
        mqttclient.unsubscribe(self.statusTopic)

    def onDeviceStatus(self, mqttclient: MqttClient, userdata, msg) -> None:
        try:
            self.status = utils.decodeBoolean(msg.payload)
        except:
            logger.error(f"The status received: {msg.payload} is not valid")

    def setSensorData(self, metadata: typing.Dict) -> None:
        self.metadata = metadata

    def run(self):
        pass
