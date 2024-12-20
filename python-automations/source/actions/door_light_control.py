import logging
from actions.action import Action
from devices import (
    living_room_light,
    light_sensor,
    door_activation_stream,
)
from actions.house_occupancy_tracker import house_occupancy_tracker
from events import EventStream

logger = logging.getLogger()

class DoorLightControl(Action):
    def action(self, event_stream: EventStream):
        if not house_occupancy_tracker.is_occupied and light_sensor.value < 1:
            living_room_light.set_state(True)
            logger.info(f"{self.name}: Light activated by door sensor")

door_light_control = DoorLightControl(
    "Door Light Control", [door_activation_stream]
)
