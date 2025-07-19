import logging

import falcon

from api_utils import getResponseModel, getToken
from docker_secrets import get_docker_secrets
import influxdb_interface

secret = get_docker_secrets("wind_auth_secret")

logger = logging.getLogger(__name__)


class LocationTracker:
    auth = {"authDisabled": True}

    def __init__(self, influxdb):
        self.influxdb = influxdb
        
    def on_post(self, req, resp, trackerid):

        token = getToken(req)

        if token != secret:
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="The user is not authorized to access this data.",
            )

        try:
            influxdb_interface.saveLocationTracking(self.influxdb, trackerid, req.media)

        except:
            logger.error(
                f"Exception.",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
               title="Bad Request", description="The request can not be completed."
            )

        resp.media = getResponseModel(True)
