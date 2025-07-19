import logging
import logging.config
from datetime import datetime
from zoneinfo import ZoneInfo 

import requests
from docker_secrets import get_docker_secrets

logger = logging.getLogger()


class IotCloudApi:

    iotcloudApiUrl = get_docker_secrets("api_url")
    client_id = get_docker_secrets("api_client_id")
    client_secret = get_docker_secrets("api_client_secret")
    auth_url = get_docker_secrets("auth_url")
    audience = get_docker_secrets("api_audience")

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
            logger.error(
                "authenticate: User could NOT be successfully authenticated.")
            return False

        logger.info("authenticate: User authenticated successfully.")
        return True

    def validateResponse(self, response: requests.Response) -> dict:

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
            return {}

    def get(self, url, auth=False) -> dict:

        headers = self.getAuthHeader() if auth else None

        # First we try to post de data without validating the token,
        # if we get the unauthorized code then we ask for a new token,
        # and if we are not able to get the token after 1 try we abandon
        for numRetries in range(2):
            r = self.session.get(self.iotcloudApiUrl + url,
                                 headers=headers, timeout=10)
            if r.status_code != requests.codes.unauthorized:
                break

            # Get the auth token
            authenticationResult = self.authenticate()
            if numRetries == 1 or not authenticationResult:
                raise Exception("Could not authenticate")
            # Send again the data with the new token
            headers = self.getAuthHeader()

        return self.validateResponse(r)

    def post(self, url, data, auth=False) -> dict:

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
                raise Exception("Could not authenticate")
            # Send again the data with the new token
            headers = self.getAuthHeader()

        return self.validateResponse(r)

    def getSensor(self, locationId, deviceId, sensorId) -> dict:

        sensor = self.get(
            f"locations/{locationId}/devices/{deviceId}/sensors/{sensorId}", auth=True
        )

        return sensor

    def getLocation(self, locationId):

        location = self.get(f"locations/{locationId}/devices", auth=True)

        return location

    def getModulesLocations(self):
        return self.get("locations/modulesEnabled", auth=True)

    def getLocationSunSchedule(self, locationId):

        sunSchedule = self.get(
            f"locations/{locationId}/sunschedule", auth=True)
        return sunSchedule

    def notifyLocationOffline(self, locationId: str, locationName: str, timeZone: str):

        user_local_now = datetime.now(tz=ZoneInfo(timeZone))

        data = {
            "notificationTitle": f"{locationName} Offline",
            "notificationBody": f"{user_local_now.strftime("%d/%m/%Y %H:%M")}: Ningun dispositivo de {locationName} esta conectado al servidor.",
            "notificationTitleArgs": [locationName],
            "notificationBodyArgs": [locationName],
        }

        self.post(
            f"locations/{locationId}/locationnotification", data=data, auth=True)
        
    def notifyLocationBackOnline(self, locationId: str, locationName: str, timeZone: str):

        user_local_now = datetime.now(tz=ZoneInfo(timeZone))

        data = {
            "notificationTitle": f"{locationName} Online",
            "notificationBody": f"{user_local_now.strftime("%d/%m/%Y %H:%M")}: La ubicacion {locationName} vuelve a estar conectada.",
            "notificationTitleArgs": [locationName],
            "notificationBodyArgs": [locationName],
        }

        self.post(
            f"locations/{locationId}/locationnotification", data=data, auth=True)

    def sendLocationNotification(self, locationId: str, sensorId: str, notificationTitle: str, notificationBody: str, timeZone: str):

        user_local_now = datetime.now(tz=ZoneInfo(timeZone))

        data = {
            "notificationTitle": notificationTitle,
            "notificationBody": f"{user_local_now.strftime("%d/%m/%Y %H:%M")}: {notificationBody}",
            "notificationTitleArgs": [],
            "notificationBodyArgs": [],
            "extra": {"sensorId": sensorId}
        }

        self.post(
            f"locations/{locationId}/locationnotification", data=data, auth=True)
