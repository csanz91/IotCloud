from datetime import datetime, timedelta
import logging
import time
from typing import Optional
import paho.mqtt.client as mqtt
import utils
from events import EventStream
from pihole6api import PiHole6Client

logger = logging.getLogger(__name__)


class Sensor:
    # Static dictionary to track shared status callbacks
    _status_callbacks = {}

    def __init__(
        self,
        name: str,
        topic: str,
        mqtt_client: mqtt.Client,
        event_streams: Optional[list[EventStream]] = None,
    ):
        self.name = name
        self.topic = topic
        self._state = False
        self.status = False
        self.mqtt_client = mqtt_client
        self.event_streams = event_streams or []

    def subscribe(self):
        tags = utils.getTags(self.topic)
        status_topic = f"v1/{tags['locationId']}/{tags['deviceId']}/status"

        # Check if we already have a callback for this status topic
        if status_topic not in Sensor._status_callbacks:
            self.mqtt_client.subscribe(status_topic)
            self.mqtt_client.message_callback_add(
                status_topic, self._shared_status_callback
            )
            Sensor._status_callbacks[status_topic] = []

        # Add this instance to the callbacks list
        Sensor._status_callbacks[status_topic].append(self)

    @staticmethod
    def _shared_status_callback(
        mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        # Find all sensors that share this topic and notify them
        topic = msg.topic
        if topic in Sensor._status_callbacks:
            for sensor in Sensor._status_callbacks[topic]:
                try:
                    new_status = utils.decodeStatus(msg.payload)
                    sensor.status = new_status

                    for stream in sensor.event_streams:
                        stream.notify(source=sensor)

                except Exception:
                    logger.error(f"The status received: {msg.payload} is not valid")


class Switch(Sensor):
    def __init__(
        self,
        name: str,
        topic: str,
        mqtt_client: mqtt.Client,
        event_streams: Optional[list[EventStream]] = None,
    ):
        super().__init__(name, topic, mqtt_client, event_streams)

        self._state_timestamp = 0

    def subscribe(self):
        super().subscribe()

        topic = f"{self.topic}/state"
        self.mqtt_client.subscribe(topic)
        self.mqtt_client.message_callback_add(topic, self.on_state)

    @property
    def state(self) -> bool:
        return self._state and self.status

    @property
    def recent_state(self) -> bool:
        return self.state or time.time() - self._state_timestamp < 6

    def set_state(self, state: bool):
        self.mqtt_client.publish(f"{self.topic}/setState", state, qos=1, retain=False)

    def on_state(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            new_state = utils.decodeBoolean(msg.payload)
            if new_state != self._state:
                self._state = new_state
                self._state_timestamp = time.time()
                for stream in self.event_streams:
                    stream.notify(source=self)
        except Exception:
            logger.error(
                f"The state received: {msg.payload} is not valid", exc_info=True
            )


class AnalogSensor(Sensor):
    def __init__(
        self,
        name: str,
        topic: str,
        mqtt_client: mqtt.Client,
        event_streams: Optional[list[EventStream]] = None,
        notify_same_value: bool = False,
    ):
        super().__init__(name, topic, mqtt_client, event_streams)
        self.value = 0.0
        self.notify_same_value = notify_same_value

    def subscribe(self):
        super().subscribe()
        self.mqtt_client.subscribe(self.topic)
        self.mqtt_client.message_callback_add(self.topic, self.on_value)

    def on_value(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            new_value = utils.parseFloat(msg.payload)
            if new_value != self.value or self.notify_same_value:
                self.value = new_value
                for stream in self.event_streams:
                    stream.notify(source=self)
        except Exception:
            logger.error(f"The value received: {msg.payload} is not valid")


class DigitalSensor(Sensor):
    def subscribe(self):
        super().subscribe()
        self.mqtt_client.subscribe(self.topic)
        self.mqtt_client.message_callback_add(self.topic, self.on_state)

    @property
    def state(self) -> bool:
        return self._state and self.status

    def on_state(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            new_state = utils.decodeBoolean(msg.payload)
            if new_state != self._state:
                self._state = new_state
                for stream in self.event_streams:
                    stream.notify(source=self)
        except Exception:
            logger.error(f"The value received: {msg.payload} is not valid")


class NotifierSensor(DigitalSensor):
    def __init__(
        self,
        name: str,
        topic: str,
        mqtt_client: mqtt.Client,
        event_streams: Optional[list[EventStream]] = None,
    ):
        super().__init__(name, topic, mqtt_client, event_streams)

    def on_state(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            for stream in self.event_streams:
                stream.notify(source=self)
        except Exception:
            logger.error(f"Error processing message: {msg.payload}")

    def send_notification(self, message: str):
        self.mqtt_client.publish(self.topic, message, qos=2, retain=False)


class BrightnessDevice(AnalogSensor):
    def __init__(
        self,
        name: str,
        topic: str,
        mqtt_client: mqtt.Client,
        event_streams: Optional[list[EventStream]] = None,
    ):
        super().__init__(name, topic, mqtt_client, event_streams)
        self.topic = f"{topic}/aux/brightness"
        self.set_brightness_topic = f"{topic}/aux/setBrightness"
        self.mqtt_client = mqtt_client
        self.state = True

    def set_brightness(self, brightness: float):
        self.mqtt_client.publish(
            self.set_brightness_topic, brightness, qos=2, retain=False
        )


class PiholeAPIClient:
    def __init__(self, base_url: str, password: str) -> None:
        """
        Initialize Pi-hole API client

        Args:
            base_url: Base URL of your Pi-hole instance (e.g., 'http://192.168.1.100/admin/')
            password: Password for authentication with Pi-hole
        """
        self.client = PiHole6Client(base_url, password)
        self.last_seen_devices = {}

    def refresh_last_seen_devices(self):
        """
        Fetch and update the list of devices from Pi-hole API with their last seen timestamps
        Updates the internal last_seen_devices dictionary
        """
        last_seen_devices = {}
        try:
            devices_response = self.client.network_info.get_devices(
                max_devices=20, max_addresses=1
            )

            for device in devices_response["devices"]:
                if not device.get("ips") or len(device["ips"]) == 0:
                    continue

                hostname = device["ips"][0]["name"]
                last_seen = device["lastQuery"]
                last_seen_devices[hostname] = last_seen

        except Exception as e:
            logger.error(f"Failed to fetch devices from Pi-hole: {e}")
            return

        self.last_seen_devices = last_seen_devices

    def is_device_home(self, hostname: str, time_window=300) -> bool:
        """
        Check if a device is present on the network based on its last seen timestamp

        Args:
            hostname: Device hostname or IP to check
            time_window: Time window in seconds to consider device as present

        Returns:
            bool: True if device has been active within time window, False otherwise
        """
        time_filter = datetime.now() - timedelta(seconds=time_window)
        timestamp_filter = time_filter.timestamp()

        last_seen = self.last_seen_devices.get(hostname, 0)
        is_home = last_seen > timestamp_filter

        logger.info(f"Device {hostname} last seen at {last_seen}, is home: {is_home}")
        return is_home


# Global registry to track all API order devices
api_order_devices: dict[str, "APIOrderDevice"] = {}


class APIOrderDevice:
    """
    Device that listens to orders via an API endpoint.
    Each instance represents a specific device that can receive orders.

    Attributes:
        name: Device identifier used in API calls
        event_streams: List of EventStream instances for notifications
        last_action: Stores the last action received
    """

    def __init__(self, name: str, event_streams: Optional[list[EventStream]] = None):
        self.name = name
        self.event_streams = event_streams or []
        self.last_action: str | None = None
        # Register this device in the global registry
        api_order_devices[name] = self

    def subscribe(self):
        pass

    @staticmethod
    def process_order(device_name: str, action: str) -> bool:
        """
        Process an order received via API

        Args:
            device_name: Name of the target device
            action: Action to perform (toggle, activate, deactivate)

        Returns:
            bool: True if order was processed, False if device not found
        """
        if device_name not in api_order_devices:
            return False

        device = api_order_devices[device_name]
        if action not in ["toggle", "activate", "deactivate"]:
            return False

        device.last_action = action
        # Notify event streams
        for stream in device.event_streams:
            stream.notify(source=device)
        return True


class FrigateCamera(Sensor):
    """
    Frigate camera device that monitors person detection and can be enabled/disabled
    to save power when house is occupied
    """

    def __init__(
        self,
        name: str,
        camera_name: str,
        mqtt_client: mqtt.Client,
        event_streams: Optional[list[EventStream]] = None,
    ):
        # Topic for receiving person detection count
        topic = f"frigate/{camera_name}/person"
        super().__init__(name, topic, mqtt_client, event_streams)

        self.camera_name = camera_name
        self.person_count = 0
        self.enabled = True
        self.enabled_topic = f"frigate/{camera_name}/enabled/set"
        self.enabled_state_topic = f"frigate/{camera_name}/enabled/state"

    def subscribe(self):
        # Subscribe to person detection topic
        self.mqtt_client.subscribe(self.topic)
        self.mqtt_client.message_callback_add(self.topic, self.on_person_detection)
        self.mqtt_client.subscribe(self.enabled_state_topic)
        self.mqtt_client.message_callback_add(
            self.enabled_state_topic, self.on_enabled_state
        )

    def on_person_detection(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            new_count = int(msg.payload.decode())
            if new_count != self.person_count:
                self.person_count = new_count
                # Trigger alarm if people detected (>0)
                if new_count > 0:
                    logger.warning(f"{self.name}: Person detected! Count: {new_count}")
                    for stream in self.event_streams:
                        stream.notify(source=self)
                else:
                    logger.info(f"{self.name}: No persons detected")
        except Exception as e:
            logger.error(
                f"Error processing person detection: {msg.payload}, error: {e}"
            )

    def on_enabled_state(
        self, mqttclient: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            self.enabled = msg.payload.decode().lower() == "on"
            logger.info(
                f"{self.name}: Camera is {'enabled' if self.enabled else 'disabled'}"
            )
        except Exception as e:
            logger.error(f"Error processing enabled state: {msg.payload}, error: {e}")

    def set_enabled(self, enabled: bool):
        """Enable or disable the camera"""

        if enabled == self.enabled:
            logger.info(
                f"{self.name}: Camera already {'enabled' if enabled else 'disabled'}"
            )
            return

        state = "ON" if enabled else "OFF"
        self.mqtt_client.publish(self.enabled_topic, state, qos=1, retain=True)
        self.enabled = enabled
        logger.info(f"{self.name}: Camera {'enabled' if enabled else 'disabled'}")

    @property
    def is_person_detected(self) -> bool:
        """Check if any person is currently detected"""
        return self.person_count > 0
