import logging

import falcon

from api_utils import checkUser, getResponseModel
import influxdb_interface

logger = logging.getLogger(__name__)


class TariffCostFlexi:

    def __init__(self, influxdb):
        self.influxdb = influxdb

    @checkUser
    def on_post(self, req, resp, userId):

        try:
            result = influxdb_interface.getEnergyTariffsCostFlexi(
                self.influxdb,
                req.media["initialTimestamp"],
                req.media["finalTimestamp"],
            )
        except:
            logger.error(
                f"Exception. userId: {userId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                title="Bad Request", description="The request can not be completed."
            )

        resp.media = getResponseModel(True, result)

class TariffCostTE:

    def __init__(self, influxdb):
        self.influxdb = influxdb

    @checkUser
    def on_post(self, req, resp, userId):

        try:
            result = influxdb_interface.getEnergyTariffsCostTE(
                self.influxdb,
                req.media["initialTimestamp"],
                req.media["finalTimestamp"],
            )
        except:
            logger.error(
                f"Exception. userId: {userId}",
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                title="Bad Request", description="The request can not be completed."
            )

        resp.media = getResponseModel(True, result)
