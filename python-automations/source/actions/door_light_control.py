import logging
from actions.action import Action
from devices_types import Switch
from devices import (
    living_room_light,
    light_sensor,
    door_activation_stream,
    enable_madrid_automations,
)
from actions.house_occupancy_tracker import house_occupancy_tracker
from events import EventStream

logger = logging.getLogger()

class DoorLightControl(Action):
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Switch):
        super().__init__(name, streams, enable_switch=enable_switch)

    def action(self, event_stream: EventStream):
        if not house_occupancy_tracker.is_occupied and light_sensor.value < 1:
            living_room_light.set_state(True)
            logger.info(f"{self.name}: Light activated by door sensor")

door_light_control = DoorLightControl(
    "Door Light Control", [door_activation_stream], enable_switch=enable_madrid_automations
)
