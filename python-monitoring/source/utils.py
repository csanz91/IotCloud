import time

with open("/app/hostname", "r") as r:
    hostname = r.read().strip()


class MetricRate:
    """ Calculate the positive rate (values/second) of the passed metric
    """

    def __init__(self):
        self.lastMetric = None
        self.lastMetricEpoch = None

    def getRate(self, value):
        currentTime = time.time()
        rate = 0.0
        if self.lastMetric and self.lastMetricEpoch and value > self.lastMetric:
            valueDiff = value - self.lastMetric
            secondsElapsed = currentTime - self.lastMetricEpoch
            rate = valueDiff / secondsElapsed

        self.lastMetricEpoch = currentTime
        self.lastMetric = value

        return rate


def getHostname():
    return hostname
