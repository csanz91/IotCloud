from actions.action import Action
from devices_types import Switch
from devices import (
    bed_led,
    bed_brightness,
    bed_brightness_stream,
    enable_madrid_automations,
)
from events import EventStream

import logging

logger = logging.getLogger()


class BedBrightnessControl(Action):
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Switch):
        super().__init__(name, streams, enable_switch=enable_switch)

    def action(self, event_stream: EventStream):
        brightness_diff = bed_brightness.value
        brightness = bed_led.value
        logger.info(f"Current brightness: {brightness}")
        if brightness_diff == 255:
            if brightness == 0:
                new_brightness = 0.8
            else:
                new_brightness = 0
        else:
            new_brightness = brightness + brightness_diff / 100.0
        new_brightness = max(0, min(new_brightness, 1.0))

        logger.info(f"New brightness: {new_brightness}")

        bed_led.set_brightness(new_brightness)


bed_brightness_control = BedBrightnessControl(
    "Bed Brightness Control",
    [bed_brightness_stream],
    enable_switch=enable_madrid_automations,
)
