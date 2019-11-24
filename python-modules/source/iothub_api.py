import logging
import logging.config

import requests
from docker_secrets import getDocketSecrets
from cache_decorator import cache_disk

logger = logging.getLogger()


class IothubApi():

    iothubApiUrl = getDocketSecrets('api_url')
    client_id = getDocketSecrets('api_client_id')
    client_secret = getDocketSecrets('api_client_secret')
    auth_url = getDocketSecrets('auth_url')
    audience = getDocketSecrets('api_audience')

    accessToken = ''

    def __init__(self):
        self.token = ""
        self.session = requests.session()

    def getAuthHeader(self):
        headers = {'Authorization': "Bearer " + self.accessToken}
        return headers

    def authenticate(self):

        data = {'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': "client_credentials",
                "audience": self.audience}

        result = requests.post(self.auth_url, json=data)

        try:
            decodedResult = result.json()
            self.accessToken = decodedResult["access_token"]
        except (KeyError, TypeError, ValueError):
            logger.error('authenticate: User could NOT be successfully authenticated.')
            return False

        logger.info('authenticate: User authenticated successfully.')
        return True

    def validateResponse(self, response):

        assert response.status_code == 200

        try:
            result = response.json()
        except ValueError:
            logger.warning("validateResponse: the response could not be json decoded. Response: %s" % response.text)
            raise

        try:
            return result['data']
        except KeyError:
            return True

    def get(self, url, auth=False):

        headers = None
        if auth:
            headers = self.getAuthHeader()

        # First we try to post de data without validating the token,
        # if we get the unauthorized code then we ask for a new token,
        # and if we are not able to get the token after 1 try we abandon
        for numRetries in range(2):
            r = self.session.get(self.iothubApiUrl+url, headers=headers, timeout=30)
            if r.status_code != requests.codes.unauthorized:
                break

            # Get the auth token
            authenticationResult = self.authenticate()
            if numRetries == 1 or not authenticationResult:
                return
            # Send again the data with the new token
            headers = self.getAuthHeader()

        # Check if the response is well formed
        result = self.validateResponse(r)
        return result

    def post(self, url, data, auth=False):

        headers = None
        if auth:
            headers = self.getAuthHeader()

        # First we try to post de data without validating the token,
        # if we get the unauthorized code then we ask for a new token,
        # and if we are not able to get the token after 1 try we abandon
        for numRetries in range(2):
            r = self.session.post(self.iothubApiUrl+url, json=data, headers=headers, timeout=30)
            if r.status_code != requests.codes.unauthorized:
                break

            # Get the auth token
            authenticationResult = self.authenticate()
            if numRetries == 1 or not authenticationResult:
                return
            # Send again the data with the new token
            headers = self.getAuthHeader()

        # Check if the response is well formed
        result = self.validateResponse(r)
        return result

    def getUserSensor(self, userId, locationId, deviceId, sensorId):

        devices = self.get("users/{userId}/sensors".format(userId=userId), auth=True)

        for device in devices:
            if deviceId == device["deviceId"]:
                for sensor in device["sensors"]:
                    if sensor["sensorId"] == sensorId:
                        return sensor
                break

        return {}

    def getSensor(self, locationId, deviceId, sensorId):

        sensor = self.get("locations/{locationId}/devices/{deviceId}/sensors/{sensorId}".format(locationId=locationId,
                                                                                                deviceId=deviceId,
                                                                                                sensorId=sensorId,
                                                                                                ), auth=True)

        return sensor

    @cache_disk(seconds=3600 * 8)
    def getLocationSunSchedule(self, locationId):

        sunSchedule = self.get("locations/{locationId}/sunschedule".format(locationId=locationId), auth=True)
        return sunSchedule

    def notifyLocationOffline(self, locationId):

        data = {
            "notificationTitle": "locationOfflineTitle",
            "notificationBody": "locationOfflineBody",
            "notificationTitleArgs": ["%(locationName)s"],
            "notificationBodyArgs": ["%(locationName)s"]
        }

        self.post("locations/{locationId}/locationnotification".format(locationId=locationId), data=data, auth=True)
