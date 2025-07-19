from datetime import datetime, time
from zoneinfo import ZoneInfo


def is_night_time():
    timezone = ZoneInfo("Europe/Madrid")
    now = datetime.now(tz=timezone).time()
    return now >= time(21, 0, tzinfo=timezone) or now <= time(6, 30, tzinfo=timezone)
