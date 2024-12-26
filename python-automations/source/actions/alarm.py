import logging
import threading
import time
from actions.action import Action
from devices import (
    cesar_presence,
    pieri_presence,
    notifier,
    door_sensor,
    door_activation_stream,
    occupancy_stream,
)
from actions.house_occupancy_tracker import house_occupancy_tracker
from events import EventStream

logger = logging.getLogger()

class Alarm(Action):
    CHECK_INTERVAL = 5

    def __init__(self, name: str, streams: list[EventStream]):
        super().__init__(name, streams)
        self.armed = False
        self.alarm_sent = False
        self.checking = False
        self.arm_thread = None
        self.last_door_time = time.time()
        self.lock = threading.Lock()

        check_thread = threading.Thread(target=self.periodic_check)
        check_thread.daemon = True
        check_thread.start()

    def periodic_check(self):
        """
        Periodically check if the house has been empty for a long time and arm the alarm
        """
        logger.debug(f"{self.name}: Started periodic check")
        while True:
            if not self.armed:
                current_time = time.time()
                # If house has been empty for 10 hours, arm the alarm
                time_since_occupancy = (
                    current_time - house_occupancy_tracker.last_occupied_time
                )
                if time_since_occupancy > 3600 * 10:  # 10 hours
                    self.arm_alarm("House empty for 10 hours")
                    continue
            time.sleep(self.CHECK_INTERVAL)

    def start_arm_thread(self):
        with self.lock:
            if self.arm_thread is None or not self.arm_thread.is_alive():
                self.arm_thread = threading.Thread(target=self.try_arm_alarm)
                self.arm_thread.daemon = True
                self.arm_thread.start()

    def check_alarm(self):
        try:
            known_presence = self.check_known_presence()
            if not known_presence:
                self.send_alarm()
            else:
                with self.lock:
                    self.armed = False
                    self.alarm_sent = False
        finally:
            self.checking = False

    def send_alarm(self):
        if not self.alarm_sent:
            self.alarm_sent = True
            logger.warning(f"{self.name}: Alarm triggered")
            notifier.send_notification("🚨 Alarm triggered")

    def check_known_presence(self):
        start_time = time.time()
        while time.time() - start_time < 180:  # 3 minutes
            cesar_home = cesar_presence.getPresence()
            pieri_home = pieri_presence.getPresence()

            logger.debug(
                f"{self.name}: Checking presence - "
                f"Cesar: {cesar_home}, Pieri: {pieri_home}"
            )

            if cesar_home or pieri_home:
                logger.info(f"{self.name}: Known device detected, canceling alarm check")
                return True

            time.sleep(10)
        logger.warning(f"{self.name}: No known presence detected after 3 minutes")
        return False  # No presence detected within timeout

    def try_arm_alarm(self):
        logger.debug(f"{self.name}: Trying to arm alarm")
        while True:
            # Give some time before arming the alarm for the users to get out of the house
            # Check if 10 minutes passed without occupancy
            current_time = time.time()
            time_since_door_was_opened = current_time - self.last_door_time
            # logger.debug(
            #     f"{self.name}: Time since door was opened: {time_since_door_was_opened}"
            # )
            if time_since_door_was_opened >= 90:
                # If the house is still occupied dont arm the alarm
                if house_occupancy_tracker.is_occupied:
                    logger.debug(f"{self.name}: House is occupied, not arming alarm")
                    return

                time_since_occupancy = (
                    current_time - house_occupancy_tracker.last_occupied_time
                )
                # If the house is empty
                if time_since_occupancy > 300:
                    self.arm_alarm("Door opened and house empty for 10 minutes")
                    return

            time.sleep(self.CHECK_INTERVAL)

    def arm_alarm(self, reason: str):
        with self.lock:
            if not self.armed:
                self.armed = True
                logger.info(f"{self.name}: Alarm armed - {reason}")
                notifier.send_notification(f"🔐 Alarm armed: {reason}")

    def action(self, event_stream: EventStream):
        if event_stream == door_activation_stream:
            self.last_door_time = time.time()
            self.start_arm_thread()  # Start checking when door is activated

        with self.lock:
            should_check = self.armed and house_occupancy_tracker.is_occupied and not self.checking

        if should_check:
            self.checking = True
            check_thread = threading.Thread(target=self.check_alarm)
            check_thread.daemon = True
            check_thread.start()


alarm = Alarm(
    "Alarm", [door_activation_stream, occupancy_stream]
)