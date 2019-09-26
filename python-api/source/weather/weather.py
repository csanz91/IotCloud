# -*- encoding: utf-8 -*-

import requests
from requests import adapters
import ssl
from urllib3 import poolmanager
import math
from datetime import datetime
import time 
import pytz

from stations_list import stationsList
from location_list import locationsList
from cache_decorator import cache_disk, clear_cache
from docker_secrets import getDocketSecrets

import sys 
sys.path.append('..')
import datetime_utils

googleApiKey = getDocketSecrets("googleApiKey")
aemetApiKey = getDocketSecrets("aemetApiKey")

measurements = {
    "temperature": {
        "observationMeasurementName": "ta",
        "predictionMeasurementName": "temperatura"
    },
    "humidity": {
        "observationMeasurementName": "hr",
        "predictionMeasurementName": "humedadRelativa"
    }
}

# Requiered to fix the AEMET poor encription
class TLSAdapter(adapters.HTTPAdapter):

    def init_poolmanager(self, connections, maxsize, block=False):
        """Create and initialize the urllib3 PoolManager."""
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        self.poolmanager = poolmanager.PoolManager(
                num_pools=connections,
                maxsize=maxsize,
                block=block,
                ssl_version=ssl.PROTOCOL_TLS,
                ssl_context=ctx)

session = requests.session()
session.mount('https://', TLSAdapter())

######################################
## Aemet functions
######################################


def getAemetData(url):
    response = session.get(url, headers={'api_key': aemetApiKey})
    result = response.json()
    assert result["estado"] == 200
    datosUrl = result["datos"]

    datosResponse = session.get(datosUrl)
    datosResult = datosResponse.json()
    return datosResult


######################################
## Main Program
######################################


# 1. Get the postal code and the location name from the coordenates from google
#
@cache_disk(seconds=0)
def getLocationFromPostalCode(postalCode):

    querystring = {
        "key": googleApiKey,
        "components": "country:ES|postal_code:%s" % postalCode
    }

    response = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params=querystring)

    result = response.json()
    assert result["status"] == "OK"
    googleData = result["results"][0]
    locationName = googleData["address_components"][1]["short_name"]
    postalCodeCoordenates = googleData["geometry"]["location"]

    return postalCodeCoordenates, locationName


# 2. Get the closest station to our coordenates
#
@cache_disk(seconds=0)
def getClosestStationId(postalCodeCoordenates):
    def closest_pair(targetPoint, pointsList):
        distances = {dist(p, targetPoint): p for p in pointsList}
        return distances[min(distances.keys())]

    def dist(p1, p2):
        return math.sqrt((p1['lat'] - p2['lat'])**2 +
                         (p1['lng'] - p2['lng'])**2)

    closestStation = closest_pair(postalCodeCoordenates, stationsList)
    stationId = closestStation['indicativo']

    return stationId


# 3. Get the current weather from the selected station
#
@cache_disk(seconds=1200)
def getCurrentWeather(stationId):
    currentWeatherData = getAemetData(
        u"https://opendata.aemet.es/opendata/api/observacion/convencional/datos/estacion/{stationId}"
        .format(stationId=stationId))

    return currentWeatherData


# 4. Get the predicted weather for today from the location
#
@cache_disk(seconds=0)
def getLocationId(locationName):

    # Convert the location name to the same format Aemet is using
    firstWord = locationName.split(" ")[0]
    if firstWord in ("la", "La", "Las", "El", "Els", "A", "Los", "L", "O",
                     "Les", "Os", "Es"):
        locationName = locationName.replace(firstWord, "")
        locationName += ", %s" % firstWord
        locationName = locationName.strip()

    for location in locationsList:
        if location['nombre'] == locationName:
            return location['id'].replace("id", "")

    raise ValueError("The location name could not be found")


@cache_disk(seconds=3600)
def getTodayPredictedWeather(locationId):

    predictedWeather = getAemetData(
        u"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{locationId}"
        .format(locationId=locationId))
    weatherForToday = predictedWeather[0]["prediccion"]["dia"][0]

    return weatherForToday

@cache_disk(seconds=3600 * 12)
def getTodaySunSchedule(locationId):
    '''
    From the locationId get the sunrise and the sunset,
    convert them to minutes since midnight and return it as
    a tuple (sunrise, sunset)
    '''

    predictedWeather = getAemetData(
        u"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/horaria/{locationId}"
        .format(locationId=locationId))
    weatherForToday = predictedWeather[0]["prediccion"]["dia"][0]
    timestamp = datetime_utils.toUtc(datetime.strptime(weatherForToday['fecha'], '%Y-%m-%d'))
    sunrise = weatherForToday["orto"]
    sunset = weatherForToday["ocaso"]

    return timestamp, dateToMinutes(sunrise), dateToMinutes(sunset)

def dateToMinutes(date):
    '''
    From a date string with the following format: 07:54
    convert it to minutes since midnight
    '''

    hours, minutes = date.split(":")
    return int(hours) * 60 + int(minutes)

def getMeasurementFromPostalCode(postalCode, measurement):
    # 1. Get the postal code coordenates from google
    postalCodeCoordenates, locationName = getLocationFromPostalCode(postalCode)
    # 2. Get the closest station to our coordenates
    stationId = getClosestStationId(postalCodeCoordenates)
    # 3. Get the current weather from the selected station
    currentWeather = getCurrentWeather(stationId)    

    # Get the last measurement
    lastMeasurement = currentWeather[-1]
    currentTemperature = lastMeasurement[measurements[measurement]["observationMeasurementName"]]
    lastUpdate = pytz.UTC.localize(datetime.strptime(lastMeasurement['fint'], '%Y-%m-%dT%H:%M:%S')).strftime("%Y-%m-%d %H:%M:%S%z")

    # Get the history of the last measurements
    numHours = min(7, len(currentWeather))
    hist = []
    for numHour in xrange(-1, -numHours, -1):
        hist.append(currentWeather[numHour][measurements[measurement]["observationMeasurementName"]])
    hist = list(reversed(hist))

    # 4. Get the predicted weather for today from the location
    locationId = getLocationId(locationName)
    weatherForToday = getTodayPredictedWeather(locationId)

    todayTemperature = weatherForToday[measurements[measurement]["predictionMeasurementName"]]
    maxTemp = todayTemperature["maxima"]
    minTemp = todayTemperature["minima"]

    return {
        "hist": hist,
        "min": minTemp,
        "max": maxTemp,
        "lastUpdate": lastUpdate,
        "current": currentTemperature
    }

def getSunScheduleFromPostalCode(postalCode):
    # 1. Get the location name from the postal code
    _, locationName = getLocationFromPostalCode(postalCode)
    # 2. Get the closest station to our coordenates
    locationId = getLocationId(locationName)
    # 3. Get the sunset and the sunrise from the selected station
    timestamp, sunrise, sunset = getTodaySunSchedule(locationId)    

    return {"timestamp": timestamp, "sunrise": sunrise, "sunset": sunset}

clear_cache()

if __name__ == "__main__":
    postalCode = 44770
    print getMeasurementFromPostalCode(postalCode, "temperature")