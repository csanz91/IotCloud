from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from threading import Event, Thread

import iotcloud_api

logger = logging.getLogger(__name__)

# Constants
DEFAULT_SUNRISE_MINUTES = 60 * 8  # 08:00
DEFAULT_SUNSET_MINUTES = 60 * 19  # 19:00
SUCCESS_RENEWAL_HOURS = 11
ERROR_RENEWAL_HOURS = 1


@dataclass
class SunScheduleData:
    sunrise: int
    sunset: int
    timestamp: int = 0
    utc_sun_schedule_expire_date: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SunScheduleDataManager:
    def __init__(self, location_id: str = "5ca4784d931b1502f377c92d"):
        self.enable_sun_schedule = True
        # By default set the sunrise at 08:00 and sunset at 20:00
        self.sun_schedule: SunScheduleData = SunScheduleData(
            DEFAULT_SUNRISE_MINUTES, DEFAULT_SUNSET_MINUTES
        )

        self.location_id = location_id

        self.api = iotcloud_api.IotCloudApi()

        self.retrieving_data = Event()

    def renew_sun_schedule(self, hours: int) -> None:
        self.sun_schedule.utc_sun_schedule_expire_date = datetime.now(
            timezone.utc
        ) + timedelta(hours=hours)

    def retrieve_sun_schedule(self) -> None:
        try:
            sun_schedule_data = self.api.get_location_sun_schedule(self.location_id)

            self.sun_schedule = SunScheduleData(
                sun_schedule_data["sunrise"],
                sun_schedule_data["sunset"],
                sun_schedule_data["timestamp"],
            )
            self.renew_sun_schedule(SUCCESS_RENEWAL_HOURS)

        except Exception:
            logger.error(
                "It was not possible to retrieve the sun schedule.", exc_info=True
            )
            self.renew_sun_schedule(ERROR_RENEWAL_HOURS)
        finally:
            self.retrieving_data.clear()

    def update_sun_schedule(self) -> None:
        if not self.enable_sun_schedule:
            return

        now = datetime.now(timezone.utc)
        if (
            now > self.sun_schedule.utc_sun_schedule_expire_date
            and not self.retrieving_data.is_set()
        ):
            self.retrieving_data.set()
            Thread(target=self.retrieve_sun_schedule, daemon=True).start()

    def get_sun_schedule(self) -> SunScheduleData:
        return self.sun_schedule
