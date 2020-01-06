import logging

import falcon

import weather
import utils

logger = logging.getLogger(__name__)


class Weather():

    def on_post(self, req, resp, postalCode):

        try:
            result = weather.getMeasurementFromPostalCode(
                postalCode, req.media['measurement'])

        except:
            logger.error(
                f"Exception for the postal code: {postalCode}.", exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = utils.getResponseModel(True, result)


class SunSchedule():

    def on_get(self, req, resp, postalCode):

        try:
            result = weather.getSunScheduleFromPostalCode(postalCode)

        except:
            logger.error(
                f"Exception for the postal code: {postalCode}.", exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = utils.getResponseModel(True, result)



class TimeZone():

    def on_get(self, req, resp, postalCode):

        try:
            result = weather.getTimeZoneFromPostalCode(postalCode)

        except:
            logger.error(
                f"Exception for the postal code: {postalCode}.", exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = utils.getResponseModel(True, result)

class LatestsWeatherAlerts():

    def on_get(self, req, resp, postalCode):

        try:
            result = weather.getLatestAlertsForPostalCode(postalCode)

        except:
            logger.error(
                f"Exception for the postal code: {postalCode}.", exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = utils.getResponseModel(True, result)

class Geocode():

    def on_get(self, req, resp, postalCode):

        try:
            result = weather.getGeocodeFromPostalCode(postalCode)

        except:
            logger.error(
                f"Exception for the postal code: {postalCode}.", exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = utils.getResponseModel(True, result)