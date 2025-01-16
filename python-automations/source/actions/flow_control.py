import logging
import threading
from actions.action import Action
from devices_types import Switch, Sensor, DigitalSensor
from devices import (
    bedroom_light,
    bedroom_presence,
    bathroom_light,
    living_room_presence_center,
    living_room_presence,
    living_room_center_light,
    living_room_light,
    office_light,
    office_presence_2,
    kitchen_light,
    flow_control_stream,
    home_alone,
)
from events import EventStream

logger = logging.getLogger()


class FlowControl(Action):
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Switch):
        super().__init__(name, streams, enable_switch=enable_switch)

    def reactivate(self, presence, light: Switch, delay: float = 10):
        # Reactivate the light if the presence is still there
        def activate_lights():
            if presence.state:
                logger.info(
                    f"{self.name}: Reactivating light {light.name} after {delay} seconds"
                )
                light.set_state(True)

        # Check the presence after the delay
        threading.Timer(delay, activate_lights).start()

    def action(self, event_stream: EventStream):

        # From kitchen to living room
        if (
            event_stream.source == living_room_presence
            and living_room_presence.state
            and kitchen_light.state
        ):
            kitchen_light.set_state(False)
            # self.reactivate(living_room_presence.state, [living_room_center_light, living_room_light])
            logger.info(f"{self.name}: Kitchen light turned off")

        # From living room to kitchen
        if (
            event_stream.source == kitchen_light
            and kitchen_light.state
            and (living_room_center_light.state or living_room_light.state)
        ):
            living_room_center_light.set_state(False)
            living_room_light.set_state(False)
            self.reactivate(living_room_presence, living_room_light, delay=8)
            self.reactivate(living_room_presence_center, living_room_center_light)
            logger.info(f"{self.name}: Living room light turned off")

        # From living room to bedroom
        if (
            event_stream.source == bedroom_light
            and bedroom_light.state
            and (living_room_center_light.state or living_room_light.state)
        ):
            living_room_center_light.set_state(False)
            living_room_light.set_state(False)
            self.reactivate(living_room_presence, living_room_light)
            self.reactivate(living_room_presence_center, living_room_center_light)
            logger.info(f"{self.name}: Living room light turned off")

        # From living room to office
        if (
            event_stream.source == office_light
            and office_light.state
            and (living_room_center_light.state or living_room_light.state)
        ):
            living_room_center_light.set_state(False)
            living_room_light.set_state(False)
            self.reactivate(living_room_presence, living_room_light)
            self.reactivate(living_room_presence_center, living_room_center_light)
            logger.info(f"{self.name}: Living room light turned off")

        # From bedroom to living room
        if (
            event_stream.source == living_room_center_light
            and living_room_center_light.state
            and bedroom_light.state
        ):
            bedroom_light.set_state(False)
            self.reactivate(bedroom_presence, bedroom_light)
            logger.info(f"{self.name}: Bedroom light turned off")

        # From bedroom to bathroom
        if (
            event_stream.source == bathroom_light
            and bathroom_light.state
            and bedroom_light.state
        ):
            bedroom_light.set_state(False)
            self.reactivate(bedroom_presence, bedroom_light)
            logger.info(f"{self.name}: Bedroom light turned off")

        # From bedroom to office
        if (
            event_stream.source == office_light
            and office_light.state
            and bedroom_light.state
        ):
            bedroom_light.set_state(False)
            self.reactivate(bedroom_presence, bedroom_light)
            logger.info(f"{self.name}: Bedroom light turned off")

        # From bathroom to living room
        if (
            event_stream.source == living_room_presence
            and living_room_presence.state
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
            event_stream.source == living_room_presence
            and living_room_presence.state
            and office_light.state
        ):
            office_light.set_state(False)
            self.reactivate(office_presence_2, office_light)
            logger.info(f"{self.name}: Office light turned off")

        # From office to bedroom
        if (
            event_stream.source == bedroom_light
            and bedroom_light.state
            and office_light.state
        ):
            office_light.set_state(False)
            self.reactivate(office_presence_2, office_light)
            logger.info(f"{self.name}: Office light turned off")

        # From office to bathroom
        if (
            event_stream.source == bathroom_light
            and bathroom_light.state
            and office_light.state
        ):
            office_light.set_state(False)
            self.reactivate(office_presence_2, office_light)
            logger.info(f"{self.name}: Office light turned off")


flow_control = FlowControl(
    "Flow Control", [flow_control_stream], enable_switch=home_alone
)
