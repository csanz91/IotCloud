import logging
import logging.config
import time
from typing import Optional
from events import EventStream
from devices_types import DigitalSensor, Switch

logger = logging.getLogger()


class Action:
    """
    The Action class represents an action that can be executed in response to events from event streams.

    Attributes:
        name (str): The name of the action.
        streams (list[EventStream]): The event streams that trigger the action.

    Methods:
        execute(): Executes the action.
        action(): Defines the specific action to be performed. Should be overridden by subclasses.
    """

    def __init__(
        self, name: str, streams: list[EventStream], enable_switch: Optional[Switch] = None
    ):
        self.name = name
        self.enable_switch = enable_switch
        for stream in streams:
            stream.subscribe(self.execute)

    def execute(self, event_stream: EventStream):
        try:
            if self.enable_switch is None or self.enable_switch.state:
                self.action(event_stream)
        except Exception:
            logger.error(f"{self.name}: Error executing action", exc_info=True)

    def action(self, event_stream: EventStream):
        pass


class ActionLightSwitch(Action):
    def __init__(
        self,
        name: str,
        streams: list[EventStream],
        enable_switch: Switch | None,
        light_device: Switch,
        presence_in_prev_rooms_devices: list[DigitalSensor],
        presence_state_devices: list[DigitalSensor],
        redetection_window_seconds: float = 10.0,
    ):
        super().__init__(name, streams, enable_switch=enable_switch)
        self.is_triggered = False
        self.trigger_flag_timestamp: float = 0.0
        # Redetection is only allowed after a valid session ended
        self.redetection_deadline: float = 0.0
        self.session_was_valid: bool = False

        self.light_device = light_device

        self.presence_in_prev_rooms_devices = presence_in_prev_rooms_devices
        self.presence_state_devices = presence_state_devices

        self.redetection_window_seconds = redetection_window_seconds

    def action(self, event_stream: EventStream):
        presence_in_prev_rooms = any(device.state for device in self.presence_in_prev_rooms_devices)
        presence_state = any(device.state for device in self.presence_state_devices)

        now = time.monotonic()
        redetection_allowed = self.session_was_valid and (now < self.redetection_deadline)

        # Turn ON logic
        if (
            not self.is_triggered
            and presence_state
            and (presence_in_prev_rooms or redetection_allowed)
        ):
            self.is_triggered = True
            self.light_device.set_state(True)
            # Mark session valid only if activation came from previous room
            if presence_in_prev_rooms:
                self.session_was_valid = True
            return

        # Turn OFF only when presence is lost
        if self.is_triggered and (not presence_state):
            self.light_device.set_state(False)
            self.is_triggered = False
            # Open redetection window only if session was valid
            if self.session_was_valid:
                self.redetection_deadline = now + self.redetection_window_seconds
            return

        # If presence returns while light is already ON, keep it; do nothing on brief false negatives
        # No other action needed
