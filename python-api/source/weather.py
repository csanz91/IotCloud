import logging

import requests


logger = logging.getLogger(__name__)

weatherServiceUrl = "http://weather:5003/api"


def getWeather(postalCode, measurement):
    postData = {"measurement": measurement}
    r = requests.post(
        f"{weatherServiceUrl}/postalcode/{postalCode}/weather", json=postData,
    )
    return r.json()


def getSunSchedule(postalCode):
    r = requests.get(f"{weatherServiceUrl}/postalcode/{postalCode}/sunschedule")
    return r.json()


def getTimeZone(postalCode):
    r = requests.get(f"{weatherServiceUrl}/postalcode/{postalCode}/timezone")
    result = r.json()
    return result["data"]

def getWind(latitude, longitude):
    postData = {"latitude": latitude, "longitude": longitude}
    r = requests.post(
        f"{weatherServiceUrl}/wind", json=postData
    )
    if r.status_code != 200:
        raise Exception(f"API request failed (status code: {r.status_code}). "
                  f"Error: {r.text}")
    return r.json()