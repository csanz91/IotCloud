import logging
from actions.action import Action
from devices_types import Switch
from devices import (
    living_room_light,
    living_room_presence,
    living_room_presence_center,
    # bedroom_light,
    # office_light,
    # bathroom_light,
    # kitchen_light,
    deactivate_living_room_stream,
    enable_madrid_automations,
)
from events import EventStream

logger = logging.getLogger()

class DeactivateLivingRoom(Action):
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Switch):
        super().__init__(name, streams, enable_switch=enable_switch)
        self.trigger_flag = False

    def action(self, event_stream: EventStream):
        presence = living_room_presence.state or living_room_presence_center.state
        # other_lights_on = bedroom_light.state or office_light.state or bathroom_light.state or kitchen_light.state

        if presence:
            self.trigger_flag = False
            return

        # if not self.trigger_flag and not presence and other_lights_on:
        if not self.trigger_flag and not presence:
            self.trigger_flag = True
            living_room_light.set_state(False)

deactivate_living_room = DeactivateLivingRoom(
    "Deactivate Living Room", [deactivate_living_room_stream], enable_switch=enable_madrid_automations
)
