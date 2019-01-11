import logging
import time

import falcon
import jwt

import api_utils
import dbinterface
from api_utils import Roles
import dbinterface
from docker_secrets import getDocketSecrets

logger = logging.getLogger(__name__)
secret = getDocketSecrets('mqtt_auth_secret')

class MqttRoles:
    user = 'User'
    device = 'Device'
    admin = "Admin"


def raiseUnauthorized():
    raise falcon.HTTPUnauthorized(
        'Unauthorized',
        'The user is not authorized to access this topic.'
    )

class MqttAuth():

    auth = {
        'authDisabled': True
    }

    def on_post(self, req, resp):

        try:
            token = req.params['username']
            tokenData = verifyMqttToken(token)
            assert tokenData['role']
            logger.info(
                "Granted MQTT connection to the user with id: %s" % token)

        except:
            logger.error("Exception. params: %s" % (req.params), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )
        resp.media = api_utils.getResponseModel(True)


class MqttAcl():

    auth = {
        'authDisabled': True
    }

    def __init__(self, db):
        self.db = db

    def on_post(self, req, resp):

        try:
            token = req.params['username']
            tokenData = verifyMqttToken(token)

            grantedRole = tokenData['role']
            topic = req.params['topic']

            # v1/locationId/deviceId/sensorId/...
            subtopics = topic.split('/')
            #version = subtopics[0]
            locationIdRequested = subtopics[1]
            deviceIdRequested = subtopics[2]
            endpoint = subtopics[-1]
            acc = int(req.params['acc']) # 1: read only access, 2: read-write

            if grantedRole==MqttRoles.user:
                role = dbinterface.selectUserLocationRole(self.db, tokenData['userId'], locationIdRequested)
                if not role or (acc==2 and role <= Roles.viewer):
                    raiseUnauthorized()

            elif grantedRole==MqttRoles.device:
                grantedLocationId = tokenData['locationId']
                grantedDeviceId = tokenData['deviceId']

                if grantedLocationId != locationIdRequested or grantedDeviceId != deviceIdRequested or (acc == 2 and endpoint not in ["value", "status", "setState", "state"] and subtopics[4]!="aux"):
                    raiseUnauthorized()

            elif grantedRole!=MqttRoles.admin:
                raiseUnauthorized()

        except falcon.HTTPUnauthorized:
            raise
        except:
            logger.error("Exception. params: %s" % (req.params), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )
        resp.media = api_utils.getResponseModel(True)


class MqttSuperUser():

    auth = {
        'authDisabled': True
    }

    def on_post(self, req, resp):

        try:

            token = req.params['username']
            tokenData = verifyMqttToken(token)

            if tokenData['role']!=MqttRoles.admin:
                raiseUnauthorized()

        except falcon.HTTPUnauthorized:
            raise
        except:
            logger.error("Exception. params: %s" % (req.params), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )
        resp.media = api_utils.getResponseModel(True)


def generateMqttToken(userId, role, locationId=None, deviceId=None):

    if role == MqttRoles.user or role == MqttRoles.admin:
        tokenData = {"userId": userId,
                     "exp": int(time.time())+3600*24*7}

    elif role == MqttRoles.device:
        tokenData = {"issuerId": userId,
                     "deviceId": deviceId,
                     "locationId": locationId}
    else:
        return None

    
    tokenData["role"] = role
    encoded = jwt.encode(tokenData, secret, algorithm='HS256')
    return encoded


def verifyMqttToken(token):
    decoded = jwt.decode(token, secret, algorithm='HS256')
    return decoded
