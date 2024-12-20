
from actions.action import Action
from devices import (
    clock,
    living_room_presence,
    light_sensor,
    clock_brightness_stream,
)
from events import EventStream

class ClockBrightnessControl(Action):
    def action(self, event_stream: EventStream):
        brightness = 0
        presence = living_room_presence.state
        if presence:
            brightness = 0.05 + (light_sensor.value / 1000) * (0.7 - 0.05)
            brightness = max(0, min(brightness, 100))

        clock.set_brightness(brightness)

clock_brightness_control = ClockBrightnessControl(
    "Clock Brightness Control", [clock_brightness_stream]
)