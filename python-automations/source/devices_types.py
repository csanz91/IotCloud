from datetime import datetime, timedelta
import json
import logging
import time
from typing import Optional
import paho.mqtt.client as mqtt
import utils
import requests
from events import EventStream

logger = logging.getLogger(__name__)


class Switch:
    def __init__(
        self,
        name: str,
        topic: str,
        mqtt_client: mqtt.Client,
        event_streams: Optional[list[EventStream]] = None,
    ):
        self.name = name
        self.topic = topic
        self.state = False
        self.status = False
        self.mqtt_client = mqtt_client
        self.event_streams = event_streams or []

    def subscribe(self):
        topic = f"{self.topic}/state"
        self.mqtt_client.subscribe(topic)
        self.mqtt_client.message_callback_add(topic, self.on_device_state)

        status_topic = "/".join(self.topic.split("/")[:-1]) + "/status"
        self.mqtt_client.subscribe(status_topic)
        self.mqtt_client.message_callback_add(status_topic, self.on_device_status)

    def set_state(self, state: bool):
        self.mqtt_client.publish(f"{self.topic}/setState", state, qos=1, retain=False)

    def on_device_state(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            new_state = utils.decodeBoolean(msg.payload)
            if new_state != self.state:
                self.state = new_state
                for stream in self.event_streams:
                    stream.notify(source=self)
        except Exception:
            logger.error(f"The state received: {msg.payload} is not valid")

    def on_device_status(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            new_status = utils.decodeStatus(msg.payload)
            self.status = new_status
            if not new_status:
                self.state = False

            for stream in self.event_streams:
                stream.notify(source=self)

        except Exception:
            logger.error(f"The status received: {msg.payload} is not valid")


class AnalogSensor:
    def __init__(
        self,
        name: str,
        topic: str,
        mqtt_client: mqtt.Client,
        event_streams: Optional[list[EventStream]] = None,
    ):
        self.name = name
        self.topic = topic
        self.value = 0
        self.mqtt_client = mqtt_client
        self.event_streams = event_streams or []

    def subscribe(self):
        self.mqtt_client.subscribe(self.topic)
        self.mqtt_client.message_callback_add(self.topic, self.on_value)

    def on_value(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            new_value = utils.parseFloat(msg.payload)
            if new_value != self.value:
                self.value = new_value
                for stream in self.event_streams:
                    stream.notify(source=self)
        except Exception:
            logger.error(f"The value received: {msg.payload} is not valid")


class DigitalSensor:
    def __init__(
        self,
        name: str,
        topic: str,
        mqtt_client: mqtt.Client,
        event_streams: Optional[list[EventStream]] = None,
    ):
        self.name = name
        self.topic = topic
        self.state = False
        self.mqtt_client = mqtt_client
        self.event_streams = event_streams or []

    def subscribe(self):
        self.mqtt_client.subscribe(self.topic)
        self.mqtt_client.message_callback_add(self.topic, self.on_state)

    def on_state(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            new_state = utils.decodeBoolean(msg.payload)
            if new_state != self.state:
                self.state = new_state
                for stream in self.event_streams:
                    stream.notify(source=self)
        except:
            logger.error(f"The value received: {msg.payload} is not valid")


class NotifierSensor(DigitalSensor):
    def __init__(self, name: str, topic: str, mqtt_client: mqtt.Client, event_streams: Optional[list[EventStream]] = None):
        super().__init__(name, topic, mqtt_client, event_streams)

    def on_state(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            message = msg.payload.decode()
            for stream in self.event_streams:
                stream.notify(source=self)
        except:
            logger.error(f"Error processing message: {msg.payload}")

    def send_notification(self, message: str):
        self.mqtt_client.publish(self.topic, message, qos=2, retain=False)


class Clock:
    def __init__(self, name: str, topic: str, mqtt_client: mqtt.Client):
        self.name = name
        self.topic = topic
        self.mqtt_client = mqtt_client

    def set_brightness(self, brightness: float):
        self.mqtt_client.publish(self.topic, brightness, qos=2, retain=False)


class PiholeAPIClient:
    def __init__(self, base_url: str, api_token: Optional[str] = None) -> None:
        """
        Initialize Pi-hole API client

        Args:
            base_url: Base URL of your Pi-hole instance (e.g., 'http://192.168.1.100/admin/')
            api_token: Optional API token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.session = requests.Session()

    def is_device_home(self, device_name: str) -> bool:
        """
        Check if a device is present on the network based on recent Pi-hole queries

        Args:
            device_name: Device hostname or IP to check

        Returns:
            bool: True if device has been active within time window, False otherwise
        """
        DEFAULT_QUERY_LIMIT = 200
        DEFAULT_TIME_WINDOW_MINUTES = 5

        api_endpoint = f"{self.base_url}/api.php"
        params: dict[str, int | str] = {"getAllQueries": DEFAULT_QUERY_LIMIT}

        if self.api_token:
            params["auth"] = self.api_token

        try:
            response = self.session.get(api_endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            time_filter = datetime.now() - timedelta(
                minutes=DEFAULT_TIME_WINDOW_MINUTES
            )
            timestamp_filter = time_filter.timestamp()

            return any(
                int(query[0]) >= timestamp_filter
                for query in data.get("data", [])
                if query[3] == device_name
            )

        except requests.RequestException as e:
            logger.error(f"Pi-hole API request failed: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Pi-hole API response: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking device presence: {e}")
            return False


class Presence:
    def __init__(self, name: str, host_name: str, pihole_client: PiholeAPIClient):
        self.name = name
        self.host_name = host_name
        self.pihole_client = pihole_client

    def getPresence(self) -> float | None:
        return self.pihole_client.is_device_home(self.host_name)
