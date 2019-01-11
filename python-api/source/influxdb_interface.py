import logging

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