from actions.action import Action
from devices_types import Switch
from devices import (
    clock,
    living_room_presence,
    light_sensor,
    clock_brightness_stream,
    enable_madrid_automations,
)
from events import EventStream


class ClockBrightnessControl(Action):
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Switch):
        super().__init__(name, streams, enable_switch=enable_switch)

    def action(self, event_stream: EventStream):
        brightness = 0
        presence = living_room_presence.state
        if presence:
            brightness = 0.05 + (light_sensor.value / 1000) * (0.7 - 0.05)
            brightness = max(0, min(brightness, 100))

        clock.set_brightness(brightness)


clock_brightness_control = ClockBrightnessControl(
    "Clock Brightness Control",
    [clock_brightness_stream],
    enable_switch=enable_madrid_automations,
)
