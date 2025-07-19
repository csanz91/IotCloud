import logging
import threading
from actions.action import Action
from devices_types import Switch
from devices import all_zones
from events import EventStream

from zones import Zone

logger = logging.getLogger()


class LightsAutoSwitchOff(Action):
    """
    Action that turns off lights if there's no presence detected for 5 minutes in a specific zone.
    This helps prevent lights from staying on due to false sensor activations.
    """

    CLEANUP_DELAY = 300  # 5 minutes in seconds
    CHECK_INTERVAL = 30  # Check every 30 seconds

    def __init__(self, name: str, streams: list[EventStream]):
        super().__init__(name, streams)
        self.cleanup_timers = {}  # Dict to track timers for each light
        self.zone_timers = {}  # Dict to track timers for each zone
        self.lock = threading.Lock()
        self._start_zone_timers()

    def _start_zone_timers(self):
        """Start a recurring timer for each zone to check its state."""
        for zone in all_zones:
            timer = threading.Timer(self.CHECK_INTERVAL, self._check_zone, args=[zone])
            timer.daemon = True
            timer.start()
            self.zone_timers[zone.name] = timer

    def _check_zone(self, zone: Zone):
        """Periodically check the state of a zone and manage cleanup timers."""
        with self.lock:
            if zone.is_presence_detected():
                self._cancel_cleanup_timer_for_zone(zone)
            else:
                self._start_cleanup_timer_for_zone(zone)

        # Reschedule the timer for the next check
        timer = threading.Timer(self.CHECK_INTERVAL, self._check_zone, args=[zone])
        timer.daemon = True
        timer.start()
        self.zone_timers[zone.name] = timer

    def _cancel_cleanup_timer_for_zone(self, zone: Zone):
        """Cancel cleanup timers for all lights in a specific zone."""
        for light in zone.lights:
            light_name = light.name
            if light_name in self.cleanup_timers:
                timer = self.cleanup_timers.pop(light_name)
                if timer and timer.is_alive():
                    timer.cancel()
                    logger.debug(
                        f"{self.name}: Cancelled cleanup timer for {light_name} in zone {zone.name}"
                    )

    def _start_cleanup_timer_for_zone(self, zone: Zone):
        """Start cleanup timers for lights that are currently on in a specific zone."""
        for light in zone.lights:
            if light.state:
                light_name = light.name
                if light_name not in self.cleanup_timers:
                    logger.info(
                        f"{self.name}: Starting cleanup timer for {light_name} in zone {zone.name}"
                    )
                    timer = threading.Timer(
                        self.CLEANUP_DELAY, self._cleanup_light, args=(light, zone)
                    )
                    timer.daemon = True
                    timer.start()
                    self.cleanup_timers[light_name] = timer

    def _cleanup_light(self, light: Switch, zone: Zone):
        """Turn off a light if its associated presence sensors are off"""
        try:
            # Re-check presence right before turning off the light
            if not zone.is_presence_detected() and light.state:
                light.set_state(False)
                logger.info(
                    f"{self.name}: Turned off {light.name} in zone {zone.name} due to no presence for {self.CLEANUP_DELAY // 60} minutes"
                )
            else:
                logger.debug(
                    f"{self.name}: Skipped turning off {light.name} in zone {zone.name} - presence detected or light already off"
                )
        except Exception as e:
            logger.error(
                f"{self.name}: Error turning off {light.name} in zone {zone.name}: {e}",
                exc_info=True,
            )
        finally:
            with self.lock:
                self.cleanup_timers.pop(light.name, None)


lights_auto_switch_off = LightsAutoSwitchOff(
    "Lights Auto Switch Off",
    [],  # No event streams needed for polling
)
