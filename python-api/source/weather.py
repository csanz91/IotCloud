import logging

import requests


logger = logging.getLogger(__name__)

weatherServiceUrl = "http://weather:5003/api"


def getWeather(postalCode, measurement):
    postData = {"measurement": measurement}
    r = requests.post(
        f"{weatherServiceUrl}/postalcode/{postalCode}/weather", json=postData,
    )
    result = r.json()
    return result


def getSunSchedule(postalCode):
    r = requests.get(f"{weatherServiceUrl}/postalcode/{postalCode}/sunschedule")
    result = r.json()
    return result


def getTimeZone(postalCode):
    r = requests.get(f"{weatherServiceUrl}/postalcode/{postalCode}/timezone")
    result = r.json()
    return result["data"]
