import logging
import logging.config
import time
from collections import defaultdict
from cache_decorator import cache_disk

logger = logging.getLogger()

class MaxSizeList(object):
    def __init__(self, sizeLimit, maxPercentageVariation=0.2):
        self.maxPercentageVariation = maxPercentageVariation
        self.sizeLimit = sizeLimit
        self.list = [None] * sizeLimit
        self.next = 0

    def push(self, item):
        self.list[self.next % len(self.list)] = item
        self.next += 1

    def getList(self):
        if self.next < len(self.list):
            return self.list[:self.next]
        else:
            split = self.next % len(self.list)
            return self.list[split:] + self.list[:split]

    def getMedian(self):
        selfList = self.getList()
        lenSelfList = len(selfList)
        if not lenSelfList:
            return None
        return sum(selfList)/float(lenSelfList)

    def addValueSafe(self, newValue, valueRange):
        
        median = self.getMedian()
        # Anyway we add the value to the list, this way we get 
        # the chance to correct a false negative
        self.push(newValue)

        if not median:
            return

        if valueRange:
            maxValueDelta = abs(valueRange) * self.maxPercentageVariation
        else:
            maxValueDelta = abs(median) * self.maxPercentageVariation

        try:
            assert median-maxValueDelta < newValue < median+maxValueDelta
        except AssertionError:
            logger.error("The value is not valid. %s < %s < %s " %(median-maxValueDelta, newValue, median+maxValueDelta))
            raise ValueError("The value is outside the acceptable range")

@cache_disk()
def getValueRange(influxDb, locationId, sensorId):
    oneDayAgo = int(time.time()) - 3600 * 24
    query = ''' SELECT 
                    MAX(value) - MIN(value) as range,
                    COUNT(value) as numValues
                FROM
                    sensorsData 
                WHERE
                    locationId='%s' AND sensorId='%s' AND time>=%is
            ''' % (locationId, sensorId, oneDayAgo)

    results = influxDb.query(query)
    if not results:
        return

    data = list(results.get_points())[0]
    
    numValues = data["numValues"]
    if numValues<100:
        logger.error("There is not enough values: %s to calculate the range" % numValues)
        return None

    valueRange = data["range"]
    return valueRange