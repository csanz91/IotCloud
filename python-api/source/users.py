import logging
import inspect

import falcon
from auth0 import exceptions

import dbinterface
import api_utils
from api_utils import checkUser, getResponseModel
from mqtt import generateMqttToken, MqttRoles


logger = logging.getLogger(__name__)


class Users:
    def __init__(self, db, auth0):
        self.db = db
        self.auth0 = auth0

    @checkUser
    def on_get(self, req, resp, userId):

        try:
            user = dbinterface.selectUserInheritedData(self.db, userId)
        except:
            logger.error(
                f"Exception. userId: {userId}", exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, user)

    @checkUser
    def on_put(self, req, resp, userId):

        try:

            # The relevant fields can not be edited. Auth0????
            # if 'name' in req.media:
            #    self.auth0.updateUser(userId, {'given_name': req.media['name']})

            response = dbinterface.updateUser(self.db, userId, req.media)

        except:
            logger.error(
                f"Exception. req.media: {req.media}",
                exc_info=True,
                extra={"area": "users"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(response)

    @checkUser
    def on_delete(self, req, resp, userId):

        try:
            self.auth0.deleteUser(userId)
            response = dbinterface.deleteUser(self.db, userId)

        except exceptions.Auth0Error as e:
            logger.error(e.message)
            logger.error("Req.media: %s" % (req.media))
            raise falcon.HTTPBadRequest("Error", e.message)
        except:
            logger.error(
                f"Exception. req.media: {req.media}",
                exc_info=True,
                extra={"area": "users"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(response)


class ValidateLocationPermissions:
    def __init__(self, db):
        self.db = db

    @checkUser
    def on_get(self, req, resp, userId):

        try:
            pendingShares = dbinterface.getPendingValidateShares(self.db, userId)
        except:
            logger.error(
                f"Exception. userId: {userId}", exc_info=True,
            )

            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, pendingShares)

    @checkUser
    def on_post(self, req, resp, userId):

        try:
            # Check we are the user to validate the share
            shareId = req.media["shareId"]
            locationShare = dbinterface.selectShare(self.db, shareId)
            assert locationShare["sharedToUserId"] == userId

            dbinterface.validateLocationPermissions(self.db, shareId)
        except:
            logger.error(
                f"Exception. userId: {userId}", exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True)


class ChangePassword:
    def __init__(self, auth0):
        self.auth0 = auth0

    @checkUser
    def on_post(self, req, resp, userId):

        try:
            response = self.auth0.changePassword(userId, req.media["password"])
        except exceptions.Auth0Error as e:
            logger.error(e.message)
            logger.error("Req.media: %s" % (req.media))
            raise falcon.HTTPBadRequest("Error", e.message)
        except:
            logger.error(
                f"Exception. req.media: {req.media}",
                exc_info=True,
                extra={"area": "users"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, response)


class MqttUserToken:
    @checkUser
    def on_get(self, req, resp, userId):

        try:
            token = generateMqttToken(userId, MqttRoles.user)
            assert token
        except:
            logger.error(
                f"Exception. userId: {userId}", exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, token)


class FirebaseUserToken:
    def __init__(self, db):
        self.db = db

    @checkUser
    def on_post(self, req, resp, userId):

        try:
            # Check we are the user to validate the share
            firebaseToken = req.media["firebaseToken"]
            dbinterface.setUserFirebaseToken(self.db, userId, firebaseToken)

        except:
            logger.error(
                f"Exception. req.media: {req.media}",
                exc_info=True,
                extra={"area": "users"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True)
