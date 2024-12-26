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
        sensorName: str,
        metadata: typing.Dict,
        mqttclient: MqttClient,
        locationData: LocationDataManager,
    ) -> None:
        super().__init__(baseTopic, sensorId, sensorName, metadata, mqttclient, locationData)

        self.state = False

        self.setSensorData(sensorName, metadata, mqttclient)

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
        logger.info(f"{self.sensorName}: {msg.payload.decode('utf-8').format(sensor_name=self.sensorName)}")
        try:
            self.api.sendLocationNotification(
                self.locationId,
                self.sensorId,
                self.sensorName,
                msg.payload.decode("utf-8").format(sensor_name=self.sensorName),
                self.timeZone,
            )
        except:
            logger.error(f"It was not possible to send the notification: {msg.payload}", exc_info=True)
