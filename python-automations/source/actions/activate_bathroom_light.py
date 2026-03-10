import logging

from devices import (
    activate_bathroom_stream,
    bathroom_light,
    bathroom_presence,
    bedroom_presence,
    enable_madrid_automations,
    living_room_presence_center,
    office_presence,
)

from actions.action import ActionLightSwitch

logger = logging.getLogger()


activate_bathroom_light = ActionLightSwitch(
    "Activate Bathroom Light",
    [activate_bathroom_stream],
    enable_switch=None,
    light_device=bathroom_light,
    presence_in_prev_rooms_devices=[
        living_room_presence_center,
        bedroom_presence,
        office_presence,
    ],
    presence_state_devices=[bathroom_presence],
)
