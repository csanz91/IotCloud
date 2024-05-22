import logging
import logging.config
import typing

from paho.mqtt.client import Client as MqttClient

from locationdatamanager import LocationDataManager
from sensor import Sensor

logger = logging.getLogger()


class Notifier(Sensor):

    SENSOR_TYPES = ["notifier"]

    def __init__(
        self,
        baseTopic: str,
        sensorId: str,
        metadata: typing.Dict,
        mqttclient: MqttClient,
        locationData: LocationDataManager,
    ) -> None:
        super().__init__(baseTopic, sensorId, metadata, mqttclient, locationData)

        self.state = False

        self.setSensorData(metadata, mqttclient)

        self.api = locationData.api
        self.locationId = locationData.locationId
        self.sensorId = sensorId
        self.timeZone = locationData.timeZone

        # Set up the relevant MQTT topics
        self.notificationTopic = f"{baseTopic}{sensorId}/aux/notification"
        mqttclient.message_callback_add(
            self.notificationTopic, self.onDeviceNotification
        )

    def subscribe(self, mqttclient: MqttClient) -> None:
        super().subscribe(mqttclient)
        mqttclient.subscribe(self.notificationTopic)

    def unsubscribe(self, mqttclient: MqttClient) -> None:
        super().unsubscribe(mqttclient)
        mqttclient.unsubscribe(self.notificationTopic)

    def onDeviceNotification(self, mqttclient: MqttClient, userdata, msg) -> None:
        try:
            self.api.sendLocationNotification(
                self.locationId,
                self.sensorId,
                "Notification from the device",
                msg.payload.decode("utf-8"),
                self.timeZone,
            )
        except:
            logger.error(f"It was not possible to send the notification: {msg.payload}")
