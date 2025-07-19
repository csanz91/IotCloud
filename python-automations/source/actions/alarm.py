import logging
import threading
import time
from actions.action import Action
from devices import (
    pihole_client,
    notifier,
    door_activation_stream,
    occupancy_stream,
    alarm_armed_stream,
    alarm_armed,
)
from actions.house_occupancy_tracker import house_occupancy_tracker
from events import EventStream
from config import (
    VACUUM_ACTIVE_STATES,
    ALARM_AUTO_ARM_DELAY,
    ALARM_PRESENCE_CHECK_TIMEOUT,
    ALARM_DOOR_DELAY,
    ALARM_EMPTY_HOUSE_DELAY,
    KNOWN_HOSTNAMES,
)
from docker_secrets import get_docker_secrets
from miio.integrations.vacuum import RoborockVacuum
from miio.integrations.vacuum.roborock.vacuum import ROCKROBO_V1

logger = logging.getLogger()


class Alarm(Action):
    CHECK_INTERVAL = 5
    ALARM_PRESENCE_CHECK_SLEEP = 10
    MIN_PRESENCE_DURATION = 30  # Minimum seconds of continuous presence to disarm alarm

    def __init__(self, name: str, streams: list[EventStream]):
        super().__init__(name, streams)
        self.armed = False
        self.alarm_sent = False
        self.checking = False
        self.disarmed_by_user = False
        self.arm_thread = None
        self.last_door_time = time.time()
        self.lock = threading.Lock()

        token = get_docker_secrets(name="roborock_token")
        ip = get_docker_secrets(name="roborock_ip")
        self.vac = RoborockVacuum(ip, token, model=ROCKROBO_V1)

        check_thread = threading.Thread(target=self.periodic_check)
        check_thread.daemon = True
        check_thread.start()

    def periodic_check(self):
        """
        Periodically check if the house has been empty for a long time and arm the alarm
        """
        logger.debug(f"{self.name}: Started periodic check")
        while True:
            if not self.armed and not self.disarmed_by_user:
                current_time = time.time()
                # If house has been empty for 10 hours, arm the alarm
                time_since_occupancy = (
                    current_time - house_occupancy_tracker.last_occupied_time
                )
                if time_since_occupancy > ALARM_AUTO_ARM_DELAY:  # 10 hours
                    hours = ALARM_AUTO_ARM_DELAY // 3600
                    self.arm_alarm(f"House empty for {hours} hours")
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
            # Check for sustained presence before disarming
            sustained_presence = self.check_sustained_presence()
            if not sustained_presence:
                known_presence = self.check_known_presence()
                if not known_presence:
                    self.send_alarm()
                else:
                    self.disarm_alarm("Known presence detected")
            else:
                logger.info(f"{self.name}: False alarm - NOT sustained presence detected")
                self.disarm_alarm("Sustained occupancy detected")
        finally:
            self.checking = False

    def disarm_alarm(self, reason: str):
        with self.lock:
            if self.armed:
                alarm_armed.set_state(False)
                self.armed = False
                self.alarm_sent = False
                logger.info(f"{self.name}: Alarm disarmed - {reason}")

    def send_alarm(self):
        if not self.alarm_sent:
            self.alarm_sent = True
            logger.warning(f"{self.name}: Alarm triggered")
            notifier.send_notification("🚨 Alarm triggered")

    def check_sustained_presence(self):
        """
        Check if there has been sustained presence for the minimum duration.
        Returns True only if occupancy has been continuous for MIN_PRESENCE_DURATION seconds.
        """
        if not house_occupancy_tracker.is_occupied:
            logger.info(f"{self.name}: House is not occupied")
            return False

        # Check how long the house has been continuously occupied
        current_time = time.time()
        continuous_occupancy_duration = (
            current_time - house_occupancy_tracker.last_occupied_time
        )

        # If occupancy just started, we need to wait and monitor for sustained presence
        if continuous_occupancy_duration < self.MIN_PRESENCE_DURATION:
            logger.info(f"{self.name}: Checking for sustained presence...")
            start_time = time.time()

            while time.time() - start_time < self.MIN_PRESENCE_DURATION:
                if not house_occupancy_tracker.is_occupied:
                    logger.info(f"{self.name}: Presence lost during sustained check")
                    return False
                time.sleep(1)  # Check every second

            logger.info(
                f"{self.name}: Sustained presence confirmed for {self.MIN_PRESENCE_DURATION} seconds"
            )
            return True
        else:
            # House has been occupied for longer than minimum duration
            logger.info(
                f"{self.name}: House already occupied for {continuous_occupancy_duration:.1f} seconds"
            )
            return True

    def check_known_presence(self):
        start_time = time.time()
        while time.time() - start_time < ALARM_PRESENCE_CHECK_TIMEOUT:  # 3 minutes
            pihole_client.refresh_last_seen_devices()
            for hostname in KNOWN_HOSTNAMES:
                if pihole_client.is_device_home(hostname):
                    logger.info(
                        f"{self.name}: Known device detected, canceling alarm check"
                    )
                    return True

            time.sleep(self.ALARM_PRESENCE_CHECK_SLEEP)
        logger.warning(f"{self.name}: No known presence detected after 3 minutes")
        return False  # No presence detected within timeout

    def try_arm_alarm(self):
        logger.debug(f"{self.name}: Trying to arm alarm")
        while True:
            # Give some time before arming the alarm for the users to get out of the house
            # Check if 10 minutes passed without occupancy
            current_time = time.time()
            time_since_door_was_opened = current_time - self.last_door_time
            logger.debug(
                f"{self.name}: Time since door was opened: {time_since_door_was_opened}"
            )
            if time_since_door_was_opened >= ALARM_DOOR_DELAY:
                # If the house is still occupied dont arm the alarm
                logger.debug(f"House ocupancy: {house_occupancy_tracker.is_occupied}")
                if house_occupancy_tracker.is_occupied:
                    vacuum_state = self.vac.status().state
                    logger.info(f"{self.name}: Vacuum state: {vacuum_state}")
                    if vacuum_state not in VACUUM_ACTIVE_STATES:
                        logger.debug(
                            f"{self.name}: House is occupied, not arming alarm"
                        )
                        return

                time_since_occupancy = (
                    current_time - house_occupancy_tracker.last_occupied_time
                )
                # If the house is empty
                if time_since_occupancy > ALARM_EMPTY_HOUSE_DELAY:
                    duration_in_minutes = ALARM_EMPTY_HOUSE_DELAY // 60
                    self.arm_alarm(
                        f"Door opened and house empty for {duration_in_minutes} minutes"
                    )
                    return

            time.sleep(self.CHECK_INTERVAL)

    def arm_alarm(self, reason: str):
        with self.lock:
            if not self.armed:
                alarm_armed.set_state(True)
                self.armed = True
                logger.info(f"{self.name}: Alarm armed - {reason}")
                notifier.send_notification(f"🔐 Alarm armed: {reason}")

    def action(self, event_stream: EventStream):
        if event_stream == door_activation_stream:
            self.disarmed_by_user = False
            self.last_door_time = time.time()
            self.start_arm_thread()  # Start checking when door is activated

        elif event_stream == alarm_armed_stream:
            if alarm_armed.state:
                self.disarmed_by_user = False
                self.arm_alarm("Armed by user")
            else:
                self.disarmed_by_user = True
                self.disarm_alarm("Disarmed by user")

        if house_occupancy_tracker.is_occupied:
            self.disarmed_by_user = False

        with self.lock:
            should_check = (
                self.armed and house_occupancy_tracker.is_occupied and not self.checking
            )

        if should_check:
            self.checking = True
            logger.info(f"{self.name}: Checking for alarm")
            logger.info(f"House occupancy: {house_occupancy_tracker.is_occupied}")
            check_thread = threading.Thread(target=self.check_alarm)
            check_thread.daemon = True
            check_thread.start()


alarm = Alarm("Alarm", [door_activation_stream, occupancy_stream, alarm_armed_stream])
