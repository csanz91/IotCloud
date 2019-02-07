import logging
import logging.config
from collections import defaultdict

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

    def addValueSafe(self, newValue):
        median = self.getMedian()
        # Anyway we add the value to the list, this way we get 
        # the chance to correct a false negative
        self.push(newValue)

        if not median:
            return

        maxValueDelta = median * self.maxPercentageVariation
        try:
            assert median-maxValueDelta < newValue < median+maxValueDelta
        except AssertionError:
            logger.error("The value from the topic: %s is not valid. %s < %s < %s " %(msg.topic, median-maxValueDelta, lastValue, median+maxValueDelta))
            raise ValueError("The value is outside the acceptable range")
