import logging
from actions.action import Action
from devices_types import Switch
from devices import (
    bedroom_light,
    bedroom_presence,
    bedroom_auto,
    light_sensor,
    bedroom_light_stream,
    living_room_light,
    bed_led,
)
from config import BEDROOM_DARK_THRESHOLD
from events import EventStream

from actions import is_night_time

logger = logging.getLogger()


class ActivateBedroom(Action):
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Switch):
        super().__init__(name, streams)
        self.activate_light_executed = False
        self.enable_switch = enable_switch

    def action(self, event_stream: EventStream):
        is_dark = (
            light_sensor.value < BEDROOM_DARK_THRESHOLD
            or living_room_light.recent_state
        ) and is_night_time()
        is_present = bedroom_presence.state

        # Reset manual off flag when room becomes empty
        if not is_present:
            self.activate_light_executed = False
            if bedroom_light.state:
                bedroom_light.set_state(False)

            if bed_led.value > 0:
                bed_led.set_brightness(0)

        # Turn on light conditions
        if is_present and is_dark and not self.activate_light_executed:
            bedroom_light.set_state(True)
            self.activate_light_executed = True


activate_bedroom_light = ActivateBedroom(
    "Activate Bedroom Room",
    [bedroom_light_stream],
    enable_switch=bedroom_auto,
)
