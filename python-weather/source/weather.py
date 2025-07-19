# -*- encoding: utf-8 -*-
import logging
import requests
from requests import adapters
import ssl
from urllib3 import poolmanager
import time
from dateutil import tz

import datetime

from stations_list import stationsList
from location_list import locationsList
from geocodes_list import geocodesList
from disk_cache import disk_cache
from docker_secrets import get_docker_secrets
import utils

logger = logging.getLogger(__name__)

googleApiKey = get_docker_secrets("googleApiKey")
aemetApiKey = get_docker_secrets("aemetApiKey")

measurements = {
    "temperature": {
        "observationMeasurementName": "ta",
        "predictionMeasurementName": "temperatura",
    },
    "humidity": {
        "observationMeasurementName": "hr",
        "predictionMeasurementName": "humedadRelativa",
    },
}

# Requiered to fix the AEMET cipher


class TLSAdapter(adapters.HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        """Create and initialize the urllib3 PoolManager."""
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        self.poolmanager = poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLS,
            ssl_context=ctx,
        )


session = requests.session()
session.mount("https://", TLSAdapter())

######################################
# Aemet functions
######################################


def getAemetData(url):
    response = session.get(url, headers={"api_key": aemetApiKey})
    result = response.json()
    try:
        assert result["estado"] == 200
    except AssertionError:
        logger.info(f"status code not 200. decoded response: {result}")
        if result["estado"] == 429:
            response = session.get(url, headers={"api_key": aemetApiKey})
            result = response.json()
            if result["estado"] != 200:
                raise
    
    datosUrl = result["datos"]

    datosResponse = session.get(datosUrl)
    datosResult = datosResponse.json()
    return datosResult


######################################
# Main Program
######################################


@disk_cache(seconds=0)
def getLocationFromPostalCode(postalCode):
    """
    Get the postal code and the location name
    from the coordenates using the Google Maps API
    """

    querystring = {
        "key": googleApiKey,
        "components": "country:ES|postal_code:%s" % postalCode,
    }

    response = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json", params=querystring
    )

    result = response.json()

    # If no results are found, return a dummy location
    if result["status"] == "ZERO_RESULTS":
        return {"lat": 0.0, "lng": 0.0}, "no_location_available"

    assert result["status"] == "OK"
    googleData = result["results"][0]
    locationName = googleData["address_components"][1]["short_name"]
    postalCodeCoordenates = googleData["geometry"]["location"]

    return postalCodeCoordenates, locationName


@disk_cache(seconds=0)
def getTimeZone(postalCodeCoordenates, timestamp=None):
    """
    Get the time zone data from the coordenates
    using the Google Maps API

    Example:
    {
        "dstOffset": 3600,
        "rawOffset": 3600,
        "status": "OK",
        "timeZoneId": "Europe/Madrid",
        "timeZoneName": "Central European Summer Time"
    }
    """

    if not timestamp:
        timestamp = int(time.time())

    querystring = {
        "key": googleApiKey,
        "timestamp": timestamp,
        "location": f"{postalCodeCoordenates['lat']},{postalCodeCoordenates['lng']}",
    }

    response = requests.get(
        "https://maps.googleapis.com/maps/api/timezone/json", params=querystring
    )

    result = response.json()
    # If no results are found, return a dummy location
    if result["status"] == "ZERO_RESULTS":
        return {
            "dstOffset": 3600,
            "rawOffset": 3600,
            "status": "OK",
            "timeZoneId": "Europe/Madrid",
            "timeZoneName": "Central European Summer Time",
        }

    assert result["status"] == "OK"

    return result


@disk_cache(seconds=0)
def getClosestStationId(postalCodeCoordenates):
    """Get the closest station to our coordenates
    """

    closestStation = utils.closest_pair(postalCodeCoordenates, stationsList)
    stationId = closestStation["indicativo"]

    return stationId


@disk_cache(seconds=0)
def getClosestGeocode(postalCodeCoordenates):
    """Get the closest geocode to our coordenates
    """

    closestGeocode = utils.closest_pair(postalCodeCoordenates, geocodesList)
    geocode = closestGeocode["geocode"]

    return geocode


@disk_cache(seconds=900)
def getCurrentWeather(stationId):
    """
    Get the current weather from the selected station
    """
    currentWeatherData = getAemetData(
        f"https://opendata.aemet.es/opendata/api/observacion/convencional/datos/estacion/{stationId}"
    )

    return currentWeatherData


@disk_cache(seconds=0)
def getLocationId(locationName):
    """
    Get the predicted weather for today
    from the selected location
    """

    # Convert the location name to the same format Aemet is using
    firstWord = locationName.split(" ")[0]
    if firstWord in (
        "la",
        "La",
        "Las",
        "El",
        "Els",
        "A",
        "Los",
        "L",
        "O",
        "Les",
        "Os",
        "Es",
    ):
        locationName = locationName.replace(firstWord, "")
        locationName += f", {firstWord}"
        locationName = locationName.strip()

    for location in locationsList:
        if location["nombre"] == locationName:
            return location["id"].replace("id", "")

    raise ValueError("The location name could not be found")


@disk_cache(seconds=3600)
def getTodayPredictedWeather(locationId):

    predictedWeather = getAemetData(
        f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{locationId}"
    )
    weatherForToday = predictedWeather[0]["prediccion"]["dia"][0]

    return weatherForToday


@disk_cache(seconds=3600 * 12)
def getTodaySunSchedule(locationId):
    """
    From the locationId get the sunrise and the sunset,
    convert them to minutes since midnight and return it as
    a tuple (sunrise, sunset)
    """

    timeZoneId = "Europe/Madrid"

    predictedWeather = getAemetData(
        f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/horaria/{locationId}"
    )
    weatherForToday = predictedWeather[0]["prediccion"]["dia"][0]
    timestamp = utils.toUtcTimestamp(
        datetime.datetime.strptime(weatherForToday["fecha"], "%Y-%m-%dT%H:%M:%S"),
        timeZoneId,
    )
    sunrise = weatherForToday["orto"]
    sunset = weatherForToday["ocaso"]

    return timestamp, dateToMinutes(sunrise), dateToMinutes(sunset)


@disk_cache(seconds=60)
def getLatestAlertsURLForArea(area):
    """
    From the area code (first two numbers
    from the geocode) get the latests alerts
    contained in the file available to download
    in the returned URL
    """

    response = session.get(
        f"https://opendata.aemet.es/opendata/api/avisos_cap/ultimoelaborado/area/{area}",
        headers={"api_key": aemetApiKey},
    )
    result = response.json()
    assert result["estado"] == 200
    datosUrl = result["datos"]

    return datosUrl


def dateToMinutes(date):
    """
    From a local (Europe/Madrid) date string with the following format: 07:54
    convert it to minutes since midnight in UTC
    """

    hour, minute = date.split(":")
    localZone = tz.gettz("Europe/Madrid")
    now = datetime.datetime.now(localZone)
    now = now.replace(hour=int(hour), minute=int(minute))
    now = now.astimezone(tz=tz.UTC)
    minutesConverted = now.hour * 60 + now.minute
    return minutesConverted


def getMeasurementFromPostalCode(postalCode, measurement):
    # 1. Get the postal code coordenates from google
    postalCodeCoordenates, locationName = getLocationFromPostalCode(postalCode)
    # 2. Get the closest station to our coordenates
    stationId = getClosestStationId(postalCodeCoordenates)

    # 3. Get the current weather from the selected station
    currentWeather = getCurrentWeather(stationId)

    # Get the last measurement
    lastMeasurement = currentWeather[-1]
    currentTemperature = lastMeasurement[
        measurements[measurement]["observationMeasurementName"]
    ]

    lastUpdateUtcAware = datetime.datetime.strptime(
        lastMeasurement["fint"], "%Y-%m-%dT%H:%M:%S%z"
    )
    lastUpdate = lastUpdateUtcAware.strftime("%Y-%m-%d %H:%M:%S%z")

    # Get the history of the last measurements
    numHours = min(7, len(currentWeather))
    hist = [
        currentWeather[numHour][measurements[measurement]["observationMeasurementName"]]
        for numHour in range(-1, -numHours, -1)
    ]
    hist = list(reversed(hist))

    # 4. Get the predicted weather for today from the location
    locationId = getLocationId(locationName)
    weatherForToday = getTodayPredictedWeather(locationId)

    todayTemperature = weatherForToday[
        measurements[measurement]["predictionMeasurementName"]
    ]
    maxTemp = todayTemperature["maxima"]
    minTemp = todayTemperature["minima"]

    return {
        "hist": hist,
        "min": minTemp,
        "max": maxTemp,
        "lastUpdate": lastUpdate,
        "current": currentTemperature,
        "weatherDataExpanded": lastMeasurement,
    }


def getSunScheduleFromPostalCode(postalCode):
    # 1. Get the location name from the postal code
    _, locationName = getLocationFromPostalCode(postalCode)
    # 2. Get the closest station to our coordenates
    locationId = getLocationId(locationName)
    # 3. Get the sunset and the sunrise from the selected station
    timestamp, sunrise, sunset = getTodaySunSchedule(locationId)

    return {"timestamp": timestamp, "sunrise": sunrise, "sunset": sunset}


def getTimeZoneFromPostalCode(postalCode):
    # 1. Get the location coordenates from the postal code
    postalCodeCoordenates, _ = getLocationFromPostalCode(postalCode)
    # 2. Get the timezone of our coordenates
    locationTimezoneData = getTimeZone(postalCodeCoordenates)

    return locationTimezoneData


def getGeocodeFromPostalCode(postalCode):
    # 1. Get the location coordenates from the postal code
    postalCodeCoordenates, _ = getLocationFromPostalCode(postalCode)
    # 2. Get the closest geocode to our coordenates
    geocode = getClosestGeocode(postalCodeCoordenates)

    return geocode


def getLatestAlertsForPostalCode(postalCode):

    if postalCode == "esp":
        area = "esp"
    else:
        # 1. Get the closest geocode to our postal code
        geocode = getGeocodeFromPostalCode(postalCode)
        area = geocode[0:2]

    # 2. Get the URL with the latest alerts
    dataUrl = getLatestAlertsURLForArea(area)

    return dataUrl
