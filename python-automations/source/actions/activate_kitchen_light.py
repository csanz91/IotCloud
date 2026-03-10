import logging

from devices import (
    activate_kitchen_stream,
    kitchen_light,
    kitchen_presence,
    living_room_presence_center,
    always_off_switch,
)

from actions.action import ActionLightSwitch

logger = logging.getLogger()


activate_kitchen_light = ActionLightSwitch(
    "Activate Kitchen Light",
    [activate_kitchen_stream],
    enable_switch=always_off_switch,
    light_device=kitchen_light,
    presence_in_prev_rooms_devices=[
        living_room_presence_center,
    ],
    presence_state_devices=[kitchen_presence],
)
