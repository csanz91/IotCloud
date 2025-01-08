import time
from actions.action import Action
from devices import (
    living_room_presence,
    living_room_presence_center,
    living_room_light,
    bedroom_light,
    bedroom_presence,
    office_presence_2 as office_presence,
    office_light,
    bathroom_light,
    kitchen_light,
    occupancy_stream_in,
    occupancy_stream,
)
from events import EventStream


class HouseOccupancyTracker(Action):
    def __init__(self, name: str, streams: list[EventStream]):
        super().__init__(name, streams)
        self.is_occupied = False
        self.last_occupied_time = time.time()

    def action(self, event_stream: EventStream):
        # Check presence sensors
        presence = (
            living_room_presence.state
            or living_room_presence_center.state
            or bedroom_presence.state
            or office_presence.state
        )
        if presence:
            self.last_occupied_time = time.time()

        # Check if any light is on
        any_light_on = (
            living_room_light.state
            or bedroom_light.state
            or office_light.state
            or bathroom_light.state
            or kitchen_light.state
        )

        new_occupied_state = presence or any_light_on
        if new_occupied_state != self.is_occupied:
            self.is_occupied = new_occupied_state
            occupancy_stream.notify(self.name)


house_occupancy_tracker = HouseOccupancyTracker(
    "House Occupancy Tracker", [occupancy_stream_in]
)
