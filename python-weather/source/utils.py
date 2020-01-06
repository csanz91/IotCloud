import logging
import math
from dateutil import tz

logger = logging.getLogger(__name__)


def getResponseModel(result, data=None):
    response = {"result": result}
    if not data is None:
        response['data'] = data

    return response

def closest_pair(targetPoint, pointsList):
    distances = {dist(p, targetPoint): p for p in pointsList}
    return distances[min(distances.keys())]

def dist(p1, p2):
    return math.sqrt((p1['lat'] - p2['lat'])**2 +
                        (p1['lng'] - p2['lng'])**2)

def toUtcTimestamp(measureTime, timeZoneId):
    '''Converts a timestamp from a local time to UTC'''

    if not timeZoneId:
        timeZoneId = "Europe/Madrid"

    localZone = tz.gettz(timeZoneId)

    localTimeAware = measureTime.replace(tzinfo=localZone)
    utcTimeAware = localTimeAware.astimezone(tz.UTC)
    utcTimestamp = int(utcTimeAware.timestamp())
    return utcTimestamp

def toUtc(measureTime, timeZoneId):
    '''Converts a timestamp from a local time to UTC'''

    if not timeZoneId:
        timeZoneId = "Europe/Madrid"

    localZone = tz.gettz(timeZoneId)

    localTimeAware = measureTime.replace(tzinfo=localZone)
    utcTimeAware = localTimeAware.astimezone(tz.UTC)
    return utcTimeAware