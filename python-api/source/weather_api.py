import logging

import falcon

import api_utils
from api_utils import checkUser
import weather

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
                extra={"area": "weather"},
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = result
