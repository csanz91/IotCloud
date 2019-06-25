import logging

import falcon

import api_utils
from api_utils import checkUser
import bitcoin_price
import time

logger = logging.getLogger(__name__)


class BitcoinCurrent():

    @checkUser
    def on_get(self, req, resp, userId):

        try:
            result = bitcoin_price.getCurrentPrice()

        except:
            logger.error("Exception. userId: %s." % userId, exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = api_utils.getResponseModel(True, result)


class BitcoinHistorical():

    @checkUser
    def on_get(self, req, resp, userId):

        try:
            result = bitcoin_price.getHistoricalPrice()

        except:
            logger.error("Exception. userId: %s." % userId, exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = api_utils.getResponseModel(True, result)


class BitcoinPrice():
    @checkUser
    def on_get(self, req, resp, userId):

        try:
            historicalPrice = bitcoin_price.getHistoricalPrice()
            currentPrice = bitcoin_price.getCurrentPrice()

            data = {'current': currentPrice, 'hist': historicalPrice, 'lastUpdate': int(time.time())}

        except:
            logger.error("Exception. userId: %s." % userId, exc_info=True)
            raise falcon.HTTPBadRequest('Bad Request',
                                        'The request can not be completed.')

        resp.media = api_utils.getResponseModel(True, data)
