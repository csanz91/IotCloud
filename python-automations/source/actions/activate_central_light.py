import logging
from actions.action import Action
from devices_types import Switch
from devices import (
    living_room_light,
    living_room_center_light,
    living_room_presence,
    living_room_presence_center,
    light_sensor,
    activate_central_light_stream,
    enable_madrid_automations,
)
from config import LIVING_ROOM_DARK_THRESHOLD
from events import EventStream

from actions import is_night_time

logger = logging.getLogger()


class ActivateCentralLight(Action):
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Switch):
        super().__init__(name, streams, enable_switch=enable_switch)
        self.trigger_flag = False

    def action(self, event_stream: EventStream):
        is_dark = (light_sensor.value < LIVING_ROOM_DARK_THRESHOLD) and is_night_time()
        state = (
            living_room_presence_center.state
            and not living_room_light.state
            and is_dark
        )

        if (
            not living_room_presence_center.state
            and not living_room_light.state
            and not living_room_presence.state
        ):
            self.trigger_flag = False

        if not self.trigger_flag and state:
            self.trigger_flag = True
            living_room_center_light.set_state(True)
        elif not state:
            living_room_center_light.set_state(False)


activate_central_light = ActivateCentralLight(
    "Activate Living Central Light",
    [activate_central_light_stream],
    enable_switch=enable_madrid_automations,
)
