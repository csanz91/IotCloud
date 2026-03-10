from actions.action import Action
from devices_types import APIOrderDevice, Switch
from devices import (
    clock,
    living_room_presence,
    light_sensor,
    clock_brightness_stream,
    enable_madrid_automations,
    living_room_light,
    living_room_presence_center,
    temp_box,
)
from config import CLOCK_MIN_BRIGHTNESS, CLOCK_MAX_BRIGHTNESS, CLOCK_BRIGHTNESS_SCALE
from events import EventStream


class ClockBrightnessControl(Action):
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Switch):
        super().__init__(name, streams, enable_switch=enable_switch)
        self.trigger_flag = False

    def action(self, event_stream: EventStream):
        source = event_stream.source
        if isinstance(source, APIOrderDevice):
            clock.state = not living_room_light.state

        presence = living_room_presence.state
        if source == living_room_presence and not presence:
            clock.state = True

        # If no presence detected, reset trigger flag
        if (
            not living_room_presence.state
            and not living_room_presence_center.state
            and self.trigger_flag
        ):
            self.trigger_flag = False

        # Set the brightness if there is actual presence in the living room or until the person leaves the room
        brightness = 0
        if clock.state and (
            living_room_presence.state or self.trigger_flag and living_room_presence_center.state
        ):
            brightness = CLOCK_MIN_BRIGHTNESS + (light_sensor.value / CLOCK_BRIGHTNESS_SCALE) * (
                CLOCK_MAX_BRIGHTNESS - CLOCK_MIN_BRIGHTNESS
            )
            brightness = max(0, min(brightness, 100))

        if brightness > CLOCK_MIN_BRIGHTNESS:
            self.trigger_flag = True

        clock.set_brightness(brightness)
        temp_box.set_brightness(brightness)


clock_brightness_control = ClockBrightnessControl(
    "Clock Brightness Control",
    [clock_brightness_stream],
    enable_switch=enable_madrid_automations,
)
