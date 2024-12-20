import logging
from actions.action import Action
from devices import office_light, office_light_brightness, control_office_light_stream, office_presence
from events import EventStream

logger = logging.getLogger()

class OfficeLightControl(Action):

    def __init__(self, name: str, streams: list[EventStream]):
        super().__init__(name, streams)
        self.activate_light_executed = False
        self.deactivate_light_executed = False

    def action(self, event_stream: EventStream):
        is_dark = office_light_brightness.value < 1.0
        is_very_bright = office_light_brightness.value > 8.0
        is_present = office_presence.state

        # Reset manual off flag when room becomes empty
        if not is_present:
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
    "Office Light Control", [control_office_light_stream]
)
