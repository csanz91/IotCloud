import logging
import time
from actions.action import Action
from devices import (
    teruel_presence_stream,
    teruel_puerta_abajo_presence,
    teruel_puerta_arriba_presence,
    teruel_alarm,
    teruel_puerta_abajo_notifier,
    teruel_puerta_arriba_notifier,
)
from events import EventStream

logger = logging.getLogger()


class TeruelPresenceAlarm(Action):
    def __init__(self, name: str, event_streams: list[EventStream], enable_device=None):
        super().__init__(name, event_streams, enable_device)
        self.last_notification_time = 0
        self.cooldown_period = 900  # 15 minutes in seconds

    def can_send_notification(self) -> bool:
        current_time = time.time()
        time_elapsed = current_time - self.last_notification_time
        return time_elapsed >= self.cooldown_period

    def action(self, event_stream: EventStream):
        current_time = time.time()
        if not self.can_send_notification():
            # Reset timer if presence is detected during cooldown
            self.last_notification_time = current_time
            return

        msg = "Presencia Detectada"
        if teruel_puerta_abajo_presence.state:
            teruel_puerta_abajo_notifier.send_notification(msg)
            self.last_notification_time = current_time

        if teruel_puerta_arriba_presence.state:
            teruel_puerta_arriba_notifier.send_notification(msg)
            self.last_notification_time = current_time


teruel_presence_alarm = TeruelPresenceAlarm(
    "Teruel Presence Alarm", [teruel_presence_stream], teruel_alarm
)
