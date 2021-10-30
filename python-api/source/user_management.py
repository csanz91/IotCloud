import logging

import falcon
from auth0.v3 import exceptions

from api_utils import getResponseModel
import dbinterface


logger = logging.getLogger(__name__)


class Login:

    auth = {"authDisabled": True}

    def __init__(self, auth0, middleware):
        self.auth0 = auth0
        self.middleware = middleware

    def on_post(self, req, resp):

        try:
            token = self.auth0.login(req.media["email"], req.media["password"])
        except exceptions.Auth0Error as e:
            logger.error(e.message,)
            logger.error("Req.media: %s" % (req.media),)
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

        self.middleware.verifyToken(req, token)
        respData = {"token": token, "userId": req.context["auth"]["subject"]}
        resp.media = getResponseModel(True, respData)


class RecoverPassword:

    auth = {"authDisabled": True}

    def __init__(self, auth0):
        self.auth0 = auth0

    def on_post(self, req, resp):

        try:
            response = self.auth0.recoverPassword(req.media["email"])
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


class UserManagement:

    auth = {"authDisabled": True}

    def __init__(self, db, auth0):
        self.db = db
        self.auth0 = auth0

    def on_post(self, req, resp):

        try:
            userId = None
            name = req.media["name"]
            lastName = req.media["lastName"]
            email = req.media["email"]
            password = req.media["password"]
            wantUpdates = req.media["wantUpdates"]
            gdprAcceptance = req.media["gdprAcceptance"]
            language = req.media["language"]

            # GDPR is mandatory
            if not gdprAcceptance:
                msg = "The GDPR must be accepted in order to enter the platform"
                resp.media = getResponseModel(False, msg)
                return

            # Register user in the auth system
            userId = self.auth0.addUser(email, name, password)

            # Register user in the database
            userId = dbinterface.insertUser(
                self.db,
                name,
                lastName,
                email,
                wantUpdates,
                gdprAcceptance,
                language,
                userId=userId,
            )

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
            # If the user has been registered but failed the db operation
            # then remove it
            if userId:
                logger.warning(
                    "The user has been registered in Auth0 but the"
                    "database operation failed",
                    extra={"area": "users"},
                )
                self.auth0.deleteUser(userId)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, userId)
