import logging
from actions.action import Action
from devices_types import APIOrderDevice, Switch
from devices import (
    living_room_light,
    living_room_center_light,
    living_room_presence,
    light_sensor,
    activate_living_room_stream,
    enable_madrid_automations,
)
from events import EventStream

logger = logging.getLogger()


class ActivateLivingRoom(Action):
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Switch):
        super().__init__(name, streams, enable_switch=enable_switch)
        self.trigger_flag = False

    def action(self, event_stream: EventStream):

        source = event_stream.source
        if isinstance(source, APIOrderDevice):
            if source.last_action == "toggle":
                if living_room_light.state:
                    living_room_light.set_state(False)
                else:
                    living_room_light.set_state(True)
            elif source.last_action == "activate":
                living_room_light.set_state(True)
            elif source.last_action == "deactivate":
                living_room_light.set_state(False)

        presence = living_room_presence.state
        if not presence:
            self.trigger_flag = False
            return

        threshold = 1.5
        is_dark = light_sensor.value < threshold or living_room_center_light.state

        if not self.trigger_flag and presence and is_dark:
            living_room_light.set_state(True)
            # Setting the flag here will turn on the light if being in the room and becomes dark
            self.trigger_flag = True


activate_living_room = ActivateLivingRoom(
    "Activate Living Room",
    [activate_living_room_stream],
    enable_switch=enable_madrid_automations,
)
