import logging
from dateutil import tz
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import calendar

logger = logging.getLogger(__name__)


def toUtc(measureTime, timeZoneId):
    """Converts a timestamp from a local time to UTC"""

    if not timeZoneId:
        timeZoneId = "Europe/Madrid"

    localZone = tz.gettz(timeZoneId)

    localTimeMidnightAware = measureTime.replace(tzinfo=localZone)
    localTimeMidnightNaive = localTimeMidnightAware.astimezone(tz.UTC)
    localMidnightTimestamp = calendar.timegm(localTimeMidnightNaive.timetuple())
    return localMidnightTimestamp


def getDayTimestamps(today, timeZoneId):

    if not timeZoneId:
        timeZoneId = "Europe/Madrid"

    localZone = tz.gettz(timeZoneId)
    todayAware = today.replace(tzinfo=tz.UTC)
    dt = todayAware.astimezone(tz=localZone)

    localMidnightTimestamp = toUtc(
        dt.replace(hour=0, minute=0, second=0, microsecond=0), timeZoneId
    )
    localEndDayTimestamp = toUtc(
        dt.replace(hour=23, minute=59, second=59, microsecond=0), timeZoneId
    )
    return localMidnightTimestamp, localEndDayTimestamp


def d2dt(sourceDate: date) -> datetime:
    return datetime(year=sourceDate.year, month=sourceDate.month, day=sourceDate.day)


def getThisWeekTimestamps(today, timeZoneId):

    if not timeZoneId:
        timeZoneId = "Europe/Madrid"

    localZone = tz.gettz(timeZoneId)
    todayAware = today.replace(tzinfo=tz.UTC)
    todayLocal = todayAware.astimezone(tz=localZone).date()
    start = todayLocal - timedelta(days=todayLocal.weekday())
    end = start + timedelta(days=6)

    localMidnightTimestamp = toUtc(
        d2dt(start).replace(hour=0, minute=0, second=0, microsecond=0), timeZoneId
    )
    localEndDayTimestamp = toUtc(
        d2dt(end).replace(hour=23, minute=59, second=59, microsecond=0), timeZoneId
    )
    return localMidnightTimestamp, localEndDayTimestamp


def getThisMonthTimestamps(today, timeZoneId):

    if not timeZoneId:
        timeZoneId = "Europe/Madrid"

    localZone = tz.gettz(timeZoneId)
    todayAware = today.replace(tzinfo=tz.UTC)
    todayLocal = todayAware.astimezone(tz=localZone)
    start = todayLocal.replace(day=1)
    end = start + relativedelta(months=1) - timedelta(days=1)

    localMidnightTimestamp = toUtc(
        d2dt(start).replace(hour=0, minute=0, second=0, microsecond=0), timeZoneId
    )
    localEndDayTimestamp = toUtc(
        d2dt(end).replace(hour=23, minute=59, second=59, microsecond=0), timeZoneId
    )
    return localMidnightTimestamp, localEndDayTimestamp
