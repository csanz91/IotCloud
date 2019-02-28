import logging
import falcon

import dbinterface
import api_utils
from api_utils import m2mValidation, getResponseModel
from weather import weather

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