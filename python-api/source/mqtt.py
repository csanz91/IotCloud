import logging
import time

import falcon
import jwt

import api_utils
from api_utils import Roles
import dbinterface
from docker_secrets import getDocketSecrets

logger = logging.getLogger(__name__)
secret = getDocketSecrets("mqtt_auth_secret")


class MqttActions:
    ADDED = "added"
    UPDATED = "updated"
    DELETED = "deleted"


class MqttRoles:
    user = "User"
    device = "Device"
    subdevice = "Subdevice"
    admin = "Admin"


class ACL:
    NO_ACCESS = 0
    READ = 1
    WRITE = 2
    READ_AND_WRITE = 3
    SUBSCRIBE = 4
    READ_AND_SUBSCRIBE = 5
    WRITE_AND_SUBSCRIBE = 6
    READ_AND_WRITE_AND_SUBSCRIBE = 7


def isReadOnlyAcl(acc):
    return acc in (ACL.READ, ACL.SUBSCRIBE, ACL.READ_AND_SUBSCRIBE)


def isWriteAcl(acc):
    return acc in (
        ACL.WRITE,
        ACL.READ_AND_WRITE,
        ACL.WRITE_AND_SUBSCRIBE,
        ACL.READ_AND_WRITE_AND_SUBSCRIBE,
    )


def raiseUnauthorized():
    raise falcon.HTTPUnauthorized(
        "Unauthorized", "The user is not authorized to access this topic."
    )


class MqttAuth:

    auth = {"authDisabled": True}

    def on_post(self, req, resp):

        try:
            token = req.params["username"]
            tokenData = verifyMqttToken(token)
            assert tokenData["role"]
            logger.info(f"Granted MQTT connection to the user with id: {token}")

        except:
            logger.error("Exception. params: %s" % (req.params), exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )
        resp.media = api_utils.getResponseModel(True)


class MqttAcl:

    auth = {"authDisabled": True}

    def __init__(self, db):
        self.db = db

    def on_post(self, req, resp):

        try:
            self.verifyPermissions(req)
        except falcon.HTTPUnauthorized:
            raise
        except:
            logger.error("Exception. params: %s" % (req.params), exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )
        resp.media = api_utils.getResponseModel(True)

    def verifyPermissions(self, req):
        token = req.params["username"]
        tokenData = verifyMqttToken(token)

        grantedRole = tokenData["role"]
        topic = req.params["topic"]
        acc = int(req.params["acc"])

        if topic.startswith("v1/ota/update/"):
            # All can read in this topic, only admin can write
            if not isReadOnlyAcl(acc) and grantedRole != MqttRoles.admin:
                raiseUnauthorized()
            return

        # v1/locationId/deviceId/sensorId/...
        subtopics = topic.split("/")
        # version = subtopics[0]
        locationIdRequested = subtopics[1]
        deviceIdRequested = subtopics[2]
        endpoint = subtopics[-1]

        if grantedRole == MqttRoles.user:
            self.verifyUserPermissions(tokenData, acc, locationIdRequested)

        elif grantedRole == MqttRoles.device:
            self.verifyDevicePermissions(
                tokenData,
                acc,
                subtopics,
                locationIdRequested,
                deviceIdRequested,
                endpoint,
            )
        elif grantedRole == MqttRoles.subdevice:
            self.verifySubdevicePermissions(
                tokenData,
                acc,
                subtopics,
                locationIdRequested,
                deviceIdRequested,
                endpoint,
            )

        elif grantedRole != MqttRoles.admin:
            raiseUnauthorized()

    def isNotAllowedMqttTopic(self, acc, subtopics, endpoint):
        return (
            isWriteAcl(acc)
            and endpoint
            not in ["value", "status", "setState", "state", "ip", "version", "reset"]
            and subtopics[4] not in ["aux", "ota"]
        )

    def verifySubdevicePermissions(
        self,
        tokenData,
        acc,
        subtopics,
        locationIdRequested,
        deviceIdRequested,
        endpoint,
    ):
        grantedLocationId = tokenData["locationId"]
        grantedDeviceId = tokenData["deviceId"]
        grantedSubdeviceId = tokenData["subdeviceId"]

        if (
            grantedLocationId != locationIdRequested
            or (
                grantedDeviceId != deviceIdRequested
                and grantedSubdeviceId != deviceIdRequested
            )
            or (self.isNotAllowedMqttTopic(acc, subtopics, endpoint))
        ):
            raiseUnauthorized()

    def verifyDevicePermissions(
        self,
        tokenData,
        acc,
        subtopics,
        locationIdRequested,
        deviceIdRequested,
        endpoint,
    ):
        grantedLocationId = tokenData["locationId"]
        grantedDeviceId = tokenData["deviceId"]

        if (
            grantedLocationId != locationIdRequested
            or grantedDeviceId != deviceIdRequested
            or (self.isNotAllowedMqttTopic(acc, subtopics, endpoint))
        ):
            raiseUnauthorized()

    def verifyUserPermissions(self, tokenData, acc, locationIdRequested):
        role = dbinterface.selectUserLocationRole(
            self.db, tokenData["userId"], locationIdRequested
        )
        if not role or (isWriteAcl(acc) and role <= Roles.viewer):
            raiseUnauthorized()


class MqttSuperUser:

    auth = {"authDisabled": True}

    def on_post(self, req, resp):

        try:

            token = req.params["username"]
            tokenData = verifyMqttToken(token)

            if tokenData["role"] != MqttRoles.admin:
                raiseUnauthorized()

        except falcon.HTTPUnauthorized:
            raise
        except:
            logger.error("Exception. params: %s" % (req.params), exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )
        resp.media = api_utils.getResponseModel(True)


def generateMqttToken(userId, role, locationId=None, deviceId=None, subdeviceId=None):

    if role in [MqttRoles.user, MqttRoles.admin]:
        tokenData = {"userId": userId, "exp": int(time.time()) + 3600 * 24 * 7}

    elif role == MqttRoles.device:
        tokenData = {"issuerId": userId, "deviceId": deviceId, "locationId": locationId}
    elif role == MqttRoles.subdevice:
        tokenData = {
            "issuerId": userId,
            "deviceId": deviceId,
            "subdeviceId": subdeviceId,
            "locationId": locationId,
        }
    else:
        return None

    tokenData["role"] = role
    return jwt.encode(tokenData, secret, algorithm="HS256")


def verifyMqttToken(token):
    return jwt.decode(token, secret, algorithms=["HS256"])
