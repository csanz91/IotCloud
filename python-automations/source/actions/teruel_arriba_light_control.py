import logging
from typing import Optional
from actions.action import Action
from devices_types import Switch
from devices import (
    teruel_puerta_arriba_light,
    teruel_puerta_arriba_brightness,
    teruel_puerta_arriba_presence,
    teruel_puerta_arriba_presence_PIR,
    teruel_puerta_arriba_stream,
)
from events import EventStream
from config import TERUEL_DARK_THRESHOLD

logger = logging.getLogger()

class TeruelLightControl(Action):

    def __init__(
        self, name: str, streams: list[EventStream], enable_switch: Optional[Switch]=None
    ):
        super().__init__(name, streams, enable_switch)
        self.activate_light_executed = False

    def action(self, event_stream: EventStream):
        is_dark = teruel_puerta_arriba_brightness.value < TERUEL_DARK_THRESHOLD

        is_present = teruel_puerta_arriba_presence.state and teruel_puerta_arriba_presence_PIR.state
        not_present = not teruel_puerta_arriba_presence.state and not teruel_puerta_arriba_presence_PIR.state

        # Reset manual off flag when room becomes empty
        if not_present:
            teruel_puerta_arriba_light.set_state(False)
            self.activate_light_executed = False

        # Turn on light conditions
        if is_present and is_dark and not self.activate_light_executed:
            teruel_puerta_arriba_light.set_state(True)
            self.activate_light_executed = True


teruel_arriba_light_control = TeruelLightControl(
    "Teruel Puerta Arriba Light Control",
    [teruel_puerta_arriba_stream],
)
