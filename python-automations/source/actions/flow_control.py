import logging
from actions.action import Action
from devices_types import Switch
from devices import (
    bedroom_light,
    bathroom_light,
    living_room_presence_center,
    living_room_center_light,
    living_room_light,
    office_light,
    kitchen_light,
    flow_control_stream,
    home_alone,
)
from events import EventStream

logger = logging.getLogger()


class FlowControl(Action):
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Switch):
        super().__init__(name, streams, enable_switch=enable_switch)

    def action(self, event_stream: EventStream):

        # From kitchen to living room
        if (
            event_stream.source == living_room_presence_center
            and living_room_presence_center.state
            and kitchen_light.state
        ):
            kitchen_light.set_state(False)
            logger.info(f"{self.name}: Kitchen light turned off")

        # From living room to kitchen
        if (
            event_stream.source == kitchen_light
            and kitchen_light.state
            and (living_room_center_light.state or living_room_light.state)
        ):
            living_room_center_light.set_state(False)
            living_room_light.set_state(False)
            logger.info(f"{self.name}: Living room light turned off")

        # From living room to bedroom
        if (
            event_stream.source == bedroom_light
            and bedroom_light.state
            and (living_room_center_light.state or living_room_light.state)
        ):
            living_room_center_light.set_state(False)
            living_room_light.set_state(False)
            logger.info(f"{self.name}: Living room light turned off")

        # From living room to bathroom
        if (
            event_stream.source == bathroom_light
            and bathroom_light.state
            and (living_room_center_light.state or living_room_light.state)
        ):
            living_room_center_light.set_state(False)
            living_room_light.set_state(False)
            logger.info(f"{self.name}: Living room light turned off")

        # From living room to office
        if (
            event_stream.source == office_light
            and office_light.state
            and (living_room_center_light.state or living_room_light.state)
        ):
            living_room_center_light.set_state(False)
            living_room_light.set_state(False)
            logger.info(f"{self.name}: Living room light turned off")

        # From bedroom to living room
        if (
            event_stream.source == living_room_center_light
            and living_room_center_light.state
            and bedroom_light.state
        ):
            bedroom_light.set_state(False)
            logger.info(f"{self.name}: Bedroom light turned off")

        # From bedroom to bathroom
        if (
            event_stream.source == bathroom_light
            and bathroom_light.state
            and bedroom_light.state
        ):
            bedroom_light.set_state(False)
            logger.info(f"{self.name}: Bedroom light turned off")

        # From bedroom to office
        if (
            event_stream.source == office_light
            and office_light.state
            and bedroom_light.state
        ):
            bedroom_light.set_state(False)
            logger.info(f"{self.name}: Bedroom light turned off")

        # From bathroom to living room
        if (
            event_stream.source == living_room_center_light
            and living_room_center_light.state
            and bathroom_light.state
        ):
            bathroom_light.set_state(False)
            logger.info(f"{self.name}: Bathroom light turned off")

        # From bathroom to bedroom
        if (
            event_stream.source == bedroom_light
            and bedroom_light.state
            and bathroom_light.state
        ):
            bathroom_light.set_state(False)
            logger.info(f"{self.name}: Bathroom light turned off")

        # From bathroom to office
        if (
            event_stream.source == office_light
            and office_light.state
            and bathroom_light.state
        ):
            bathroom_light.set_state(False)
            logger.info(f"{self.name}: Bathroom light turned off")

        # From office to living room
        if (
            event_stream.source == living_room_center_light
            and living_room_center_light.state
            and office_light.state
        ):
            office_light.set_state(False)
            logger.info(f"{self.name}: Office light turned off")

        # From office to bedroom
        if (
            event_stream.source == bedroom_light
            and bedroom_light.state
            and office_light.state
        ):
            office_light.set_state(False)
            logger.info(f"{self.name}: Office light turned off")

        # From office to bathroom
        if (
            event_stream.source == bathroom_light
            and bathroom_light.state
            and office_light.state
        ):
            office_light.set_state(False)
            logger.info(f"{self.name}: Office light turned off")


flow_control = FlowControl(
    "Flow Control", [flow_control_stream], enable_switch=home_alone
)
