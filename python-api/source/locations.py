import logging

import falcon

import dbinterface
import api_utils
import inspect
from api_utils import checkLocationPermissions, checkUser, checkShareOwner, Roles

logger = logging.getLogger(__name__)


class UserLocations:
    def __init__(self, db):
        self.db = db

    @checkUser
    def on_post(self, req, resp, userId):

        try:
            locationId = dbinterface.insertLocation(
                self.db,
                userId,
                req.media["locationName"],
                req.media["postalCode"],
                req.media["city"],
                color=req.media.get("color", None),
            )

        except:
            logger.error("Exception. userId: %s." % userId, exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(True, locationId)

    @checkUser
    def on_get(self, req, resp, userId):

        try:
            locations = dbinterface.selectLocations(self.db, userId, True)
        except:
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(True, locations)


class Locations:
    def __init__(self, db):
        self.db = db

    # As the locations are individual per user, anyone can edit
    # their own location. To update a shared location field
    # the requiered roles are checked inside each function
    @checkLocationPermissions(Roles.viewer)
    def on_put(self, req, resp, userId, locationId):

        try:
            result = dbinterface.updateLocation(self.db, userId, locationId, req.media)

        except:
            logger.error(
                "Exception. userId: %s, locationId %s" % (userId, locationId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(result)

    @checkLocationPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId):

        try:
            location = dbinterface.selectLocation(self.db, userId, locationId, True)
        except:
            logger.error(
                "Exception. userId: %s, locationId: %s" % (userId, locationId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(True, location)

    @checkLocationPermissions(Roles.viewer)
    def on_delete(self, req, resp, userId, locationId):

        try:
            result = dbinterface.deleteLocation(self.db, userId, locationId)
        except:
            logger.error(
                "Exception. userId: %s, locationId %s" % (userId, locationId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(result)


class LocationsPermissions:
    def __init__(self, db):
        self.db = db

    @checkLocationPermissions(Roles.owner)
    def on_post(self, req, resp, userId, locationId):

        try:
            otherUserId = dbinterface.findUserIdByEmail(self.db, req.media["email"])
            if not otherUserId:
                raise ValueError("The email provided doesn't belong to any user.")
            elif otherUserId == userId:
                raise ValueError(
                    "The permissions are granted to another user, please use other user's email"
                )
            if dbinterface.existsShare(self.db, otherUserId, userId, locationId):
                raise ValueError("The location has already been shared to this user")

            result = dbinterface.insertUserLocationShare(
                self.db,
                otherUserId,
                userId,
                locationId,
                req.media["email"],
                req.media["role"],
            )

        except ValueError as e:
            logger.error(
                "The userId: %s has requested to give location permissions to the following email: %s that is not valid"
                % (userId, req.media["email"])
            )
            raise falcon.HTTPBadRequest("Bad Request: Invalid Email", e)
        except:
            logger.error(
                "Exception. userId: %s, locationId %s" % (userId, locationId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(True, result)

    @checkLocationPermissions(Roles.owner)
    def on_get(self, req, resp, userId, locationId):

        try:
            locationPermissions = dbinterface.selectLocationShares(
                self.db, userId, locationId
            )
        except:
            logger.error(
                "Exception. userId: %s, locationId: %s" % (userId, locationId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(True, locationPermissions)


class LocationPermission:
    def __init__(self, db):
        self.db = db

    @checkShareOwner
    def on_put(self, req, resp, userId, shareId):

        try:
            updatedData = {"role": req.media["newRole"]}
            result = dbinterface.updateUserLocationShare(self.db, shareId, updatedData)

        except:
            logger.error("Exception. userId: %s" % (userId), exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(result)

    @checkUser
    def on_delete(self, req, resp, userId, shareId):

        try:
            result = dbinterface.deleteUserLocationShare(self.db, userId, shareId)
        except:
            logger.error("Exception. userId: %s" % (userId), exc_info=True)
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(result)


class LocationRooms:
    def __init__(self, db):
        self.db = db

    @checkLocationPermissions(Roles.editor)
    def on_post(self, req, resp, userId, locationId):

        try:
            roomId = dbinterface.insertRoom(
                self.db, userId, locationId, req.media.get("roomName")
            )

        except:
            logger.error(
                "Exception. userId: %s, locationId %s" % (userId, locationId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(True, roomId)

    @checkLocationPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId):

        try:
            rooms = dbinterface.selectRooms(self.db, userId, locationId)
        except:
            logger.error(
                "Exception. userId: %s, locationId %s" % (userId, locationId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(True, rooms)


class LocationRoom:
    def __init__(self, db):
        self.db = db

    @checkLocationPermissions(Roles.editor)
    def on_put(self, req, resp, userId, locationId, roomId):

        try:
            result = dbinterface.updateRoom(
                self.db, userId, locationId, roomId, req.media
            )

        except:
            logger.error(
                "Exception. userId: %s, locationId %s, roomId: %s"
                % (userId, locationId, roomId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(result)

    @checkLocationPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, roomId):

        try:
            room = dbinterface.selectRoom(self.db, userId, locationId, roomId)
        except:
            logger.error(
                "Exception. userId: %s, locationId %s, roomId: %s"
                % (userId, locationId, roomId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(True, room)

    @checkLocationPermissions(Roles.editor)
    def on_delete(self, req, resp, userId, locationId, roomId):

        try:
            result = dbinterface.deleteRoom(self.db, userId, locationId, roomId)
        except:
            logger.error(
                "Exception. userId: %s, locationId %s, roomId: %s"
                % (userId, locationId, roomId),
                exc_info=True,
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(result)

