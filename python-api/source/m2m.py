import logging
import falcon
from dateutil.parser import parse
import calendar

import dbinterface
import influxdb_interface
import api_utils
from api_utils import m2mValidation, getResponseModel
import firebase_notifications
import weather

logger = logging.getLogger(__name__)


class FindSensor:
    def __init__(self, db):
        self.db = db

    @m2mValidation
    def on_get(self, req, resp, locationId, deviceId, sensorId):

        try:
            sensor = dbinterface.findSensor(self.db, locationId, deviceId, sensorId)
        except:
            logger.error("Exception. sensorId: %s" % (sensorId), exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, sensor)


class UserSensors:
    def __init__(self, db):
        self.db = db

    @m2mValidation
    def on_get(self, req, resp, userId):

        try:
            sensors = dbinterface.selectUserSensors(self.db, userId)
        except:
            logger.error("Exception. userId: %s" % (userId), exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, sensors)


class LocationSunSchedule:
    def __init__(self, db):
        self.db = db

    @m2mValidation
    def on_get(self, req, resp, locationId):

        try:
            location = dbinterface.findLocation(self.db, locationId)
            postalCode = location["postalCode"]
            result = weather.getSunSchedule(postalCode)

        except:
            logger.error("Exception. locationId: %s." % locationId, exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = result


class SendNotification:
    def __init__(self, db):
        self.db = db

    @m2mValidation
    def on_post(self, req, resp, locationId):

        try:
            # Extract the request data
            notificationTitle = req.media["notificationTitle"]
            notificationTitleArgs = req.media["notificationTitleArgs"]
            notificationBody = req.media["notificationBody"]
            notificationBodyArgs = req.media["notificationBodyArgs"]

            # Get the user token and the location from the API
            firebaseTokens = dbinterface.getUserFirebaseToken(self.db, locationId)
            location = dbinterface.findLocation(self.db, locationId)

            # Generate the localization args
            notificationTitleInterpolated = [
                arg % location for arg in notificationTitleArgs
            ]
            notificationBodyInterpolated = [
                arg % location for arg in notificationBodyArgs
            ]

            # Send the notification to all the users
            for firebaseToken in firebaseTokens:
                firebase_notifications.sendLocationNotification(
                    locationId,
                    notificationTitle,
                    notificationBody,
                    firebaseToken,
                    notificationBodyArgs=notificationBodyInterpolated,
                    notificationTitleArgs=notificationTitleInterpolated,
                )

        except:
            logger.error("Exception. locationId: %s." % locationId, exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(True)


class M2MSensorData:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @m2mValidation
    def on_post(self, req, resp, userId, locationId, sensorId):

        # First check if the user
        grantedRole = dbinterface.selectUserLocationRole(self.db, userId, locationId)
        if grantedRole < api_utils.Roles.viewer:
            raise falcon.HTTPUnauthorized(
                "Unauthorized", "The user is not authorized to retrive this data."
            )

        try:
            fromDate = calendar.timegm(parse(req.media["from"]).timetuple())
            toDate = calendar.timegm(parse(req.media["to"]).timetuple())
            data = influxdb_interface.getData(
                self.influxdb,
                locationId,
                sensorId,
                fromDate,
                toDate,
                req.media["maxDataPoints"],
            )

            processedData = [
                [
                    value["value"],
                    calendar.timegm(parse(value["time"]).timetuple()) * 1000,
                ]
                for value in data
            ]

        except:
            logger.error(
                "Exception. userId: %s, locationId %s" % (userId, locationId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, processedData)


class M2MUserTags:
    def __init__(self, mongodb):
        self.db = mongodb

    @m2mValidation
    def on_get(self, req, resp, userId, locationId):

        try:
            userLocations = dbinterface.selectLocations(
                self.db, userId, includeInherited=True
            )

            locationTags = []
            deviceTags = []
            sensorTags = []
            for location in userLocations:
                # Filter the objects by location
                if locationId != "*" and locationId != location["_id"]:
                    continue
                locationTags.append(
                    {"text": location["locationName"], "value": location["_id"]}
                )
                for device in location["devices"]:
                    deviceTags.append(
                        {"text": device["deviceId"], "value": device["deviceId"]}
                    )
                    for sensor in device["sensors"]:
                        if sensor["sensorType"] in ["analog", "thermostat"]:
                            sensorTags.append(
                                {
                                    "text": sensor["sensorName"],
                                    "value": sensor["sensorId"],
                                }
                            )

            response = {
                "locationTags": locationTags,
                "deviceTags": deviceTags,
                "sensorTags": sensorTags,
            }

        except:
            logger.error("Exception. userId: %s" % (userId), exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, response)


class M2MLocationDevices:
    def __init__(self, db):
        self.db = db

    @m2mValidation
    def on_get(self, req, resp, locationId):

        try:
            location = dbinterface.findLocation(self.db, locationId)
        except:
            logger.error("Exception. locationId: %s" % (locationId), exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, location)
