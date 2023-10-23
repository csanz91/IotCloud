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
            logger.error(
                f"Exception. sensorId: {sensorId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
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
            logger.error(
                f"Exception. userId: {userId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
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
            logger.error(
                f"Exception. locationId: {locationId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
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
            logger.error(
                f"Exception. locationId: {locationId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
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
                title="Unauthorized",
                description="The user is not authorized to retrive this data.",
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
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = getResponseModel(True, processedData)


def getSensorsNames(db, userId, locationId):
    sensorsNames = {}
    devices = dbinterface.selectDevices(db, userId, locationId)
    for device in devices:
        for sensor in device["sensors"]:
            sensorsNames[sensor["sensorId"]] = sensor["sensorName"]

    return sensorsNames


def getDevicesNames(db, userId, locationId):
    devicesNames = {}
    devices = dbinterface.selectDevices(db, userId, locationId)
    for device in devices:
        sensorsNames = [sensor["sensorName"] for sensor in device["sensors"]]
        devicesNames[device["deviceId"]] = ", ".join(sensorsNames)

    return devicesNames


class M2MSensorActionData:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @m2mValidation
    def on_post(self, req, resp, userId, locationId, sensorId):
        # First check if the user
        grantedRole = dbinterface.selectUserLocationRole(self.db, userId, locationId)
        if grantedRole < api_utils.Roles.viewer:
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="The user is not authorized to retrive this data.",
            )

        try:
            fromDate = calendar.timegm(parse(req.media["from"]).timetuple())
            toDate = calendar.timegm(parse(req.media["to"]).timetuple())
            data = influxdb_interface.getActionsData(
                self.influxdb, locationId, sensorId, fromDate, toDate
            )

            processedData = []
            for value in data:
                action = value["state"]
                if action is None:
                    action = value["setToogle"]
                processedData.append(
                    (
                        str(action),
                        calendar.timegm(parse(value["time"]).timetuple()) * 1000,
                    )
                )

        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = getResponseModel(True, processedData)


class M2MLocationActionData:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @m2mValidation
    def on_post(self, req, resp, userId, locationId):
        # First check if the user
        grantedRole = dbinterface.selectUserLocationRole(self.db, userId, locationId)
        if grantedRole < api_utils.Roles.viewer:
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="The user is not authorized to retrive this data.",
            )

        try:
            fromDate = calendar.timegm(parse(req.media["from"]).timetuple())
            toDate = calendar.timegm(parse(req.media["to"]).timetuple())
            data = influxdb_interface.getLocationActionsData(
                self.influxdb, locationId, fromDate, toDate
            )

            sensorsNames = getSensorsNames(self.db, userId, locationId)

            processedData = []
            for value in data:
                try:
                    sensorsName = sensorsNames[value["sensorId"]]
                except KeyError:
                    continue

                action = value["state"]
                if action is None:
                    action = value["setToogle"]

                processedData.append(
                    (
                        calendar.timegm(parse(value["time"]).timetuple()) * 1000,
                        sensorsName,
                        str(action),
                    )
                )

        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = getResponseModel(True, processedData)


class M2MLocationDevicesStatusStats:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @m2mValidation
    def on_post(self, req, resp, userId, locationId):
        # First check if the user
        grantedRole = dbinterface.selectUserLocationRole(self.db, userId, locationId)
        if grantedRole < api_utils.Roles.viewer:
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="The user is not authorized to retrive this data.",
            )

        try:
            fromDate = calendar.timegm(parse(req.media["from"]).timetuple())
            toDate = calendar.timegm(parse(req.media["to"]).timetuple())
            data = influxdb_interface.getDevicesStatusStats(
                self.influxdb, locationId, fromDate, toDate
            )

            devicesNames = getDevicesNames(self.db, userId, locationId)

            processedData = []
            for value in data:
                try:
                    deviceNames = devicesNames[value["deviceId"]]
                except KeyError:
                    continue

                processedData.append(
                    (
                        calendar.timegm(parse(value["time"]).timetuple()) * 1000,
                        deviceNames,
                        value["reconnections"],
                    )
                )

        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = getResponseModel(True, processedData)


class M2MLocationDeviceStatus:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @m2mValidation
    def on_post(self, req, resp, userId, locationId, deviceId):
        # First check if the user
        grantedRole = dbinterface.selectUserLocationRole(self.db, userId, locationId)
        if grantedRole < api_utils.Roles.viewer:
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="The user is not authorized to retrive this data.",
            )

        try:
            fromDate = calendar.timegm(parse(req.media["from"]).timetuple())
            toDate = calendar.timegm(parse(req.media["to"]).timetuple())
            data = influxdb_interface.getDeviceStatus(
                self.influxdb, locationId, deviceId, fromDate, toDate
            )

            processedData = [
                (
                    calendar.timegm(parse(value["time"]).timetuple()) * 1000,
                    value["status"],
                )
                for value in data
            ]
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
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
                if locationId not in ["*", location["_id"]]:
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
            logger.error(
                f"Exception. userId: {userId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
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
            logger.error(
                f"Exception. locationId: {locationId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = getResponseModel(True, location)


class M2MModulesLocations:
    def __init__(self, db):
        self.db = db

    @m2mValidation
    def on_get(self, req, resp):
        try:
            locations = dbinterface.findModulesLocations(self.db)
        except:
            logger.error(
                "Exception.",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = getResponseModel(True, locations)
