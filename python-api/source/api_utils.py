import logging

import falcon

import dbinterface
import api_utils

logger = logging.getLogger(__name__)


def getResponseModel(result, data=None):
    response = {"result": result}
    if data is not None:
        response["data"] = data

    return response


class Roles:
    viewer = 100
    editor = 200
    owner = 300
    admin = 999
    superadmin = 9999

    def __iter__(self):
        for attrName, attrValue in Roles.__dict__.items():
            if attrName[:2] != "__":
                yield attrValue

    @staticmethod
    def validateRole(role):
        return int(role) in Roles()


def checkLocationPermissions(requiredRole):
    def decorator(func):
        def func_wrapper(self, *args, **kwargs):
            req = args[0]
            try:
                locationId = kwargs["locationId"]
                userId = kwargs["userId"]
                db = self.db
            except KeyError:
                errorMsg = (
                    "Programing error, the args available for this "
                    "function are not valid for this decorator"
                )
                logger.error(errorMsg)
                raise SyntaxError(errorMsg)

            userIdReq = req.context["auth"]["subject"]
            if userIdReq == userId:
                grantedRole = dbinterface.selectUserLocationRole(db, userId, locationId)
                if grantedRole >= requiredRole:
                    return func(self, *args, **kwargs)

            logger.warning(
                f"Unauthorized access attemp to the resource: {req.url}"
                f" from the userId: {userId} with IP: {req.remote_addr}",
                extra={"area": "security"},
            )
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="The user is not authorized to retrive this data.",
            )

        return func_wrapper

    return decorator


def grantLocationOwnerPermissions(requiredRole):
    def decorator(func):
        def func_wrapper(self, *args, **kwargs):
            req = args[0]
            try:
                locationId = kwargs["locationId"]
                userId = kwargs["userId"]
                db = self.db
            except KeyError:
                errorMsg = (
                    "Programing error, the args available for this "
                    "function are not valid for this decorator"
                )
                logger.error(errorMsg)
                raise SyntaxError(errorMsg)

            userIdReq = req.context["auth"]["subject"]
            if userIdReq == userId:
                grantedRole = dbinterface.selectUserLocationRole(db, userId, locationId)
                if grantedRole >= requiredRole:
                    if grantedRole != api_utils.Roles.owner:
                        locationShare = dbinterface.selectUserLocationShare(
                            db, userId, locationId
                        )
                        kwargs["userId"] = locationShare["ownerUserId"]

                    return func(self, *args, **kwargs)

            logger.warning(
                f"Unauthorized access attemp to the resource: {req.url}"
                f" from the userId: {userId} with IP: {req.remote_addr}",
                extra={"area": "security"},
            )
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="The user is not authorized to retrive this data.",
            )

        return func_wrapper

    return decorator


def checkUser(func):
    def func_wrapper(*args, **kwargs):
        req = args[1]
        userId = kwargs["userId"]

        try:
            userIdReq = req.context["auth"]["subject"]
            assert userIdReq == userId
        except:
            logger.warning(
                f"Unauthorized access attemp to the user: {userId} resource: {req.url}"
                f" from the userId: {userIdReq} with IP: {req.remote_addr}",
                extra={"area": "security"},
            )
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="The user is not authorized to retrive this data.",
            )
        return func(*args, **kwargs)

    return func_wrapper


def checkShareOwner(func):
    def func_wrapper(self, *args, **kwargs):
        req = args[0]
        try:
            shareId = kwargs["shareId"]
            userId = kwargs["userId"]
            db = self.db
        except KeyError:
            errorMsg = (
                "Programing error, the args available for this "
                "function are not valid for this decorator"
            )
            logger.error(errorMsg)
            raise SyntaxError(errorMsg)

        userIdReq = req.context["auth"]["subject"]
        if userIdReq == userId:
            locationShare = dbinterface.selectShare(db, shareId)
            if locationShare and locationShare["ownerUserId"] == userId:
                return func(self, *args, **kwargs)

            logger.warning(
                f"Unauthorized access attemp to the resource: {req.url}"
                f" from the userId: {userId} with IP: {req.remote_addr}",
                extra={"area": "security"},
            )

        raise falcon.HTTPUnauthorized(
            "Unauthorized", "The user is not authorized to retrive this data."
        )

    return func_wrapper


def m2mValidation(func):
    def func_wrapper(*args, **kwargs):
        req = args[1]

        try:
            assert req.context["auth"]["scope"] == "read:devices"
        except:
            logger.warning(
                f"Unauthorized access attemp to the resource: {req.url}"
                f"from the IP: {req.remote_addr}",
                extra={"area": "security"},
            )
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="The user is not authorized to retrive this data.",
            )
        return func(*args, **kwargs)

    return func_wrapper

def getToken(req):
    try:
        headerParts = req.auth.split()
    except:
        logger.error("Exception. params: %s" % (req.headers), exc_info=True)
        raise falcon.HTTPBadRequest("Bad Request", "The request can not be completed.")

    if len(headerParts) == 2 and headerParts[0] == "Bearer":
        token = headerParts[1]
    else:
        logger.error("Exception. params: %s" % (req.headers), exc_info=True)
        raise falcon.HTTPBadRequest(
            "Bad Request", "Invalid Authorization header format."
        )

    return token