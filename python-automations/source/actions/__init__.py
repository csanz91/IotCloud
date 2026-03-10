from datetime import datetime, timezone
from sunschedulemanager import SunScheduleDataManager

sun_schedule_manager = SunScheduleDataManager()


def is_night_time():
    sun_schedule_manager.update_sun_schedule()
    sun_schedule = sun_schedule_manager.get_sun_schedule()

    # Get current time in minutes from UTC midnight
    now_utc = datetime.now(timezone.utc)
    current_minutes = now_utc.hour * 60 + now_utc.minute

    # Night time is before sunrise or after sunset
    return (
        current_minutes < sun_schedule.sunrise or current_minutes >= sun_schedule.sunset
    )
