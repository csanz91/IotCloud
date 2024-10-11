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
        return '"3years"."downsampled_sensorsData_1d"'
    elif intervalSeconds > 3600 * 24 * 32 or secondsFromStart > 3600 * 24 * 44:
        return '"1year"."downsampled_sensorsData_1h"'
    else:
        return "sensorsData"


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
        return []

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
        return []

    valuesList = list(results.get_points())
    return valuesList


def getActionsData(
    influxClient, locationId, sensorId, initialTimestamp, finalTimestamp
):

    query = """ SELECT 
                    state, setToogle
                FROM "3years"."sensorsData" WHERE
                    locationId='%s' AND sensorId='%s' AND time>=%is AND time<%is
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
        return []

    valuesList = list(results.get_points())
    return valuesList


def getStats(influxClient, locationId, sensorId, initialTimestamp, finalTimestamp):

    rp = getRP(initialTimestamp, finalTimestamp)

    if rp == "sensorsData":
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
    else:
        query = """ SELECT 
                        mean("value") as mean,
                        min("min_value") as min,
                        max("max_value") as max
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
        return []

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


def getDeviceStatus(
    influxClient, locationId, deviceId, initialTimestamp, finalTimestamp
):

    # To calculate the time between the [initialTimestamp] and the first state from the interval
    # we need to get which state was set before [initialTimestamp], for that we first query the last
    # state before [initialTimestamp].

    query = """ SELECT 
                    "status"
                FROM "3years"."sensorsData" WHERE
                    locationId='%s' AND deviceId='%s' AND time>=%is AND time<%is
                """ % (
        locationId,
        deviceId,
        initialTimestamp,
        finalTimestamp,
    )

    results = influxClient.query(query)
    if not results:
        return []

    valuesList = list(results.get_points())
    return valuesList


def getDevicesStatusStats(influxClient, locationId, initialTimestamp, finalTimestamp):

    # To calculate the time between the [initialTimestamp] and the first state from the interval
    # we need to get which state was set before [initialTimestamp], for that we first query the last
    # state before [initialTimestamp].

    query = """ SELECT 
                    count(status) as reconnections
                FROM "3years"."sensorsData" WHERE
                    locationId='%s' AND time>=%is AND time<%is AND "status"=true
                GROUP BY "deviceId"
                """ % (
        locationId,
        initialTimestamp,
        finalTimestamp,
    )

    results = influxClient.query(query)
    if not results:
        return []

    # Add the deviceId tag to the points list
    valuesList = []
    for result in results.items():
        valuesList.append({**next(result[1]), **result[0][1]})

    return valuesList


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
        initialTimestampPrev = f"'{list(results.get_points())[0]['time']}'"
    except:
        initialTimestampPrev = f"{initialTimestamp}s"

    query = """ SELECT 
                    state
                FROM "3years"."sensorsData" WHERE
                    locationId='%s' AND sensorId='%s' AND time>=%s AND time<%is
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
                    last(heating)
                FROM "3years"."thermostatData" WHERE
                    locationId='%s' AND sensorId='%s' AND time<=%is
                """ % (
        locationId,
        sensorId,
        initialTimestamp,
    )
    try:
        results = influxClient.query(query)
        initialTimestampPrev = f"'{list(results.get_points())[0]['time']}'"
    except:
        initialTimestampPrev = f"{initialTimestamp}s"

    query = """ SELECT 
                    heating as state
                FROM "3years"."thermostatData" WHERE
                    locationId='%s' AND sensorId='%s' AND time>=%s AND time<%is
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
        return []

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
        return []

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
        return []

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


def getEnergyTariffsCostFlexi(influxClient, initialTimestamp, finalTimestamp):

    query = """ SELECT 
                    last(Flexi) as cost
                FROM "3years"."tariffs_cost" WHERE
                    time>=%is AND time<%is
                GROUP BY time(1h)
                FILL(previous)
                """ % (
        initialTimestamp,
        finalTimestamp,
    )
    results = influxClient.query(query)
    if not results:
        return []

    valuesList = list(results.get_points())
    return valuesList

def getEnergyTariffsCostTE(influxClient, initialTimestamp, finalTimestamp):

    hour_fixed_cost = 0.136685 * 3.0 / 24.0 # €/kW y día * kW / 24 horas 
    kw_cost = 0.073
    mirubee_correction_factor = 0.965 # Mean correction factor to match the real consumption 
    sensorId = '202481596676681_004_P'

    query = f""" SELECT 
                    mean(value) / 1000.0 * {mirubee_correction_factor} * {kw_cost} + {hour_fixed_cost} as cost
                FROM sensorsData
                WHERE
                    sensorId = '{sensorId}'
                    AND time>={initialTimestamp}s AND time<{finalTimestamp}s
                GROUP BY time(1h)
                FILL(none)
                """    
    results = influxClient.query(query)
    if not results:
        return []

    valuesList = list(results.get_points())
    valuesList = [v | {'dailyCost': v['cost'] * 24, 'monthlyCost': v['cost'] * 24 * 30} for v in valuesList]
    return valuesList


def saveNotification(influxClient, locationId, extra:  dict, title: str, body: str):
    dataToWrite = [
        {
            "measurement": "notifications",
            "tags": {"locationId": locationId} | extra,
            "fields": {"title": title, "body": body},
        }
    ]
    influxClient.write_points(dataToWrite, retention_policy="3years")


def getLocationNotifications(influxClient, locationId, initialTimestamp, finalTimestamp):
    query = """ SELECT 
                    "body", "title", "locationId", "sensorId"
                    FROM "3years"."notifications" WHERE
                        locationId='%s' AND 
                        time>=%is AND time<%is
                    ORDER BY time DESC
                    """ % (
        locationId,
        initialTimestamp,
        finalTimestamp,
    )
    results = influxClient.query(query)
    if not results:
        return []

    valuesList = list(results.get_points())
    return valuesList

def saveLocationTracking(influxClient, trackerid, points):
    dataToWrite = [
        {
            "measurement": "tracking",
            "tags": {"trackerid": trackerid},
            "fields": {"latitude": point['latitude'], "longitude": point['longitude']},
            "time": point['timestamp']
        }
        for point in points
    ]
    influxClient.write_points(dataToWrite, retention_policy="3years", time_precision="ms")