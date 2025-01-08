import logging
import logging.config
from typing import Optional
from events import EventStream
from devices_types import Switch

logger = logging.getLogger()

class Action:
    """
    The Action class represents an action that can be executed in response to events from event streams.

    Attributes:
        name (str): The name of the action.
        streams (list[EventStream]): The event streams that trigger the action.

    Methods:
        execute(): Executes the action.
        action(): Defines the specific action to be performed. Should be overridden by subclasses.
    """
    def __init__(self, name: str, streams: list[EventStream], enable_switch: Optional[Switch] = None):
        self.name = name
        self.enable_switch = enable_switch
        for stream in streams:
            stream.subscribe(self.execute)

    def execute(self, event_stream: EventStream):
        try:
            if self.enable_switch is None or self.enable_switch.state:
                self.action(event_stream)
        except Exception:
            logger.error(f"{self.name}: Error executing action", exc_info=True)

    def action(self, event_stream: EventStream):
        pass
