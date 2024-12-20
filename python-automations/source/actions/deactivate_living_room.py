import logging
from actions.action import Action
from devices import (
    living_room_light,
    living_room_presence,
    living_room_presence_center,
    # bedroom_light,
    # office_light,
    # bathroom_light,
    # kitchen_light,
    deactivate_living_room_stream,
)
from events import EventStream

logger = logging.getLogger()

class DeactivateLivingRoom(Action):
    def __init__(self, name: str, streams: list[EventStream]):
        super().__init__(name, streams)
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
            logger.info(f"{self.name}: Living room deactivated")

deactivate_living_room = DeactivateLivingRoom(
    "Deactivate Living Room", [deactivate_living_room_stream]
)
