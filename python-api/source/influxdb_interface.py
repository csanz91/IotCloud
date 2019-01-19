import logging
from dateutil import parser
import calendar

logger = logging.getLogger(__name__)

def getData(influxClient, locationId, sensorId, initialTimestamp, finalTimestamp, maxValues=200):

    logger.info(sensorId)

    intervalSeconds = finalTimestamp - initialTimestamp
    groupBySeconds = max(-(-intervalSeconds / maxValues-1), 1)

    query = ''' SELECT 
                    mean("value") as value
                FROM sensorsData WHERE 
                    locationId='%s' AND sensorId='%s' AND time>=%is AND time<%is
                GROUP BY
                    time(%is)
                FILL(none)
                ''' % (locationId, sensorId, initialTimestamp, finalTimestamp, groupBySeconds)

    results = influxClient.query(query)
    if not results:
        return

    valuesList = list(results.get_points())
    return valuesList

def getStats(influxClient, locationId, sensorId, initialTimestamp, finalTimestamp):

    query = ''' SELECT 
                    mean("value") as mean,
                    min("value") as min,
                    max("value") as max
                FROM sensorsData WHERE 
                    locationId='%s' AND sensorId='%s' AND time>=%is AND time<%is
                FILL(none)
                ''' % (locationId, sensorId, initialTimestamp, finalTimestamp)

    results = influxClient.query(query)
    if not results:
        return

    valuesList = list(results.get_points())
    return valuesList

def getDeviceLastTimeSeen(influxClient, locationId, deviceId):

    query = ''' SELECT 
                    last("value") as lastSeen,
                FROM sensorsData WHERE 
                    locationId='%s' AND deviceId='%s'
                ''' % (locationId, deviceId)

    results = influxClient.query(query)
    if not results:
        return

    lastTimeSeen = list(results.get_points())[0]["time"]
    return lastTimeSeen

def getStateTime(influxClient, locationId, deviceId, sensorId, initialTimestamp, finalTimestamp):

    # To calculate the time between the [initialTimestamp] and the first state from the interval
    # we need to get which state was set before [initialTimestamp], as we dont dont know when it was,
    # we have to go back a certain amount of time where we think a change of state happened
    # If no state change has happened in the time we guess, the time between [initialTimestamp] and 
    # the first state in the interval wont be registered
    initialTimestampPrev = initialTimestamp - 3600 * 24 # Go back 1 day

    query = ''' SELECT 
                    state
                FROM "3years"."sensorsData" WHERE 
                    locationId='%s' AND deviceId='%s' AND sensorId='%s' AND time>=%is AND time<%is
                ORDER BY
                    time DESC
                ''' % (locationId, deviceId, sensorId, initialTimestampPrev, finalTimestamp)

    results = influxClient.query(query)
    if not results:
        return 0

    states = list(results.get_points())

    activeTime = 0    
    previousStateTimestamp = finalTimestamp
    for statePoint in states:
        timestamp = calendar.timegm(parser.parse(statePoint["time"]).timetuple())
        state = bool(statePoint["state"])

        if timestamp<=initialTimestamp:
            if state:
                activeTime += previousStateTimestamp - initialTimestamp
            break

        if state:
            activeTime += previousStateTimestamp - timestamp
            
        previousStateTimestamp = timestamp

    return activeTime

def getHeatingTime(influxClient, locationId, deviceId, sensorId, initialTimestamp, finalTimestamp):

    # To calculate the time between the [initialTimestamp] and the first state from the interval
    # we need to get which state was set before [initialTimestamp], as we dont dont know when it was,
    # we have to go back a certain amount of time where we think a change of state happened
    # If no state change has happened in the time we guess, the time between [initialTimestamp] and 
    # the first state in the interval wont be registered
    initialTimestampPrev = initialTimestamp - 3600 * 24 # Go back 1 day

    query = ''' SELECT 
                    heating
                FROM "3years"."thermostatData" WHERE 
                    locationId='%s' AND deviceId='%s' AND sensorId='%s' AND time>=%is AND time<%is
                ORDER BY
                    time DESC
                ''' % (locationId, deviceId, sensorId, initialTimestampPrev, finalTimestamp)

    results = influxClient.query(query)
    if not results:
        return 0

    states = list(results.get_points())

    activeTime = 0    
    previousStateTimestamp = finalTimestamp
    for statePoint in states:
        timestamp = calendar.timegm(parser.parse(statePoint["time"]).timetuple())
        state = bool(statePoint["heating"])
        if state:
            if timestamp<=initialTimestamp:
                activeTime += previousStateTimestamp - initialTimestamp
                break

            activeTime += previousStateTimestamp - timestamp
        previousStateTimestamp = timestamp

    return activeTime