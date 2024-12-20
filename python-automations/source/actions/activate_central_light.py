import logging
from actions.action import Action
from devices import (
    living_room_light,
    living_room_center_light,
    living_room_presence,
    living_room_presence_center,
    light_sensor,
    activate_central_light_stream,
)
from events import EventStream

logger = logging.getLogger()

class ActivateCentralLight(Action):
    def __init__(self, name: str, streams: list[EventStream]):
        super().__init__(name, streams)
        self.trigger_flag = False

    def action(self, event_stream: EventStream):
        is_dark = light_sensor.value < 1.5
        state = living_room_presence_center.state and not living_room_light.state and is_dark

        if not living_room_presence_center.state and not living_room_light.state and not living_room_presence.state:
            self.trigger_flag = False

        if not self.trigger_flag and state:
            self.trigger_flag = True
            living_room_center_light.set_state(True)
        elif not state:
            living_room_center_light.set_state(False)

activate_central_light = ActivateCentralLight(
    "Activate Living Central Light", [activate_central_light_stream]
)
