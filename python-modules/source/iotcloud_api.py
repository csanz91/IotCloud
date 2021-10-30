import logging
import logging.config

import requests
from docker_secrets import getDocketSecrets

logger = logging.getLogger()


class IotCloudApi:

    iotcloudApiUrl = getDocketSecrets("api_url")
    client_id = getDocketSecrets("api_client_id")
    client_secret = getDocketSecrets("api_client_secret")
    auth_url = getDocketSecrets("auth_url")
    audience = getDocketSecrets("api_audience")

    accessToken = ""

    def __init__(self):
        self.token = ""
        self.session = requests.session()

    def getAuthHeader(self):
        headers = {"Authorization": "Bearer " + self.accessToken}
        return headers

    def authenticate(self):

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "audience": self.audience,
        }

        result = requests.post(self.auth_url, json=data)

        try:
            decodedResult = result.json()
            self.accessToken = decodedResult["access_token"]
        except (KeyError, TypeError, ValueError):
            logger.error("authenticate: User could NOT be successfully authenticated.")
            return False

        logger.info("authenticate: User authenticated successfully.")
        return True

    def validateResponse(self, response):

        assert response.status_code == 200

        try:
            result = response.json()
        except ValueError:
            logger.warning(
                "validateResponse: the response could not be json decoded. Response: %s"
                % response.text
            )
            raise

        try:
            return result["data"]
        except KeyError:
            return True

    def get(self, url, auth=False):

        headers = self.getAuthHeader() if auth else None

        # First we try to post de data without validating the token,
        # if we get the unauthorized code then we ask for a new token,
        # and if we are not able to get the token after 1 try we abandon
        for numRetries in range(2):
            r = self.session.get(self.iotcloudApiUrl + url, headers=headers, timeout=30)
            if r.status_code != requests.codes.unauthorized:
                break

            # Get the auth token
            authenticationResult = self.authenticate()
            if numRetries == 1 or not authenticationResult:
                return
            # Send again the data with the new token
            headers = self.getAuthHeader()

        return self.validateResponse(r)

    def post(self, url, data, auth=False):

        headers = self.getAuthHeader() if auth else None

        # First we try to post de data without validating the token,
        # if we get the unauthorized code then we ask for a new token,
        # and if we are not able to get the token after 1 try we abandon
        for numRetries in range(2):
            r = self.session.post(
                self.iotcloudApiUrl + url, json=data, headers=headers, timeout=30
            )
            if r.status_code != requests.codes.unauthorized:
                break

            # Get the auth token
            authenticationResult = self.authenticate()
            if numRetries == 1 or not authenticationResult:
                return
            # Send again the data with the new token
            headers = self.getAuthHeader()

        return self.validateResponse(r)

    def getUserSensor(self, userId, locationId, deviceId, sensorId):

        devices = self.get(f"users/{userId}/sensors", auth=True)

        for device in devices:
            if deviceId == device["deviceId"]:
                for sensor in device["sensors"]:
                    if sensor["sensorId"] == sensorId:
                        return sensor
                break

        return {}

    def getSensor(self, locationId, deviceId, sensorId):

        sensor = self.get(
            f"locations/{locationId}/devices/{deviceId}/sensors/{sensorId}", auth=True
        )

        return sensor

    def getLocation(self, locationId):

        location = self.get(f"locations/{locationId}/devices", auth=True)

        return location

    def getLocationSunSchedule(self, locationId):

        sunSchedule = self.get(f"locations/{locationId}/sunschedule", auth=True)
        return sunSchedule

    def notifyLocationOffline(self, locationId):

        data = {
            "notificationTitle": "locationOfflineTitle",
            "notificationBody": "locationOfflineBody",
            "notificationTitleArgs": ["%(locationName)s"],
            "notificationBodyArgs": ["%(locationName)s"],
        }

        self.post(f"locations/{locationId}/locationnotification", data=data, auth=True)
