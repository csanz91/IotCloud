import logging
from dateutil import parser
import calendar
import time

logger = logging.getLogger(__name__)


def getRP(initialTimestamp, finalTimestamp):
    now = int(time.time())
    intervalSeconds = finalTimestamp - initialTimestamp
    secondsFromStart = now - initialTimestamp

    # > 60 days or from 360 days ago
    if intervalSeconds > 3600 * 24 * 60 or secondsFromStart > 3600 * 24 * 360:
        rp = '"3years"."downsampled_sensorsData_1d"'
    # > 5 days or from 44 days ago
    elif intervalSeconds > 3600 * 24 * 32 or secondsFromStart > 3600 * 24 * 44:
        rp = '"1year"."downsampled_sensorsData_1h"'
    else:
        rp = "sensorsData"

    return rp


def getData(
    influxClient, locationId, sensorId, initialTimestamp, finalTimestamp, maxValues=200
):

    intervalSeconds = finalTimestamp - initialTimestamp
    groupBySeconds = max(-(-intervalSeconds / maxValues - 1), 1)

    rp = getRP(initialTimestamp, finalTimestamp)

    query = """ SELECT 
                    mean("value") as value
                FROM %s WHERE
                    locationId='%s' AND sensorId='%s' AND time>=%is AND time<%is
                GROUP BY
                    time(%is)
                FILL(none)
                """ % (
        rp,
        locationId,
        sensorId,
        initialTimestamp,
        finalTimestamp,
        groupBySeconds,
    )

    results = influxClient.query(query)
    if not results:
        return

    valuesList = list(results.get_points())
    return valuesList


def getLocationActionsData(influxClient, locationId, initialTimestamp, finalTimestamp):

    query = """ SELECT 
                    state, setToogle, sensorId
                FROM "3years"."sensorsData" WHERE
                    locationId='%s' AND time>=%is AND time<%is
                GROUP BY
                    "sensorId"
                """ % (
        locationId,
        initialTimestamp,
        finalTimestamp,
    )

    results = influxClient.query(query)
    if not results:
        return

    valuesList = list(results.get_points())
    return valuesList


def getActionsData(
    influxClient, locationId, sensorId, initialTimestamp, finalTimestamp
):

    query = """ SELECT 
                    state, setToogle
                FROM "3years"."sensorsData" WHERE
                    locationId='%s' AND sensorId='%s' AND time>=%is AND time<%is
                """ % (
        locationId,
        sensorId,
        initialTimestamp,
        finalTimestamp,
    )

    results = influxClient.query(query)
    if not results:
        return

    valuesList = list(results.get_points())
    return valuesList


def getStats(influxClient, locationId, sensorId, initialTimestamp, finalTimestamp):

    rp = getRP(initialTimestamp, finalTimestamp)

    query = """ SELECT 
                    mean("value") as mean,
                    min("value") as min,
                    max("value") as max
                FROM %s WHERE
                    locationId='%s' AND sensorId='%s' AND time>=%is AND time<%is
                FILL(none)
                """ % (
        rp,
        locationId,
        sensorId,
        initialTimestamp,
        finalTimestamp,
    )

    results = influxClient.query(query)
    if not results:
        return

    valuesList = list(results.get_points())
    return valuesList


def getDeviceLastTimeSeen(influxClient, locationId, deviceId):

    query = """ SELECT 
                    last(status) as lastStatus
                FROM "3years"."sensorsData" WHERE
                    locationId='%s' AND deviceId='%s'
                """ % (
        locationId,
        deviceId,
    )

    statusResults = influxClient.query(query)
    if not statusResults:
        return 0

    lastStatusSeen = list(statusResults.get_points())[0]
    # If the device is online, return the current timestamp
    if lastStatusSeen["lastStatus"]:
        return int(time.time())

    # Otherwise, return the timestamp when the device disconnected
    lastStatusSeenTimestamp = calendar.timegm(
        parser.parse(lastStatusSeen["time"]).timetuple()
    )
    return lastStatusSeenTimestamp


def getStateTime(
    influxClient, locationId, deviceId, sensorId, initialTimestamp, finalTimestamp
):

    # To calculate the time between the [initialTimestamp] and the first state from the interval
    # we need to get which state was set before [initialTimestamp], for that we first query the last
    # state before [initialTimestamp].

    query = """ SELECT 
                    last(state)
                FROM "3years"."sensorsData" WHERE
                    locationId='%s' AND sensorId='%s' AND time<=%is
                """ % (
        locationId,
        sensorId,
        initialTimestamp,
    )
    try:
        results = influxClient.query(query)
        initialTimestampPrev = list(results.get_points())[0]["time"]
    except:
        initialTimestampPrev = initialTimestamp

    query = """ SELECT 
                    state
                FROM "3years"."sensorsData" WHERE
                    locationId='%s' AND sensorId='%s' AND time>='%s' AND time<%is
                ORDER BY
                    time DESC
                """ % (
        locationId,
        sensorId,
        initialTimestampPrev,
        finalTimestamp,
    )

    results = influxClient.query(query)
    return calculateActiveTime(results, initialTimestamp, finalTimestamp)


def getHeatingTime(
    influxClient, locationId, deviceId, sensorId, initialTimestamp, finalTimestamp
):

    # To calculate the time between the [initialTimestamp] and the first state from the interval
    # we need to get which state was set before [initialTimestamp], for that we first query the last
    # state before [initialTimestamp].

    query = """ SELECT 
                    last(state)
                FROM "3years"."sensorsData" WHERE
                    locationId='%s' AND sensorId='%s' AND time<=%is
                """ % (
        locationId,
        sensorId,
        initialTimestamp,
    )
    try:
        results = influxClient.query(query)
        initialTimestampPrev = list(results.get_points())[0]["time"]
    except:
        initialTimestampPrev = initialTimestamp

    query = """ SELECT 
                    heating as state
                FROM "3years"."thermostatData" WHERE
                    locationId='%s' AND sensorId='%s' AND time>='%s' AND time<%is
                ORDER BY
                    time DESC
                """ % (
        locationId,
        sensorId,
        initialTimestampPrev,
        finalTimestamp,
    )

    results = influxClient.query(query)
    return calculateActiveTime(results, initialTimestamp, finalTimestamp)


def calculateActiveTime(results, initialTimestamp, finalTimestamp):

    if not results:
        return 0

    states = list(results.get_points())

    activeTime = 0
    previousStateTimestamp = finalTimestamp
    for statePoint in states:
        timestamp = calendar.timegm(parser.parse(statePoint["time"]).timetuple())
        state = bool(statePoint["state"])

        if timestamp <= initialTimestamp:
            if state:
                activeTime += previousStateTimestamp - initialTimestamp
            break

        if state:
            activeTime += previousStateTimestamp - timestamp

        previousStateTimestamp = timestamp

    return activeTime


def getTotalizerCurrentRate(influxClient, locationId, sensorId):

    query = """ SELECT
                    LAST("rate") as rate
                FROM totalizerData WHERE
                    locationId='%s' AND sensorId='%s' AND time>= NOW() - 12h
            """ % (
        locationId,
        sensorId,
    )

    results = influxClient.query(query)
    if not results:
        return

    valuesList = list(results.get_points())
    return valuesList


def getTotalizerTrendRate(influxClient, locationId, sensorId):

    query = """ SELECT
                    rate
                FROM totalizerData WHERE
                    locationId='%s' AND sensorId='%s' AND time>= NOW() - 6h
            """ % (
        locationId,
        sensorId,
    )

    results = influxClient.query(query)
    if not results:
        return

    valuesList = list(results.get_points())
    return valuesList


def getHourlyAccumulation(
    influxClient, locationId, sensorId, initialTimestamp, finalTimestamp
):

    query = """ SELECT 
                    SUM("value") as value
                FROM sensorsData WHERE
                    locationId='%s' AND sensorId='%s' AND time>=%is AND time<%is
                GROUP BY
                    time(1h)
                ORDER BY
                    time DESC
                """ % (
        locationId,
        sensorId,
        initialTimestamp,
        finalTimestamp,
    )

    results = influxClient.query(query)
    if not results:
        return

    valuesList = list(results.get_points())
    return valuesList


def getDeviceIP(influxClient, locationId, deviceId):

    query = """ SELECT 
                     last(IP) as IP
                FROM "raw"."devicesIPs" WHERE
                    locationId='%s' AND deviceId='%s'
                """ % (
        locationId,
        deviceId,
    )

    results = influxClient.query(query)
    if not results:
        return 0

    ip = list(results.get_points())[0]["IP"]

    return ip
