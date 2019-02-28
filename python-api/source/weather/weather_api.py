import logging

import falcon

import api_utils
from api_utils import checkUser
import weather

logger = logging.getLogger(__name__)


class Weather():

    @checkUser
    def on_post(self, req, resp, userId):

        try:
            result = weather.getMeasurementFromPostalCode(
                req.media['postalCode'], req.media['measurement'])

        except:
            logger.error("Exception. userId: %s." % userId, exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = api_utils.getResponseModel(True, result)


class SunSchedule():

    @checkUser
    def on_post(self, req, resp, userId):

        try:
            result = weather.getSunScheduleFromPostalCode(
                req.media['postalCode'])

        except:
            logger.error("Exception. userId: %s." % userId, exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = api_utils.getResponseModel(True, result)
