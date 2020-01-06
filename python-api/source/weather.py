import logging

import requests


logger = logging.getLogger(__name__)

weatherServiceUrl = "http://weather:5003/api"


def getWeather(postalCode, measurement):
    postData = {
        "measurement": measurement
    }
    r = requests.post("%s/postalcode/%s/weather" %
                      (weatherServiceUrl, postalCode), json=postData)
    result = r.json()
    return result


def getSunSchedule(postalCode):

    r = requests.get("%s/postalcode/%s/sunschedule" %
                     (weatherServiceUrl, postalCode))
    result = r.json()
    return result
