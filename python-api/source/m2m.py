import logging
import falcon

import dbinterface
import api_utils
from api_utils import m2mValidation, getResponseModel
from weather import weather
import firebase_notifications

logger = logging.getLogger(__name__)


class FindSensor():

    def __init__(self, db):
        self.db = db

    @m2mValidation
    def on_get(self, req, resp, locationId, deviceId, sensorId):

        try:
            sensor = dbinterface.findSensor(self.db, locationId, deviceId, sensorId)
        except:
            logger.error("Exception. sensorId: %s" % (sensorId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )

        resp.media = getResponseModel(True, sensor)


class UserSensors():

    def __init__(self, db):
        self.db = db

    @m2mValidation
    def on_get(self, req, resp, userId):

        try:
            sensors = dbinterface.selectUserSensors(self.db, userId)
        except:
            logger.error("Exception. userId: %s" % (userId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )

        resp.media = getResponseModel(True, sensors)


class LocationSunSchedule():

    def __init__(self, db):
        self.db = db

    @m2mValidation
    def on_get(self, req, resp, locationId):

        try:
            location = dbinterface.findLocation(self.db, locationId)
            postalCode = location["postalCode"]
            result = weather.getSunScheduleFromPostalCode(postalCode)

        except:
            logger.error("Exception. locationId: %s." % locationId, exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = api_utils.getResponseModel(True, result)


class SendNotification():

    def __init__(self, db):
        self.db = db

    @m2mValidation
    def on_post(self, req, resp, locationId):

        try:
            # Extract the request data
            notificationTitle = req.media['notificationTitle']
            notificationTitleArgs = req.media['notificationTitleArgs']
            notificationBody = req.media['notificationBody']
            notificationBodyArgs = req.media['notificationBodyArgs']

            # Get the user token and the location from the API
            firebaseTokens = dbinterface.getUserFirebaseToken(self.db, locationId)
            location = dbinterface.findLocation(self.db, locationId)

            # Generate the localization args
            notificationTitleInterpolated = [arg % location for arg in notificationTitleArgs]
            notificationBodyInterpolated = [arg % location for arg in notificationBodyArgs]

            # Send the notification to all the users
            for firebaseToken in firebaseTokens:
                firebase_notifications.sendLocationNotification(locationId, notificationTitle, notificationBody, firebaseToken, notificationBodyArgs=notificationBodyInterpolated, notificationTitleArgs=notificationTitleInterpolated)

        except:
            logger.error("Exception. locationId: %s." % locationId, exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = api_utils.getResponseModel(True)
