import logging
import falcon

import dbinterface
import api_utils
from api_utils import m2mValidation, getResponseModel

logger = logging.getLogger(__name__)

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