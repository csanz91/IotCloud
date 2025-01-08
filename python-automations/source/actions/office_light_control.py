import logging
from actions.action import Action
from devices_types import Switch
from devices import (
    office_light,
    office_light_brightness,
    control_office_light_stream,
    office_presence as office_presence,
    living_room_presence_center,
    bedroom_presence,
    bathroom_light,
    enable_madrid_automations,
)
from events import EventStream

logger = logging.getLogger()

class OfficeLightControl(Action):

    def __init__(
        self, name: str, streams: list[EventStream], enable_switch: Switch
    ):
        super().__init__(name, streams)
        self.activate_light_executed = False
        self.deactivate_light_executed = False
        self.enable_switch = enable_switch

    def action(self, event_stream: EventStream):
        is_dark = office_light_brightness.value < 1.0
        is_very_bright = office_light_brightness.value > 8.0
        is_present = office_presence.state

        presence_in_other_rooms = living_room_presence_center.state or bedroom_presence.state or bathroom_light.state

        # Reset manual off flag when room becomes empty
        if not is_present and presence_in_other_rooms:
            self.activate_light_executed = False
            self.deactivate_light_executed = False
            if office_light.state:
                office_light.set_state(False)

        # Turn on light conditions
        if is_present and is_dark and not self.activate_light_executed:
            office_light.set_state(True)
            self.activate_light_executed = True

        # Turn off light when it gets bright
        if not self.deactivate_light_executed and is_very_bright:
            office_light.set_state(False)
            self.deactivate_light_executed = True


office_light_control = OfficeLightControl(
    "Office Light Control", [control_office_light_stream], enable_switch=enable_madrid_automations
)
