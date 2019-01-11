# -*- encoding: utf-8 -*-

import requests
import math
from datetime import datetime
import pytz

from stations_list import stationsList
from location_list import locationsList
from cache_decorator import cache_disk, clear_cache
from docker_secrets import getDocketSecrets
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

######################################
## Aemet functions
######################################


def getAemetData(url):
    response = requests.get(url, headers={'api_key': aemetApiKey})
    result = response.json()
    assert result["estado"] == 200
    datosUrl = result["datos"]

    datosResponse = requests.get(datosUrl)
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


def getMeasurementFromPostalCode(postalCode, measurement):
    # 1. Get the postal code coordenates from google
    postalCodeCoordenates, locationName = getLocationFromPostalCode(postalCode)
    # 2. Get the closest station to our coordenates
    stationId = getClosestStationId(postalCodeCoordenates)
    # 3. Get the current weather from the selected station
    currentWeather = getCurrentWeather(stationId)

    #currentHour = datetime.now().replace(minute=0, second=0, microsecond=0)
    

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


clear_cache()

if __name__ == "__main__":
    postalCode = 44770
    print getMeasurementFromPostalCode(postalCode, "temperature")