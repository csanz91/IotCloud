import logging
import time
from dateutil import tz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

logger = logging.getLogger(__name__)

def toUtc(measureTime, timezone="Europe/Madrid"):
    '''Converts a timestamp from a local time to UTC'''

    localZone = tz.gettz(timezone)

    localTimeMidnightAware = measureTime.replace(tzinfo=localZone)
    localTimeMidnightNaive = localTimeMidnightAware.astimezone(tz.UTC)
    localMidnightTimestamp = calendar.timegm(localTimeMidnightNaive.timetuple())
    return localMidnightTimestamp


def getDayTimestamps(today, timezone="Europe/Madrid"):
    
    localZone = tz.gettz(timezone)
    dt = today.replace(tzinfo=localZone)

    localMidnightTimestamp = toUtc(dt.replace(hour=0, minute=0, second=0, microsecond=0))
    localEndDayTimestamp = toUtc(dt.replace(hour=23, minute=59, second=59, microsecond=0))
    return localMidnightTimestamp, localEndDayTimestamp


def getThisWeekTimestamps(today, timezone="Europe/Madrid"):

    localZone = tz.gettz(timezone)
    today = today.replace(tzinfo=localZone).date()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)

    d2dt = lambda date: datetime(year=date.year, month=date.month, day=date.day)
    localMidnightTimestamp = toUtc(d2dt(start).replace(hour=0, minute=0, second=0, microsecond=0))
    localEndDayTimestamp = toUtc(d2dt(end).replace(hour=23, minute=59, second=59, microsecond=0))
    return localMidnightTimestamp, localEndDayTimestamp


def getThisMonthTimestamps(today, timezone="Europe/Madrid"):

    localZone = tz.gettz(timezone)
    today = today.replace(tzinfo=localZone)
    start = today.replace(day=1)
    end = start + relativedelta(months=1) - timedelta(days=1)

    d2dt = lambda date: datetime(year=date.year, month=date.month, day=date.day)
    localMidnightTimestamp = toUtc(d2dt(start).replace(hour=0, minute=0, second=0, microsecond=0))
    localEndDayTimestamp = toUtc(d2dt(end).replace(hour=23, minute=59, second=59, microsecond=0))
    return localMidnightTimestamp, localEndDayTimestamp
