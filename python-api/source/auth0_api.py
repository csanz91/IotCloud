import logging

from auth0.v3.authentication import GetToken
from auth0.v3.authentication.database import Database
from auth0.v3.management import Auth0
from auth0.v3 import exceptions
from auth0.v3.management import Users
from docker_secrets import getDocketSecrets

logger = logging.getLogger(__name__)


def autoAuthenticate(method):
    """ Catch an unauthorized exception and try to get a new token once.
    """

    def wrapper(*args, **kwargs):
        self = args[0]
        for i in range(2):
            try:
                return method(*args, **kwargs)
            except exceptions.Auth0Error as e:
                # 401(Unauthorized) code and first time.
                if e.status_code == 401 and i == 0:
                    logger.info("Getting new token...",)
                    self.initAuth0()
                    continue
                raise

    return wrapper


class Auth0Api:
    domain = getDocketSecrets("auth0_domain")
    non_interactive_client_id = getDocketSecrets("auth0_non_interactive_client_id")
    application_client_id = getDocketSecrets("auth0_application_client_id")
    non_interactive_client_secret = getDocketSecrets(
        "auth0_non_interactive_client_secret"
    )
    interactive_client_secret = getDocketSecrets("auth0_interactive_client_secret")
    audience = getDocketSecrets("auth0_audience")
    connection = "Username-Password-Authentication"

    def __init__(self):

        self.initAuth0()
        if not self.token:
            raise ValueError("Could not get the auth token.")

    def getToken(self):
        token = self.tokenManager.client_credentials(
            self.non_interactive_client_id,
            self.non_interactive_client_secret,
            "https://{}/api/v2/".format(self.domain),
        )
        mgmt_api_token = token["access_token"]
        self.token = mgmt_api_token

    def initAuth0(self):
        self.tokenManager = GetToken(self.domain)
        self.databaseManager = Database(self.domain)
        self.getToken()
        self.auth0 = Auth0(self.domain, self.token)

    @autoAuthenticate
    def addUser(self, username, name, password, verifyEmail=False):
        userData = {
            "connection": "Username-Password-Authentication",
            "email": username,
            "name": name,
            "password": password,
            "verify_email": verifyEmail,
        }

        result = self.auth0.users.create(userData)

        try:
            userId = result["user_id"]
        except (KeyError, TypeError):
            logger.error(
                f"It was not possible to add the user with id: {userId}.",
                exc_info=True,
                extra={"area": "users"},
            )
            return
        logger.info(f"User added with id: {userId}",)
        return userId

    @autoAuthenticate
    def deleteUser(self, userId):
        logger.info(f"Deleted user with id: {userId}")
        return self.auth0.users.delete(userId)

    @autoAuthenticate
    def updateUser(self, userId, updatedData):
        """
        {
            "blocked": false,
            "email_verified": false,
            "email": "john.doe@gmail.com",
            "verify_email": false,
            "phone_number": "+199999999999999",
            "phone_verified": false,
            "verify_phone_number": false,
            "password": "secret",
            "user_metadata": {},
            "app_metadata": {},
            "connection": "Initial-Connection",
            "username": "johndoe",
            "client_id": "DaM8bokEXBWrTUFCiJjWn50jei6ardyX"
        }
        """

        result = self.auth0.users.update(userId, updatedData)

        try:
            assert result["user_id"]
        except (KeyError, TypeError, AssertionError):
            logger.error(
                "It was not possible to update the user with id: %s." % userId,
                exc_info=True,
                extra={"area": "users"},
            )
            return

        logger.info("Updated user with id: %s" % userId)
        return result

    @autoAuthenticate
    def getUser(self, userId):
        userData = self.auth0.users.get(userId)
        return userData

    def login(self, username, password):

        token = self.tokenManager.login(
            self.application_client_id,
            self.interactive_client_secret,
            username,
            password,
            "",
            "",
            self.audience,
            "password",
        )

        auth_api_token = token["access_token"]
        logger.info(f"Loging from user: {username}")
        return auth_api_token

    def recoverPassword(self, username):
        result = self.databaseManager.change_password(
            self.application_client_id, username, self.connection
        )

        logger.info(f"User: {username} requests a new password")
        return result

    def changePassword(self, userId, password):
        result = self.auth0.users.update(userId, {"password": password})
        logger.info(f"User: {userId} requests to change the password")
        return result
