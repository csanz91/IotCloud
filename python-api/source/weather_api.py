import logging

import falcon

from api_utils import checkUser, getToken
from docker_secrets import getDocketSecrets

import weather

secret = getDocketSecrets("wind_auth_secret")

logger = logging.getLogger(__name__)


class Weather:
    @checkUser
    def on_post(self, req, resp, userId):

        try:
            result = weather.getWeather(
                req.media["postalCode"], req.media["measurement"]
            )
        except:
            logger.error(
                f"Exception. userId: {userId}",
                exc_info=True,
                extra={"area": "weather"},
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = result


class SunSchedule:
    @checkUser
    def on_post(self, req, resp, userId):

        try:
            result = weather.getSunSchedule(req.media["postalCode"])

        except:
            logger.error(
                f"Exception. userId: {userId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = result

class GarminWind:
    auth = {"authDisabled": True}

    def on_post(self, req, resp):

        token = getToken(req)

        if token != secret:
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="The user is not authorized to access this data.",
            )

        try:
            result = weather.getWind(req.media["latitude"], req.media["longitude"])

        except:
            logger.error(
                f"Exception.",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = result
