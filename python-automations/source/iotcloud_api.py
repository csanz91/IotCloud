import logging

import requests
from docker_secrets import get_docker_secrets

logger = logging.getLogger(__name__)

# Constants
MAX_AUTH_RETRIES = 2
REQUEST_TIMEOUT = 10


class AuthenticationError(Exception):
    """Raised when authentication fails"""

    pass


class ApiResponseError(Exception):
    """Raised when API response is invalid"""

    pass


class IotCloudApi:
    def __init__(self):
        # Instance variables instead of class variables for thread safety
        self.iot_cloud_api_url = get_docker_secrets("api_url")
        self.client_id = get_docker_secrets("api_client_id")
        self.client_secret = get_docker_secrets("api_client_secret")
        self.auth_url = get_docker_secrets("auth_url")
        self.audience = get_docker_secrets("api_audience")

        self.access_token = ""
        self.session = requests.Session()

    def get_auth_header(self) -> dict:
        headers = {"Authorization": "Bearer " + self.access_token}
        return headers

    def authenticate(self) -> bool:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "audience": self.audience,
        }

        try:
            result = requests.post(self.auth_url, json=data, timeout=REQUEST_TIMEOUT)
            result.raise_for_status()
        except requests.RequestException as e:
            logger.error("authenticate: Failed to make authentication request: %s", e)
            return False

        try:
            decoded_result = result.json()
            self.access_token = decoded_result["access_token"]
        except (KeyError, TypeError, ValueError) as e:
            logger.error("authenticate: Could not parse authentication response: %s", e)
            return False

        logger.info("authenticate: User authenticated successfully.")
        return True

    def validate_response(self, response: requests.Response) -> dict:
        if response.status_code != 200:
            raise ApiResponseError(f"HTTP {response.status_code}: {response.text}")

        try:
            result = response.json()
        except ValueError as e:
            logger.warning(
                "validate_response: the response could not be json decoded. Response: %s",
                response.text,
            )
            raise ApiResponseError(f"Invalid JSON response: {e}") from e

        try:
            return result["data"]
        except KeyError:
            return {}

    def get(self, url: str, auth: bool = False) -> dict:
        headers = self.get_auth_header() if auth else None

        # First we try to get the data without validating the token,
        # if we get the unauthorized code then we ask for a new token,
        # and if we are not able to get the token after retries we abandon
        response = None
        for num_retries in range(MAX_AUTH_RETRIES):
            try:
                response = self.session.get(
                    self.iot_cloud_api_url + url,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                if response.status_code != requests.codes.unauthorized:
                    break
            except requests.RequestException as e:
                logger.error("get: Request failed", exc_info=True)
                if num_retries == MAX_AUTH_RETRIES - 1:
                    raise AuthenticationError(
                        f"Request failed after {MAX_AUTH_RETRIES} retries"
                    ) from e
                continue

            # Get the auth token
            authentication_result = self.authenticate()
            if num_retries == MAX_AUTH_RETRIES - 1 or not authentication_result:
                raise AuthenticationError("Could not authenticate after retries")
            # Send again the data with the new token
            headers = self.get_auth_header()

        if response is None:
            raise AuthenticationError("No response received")

        return self.validate_response(response)

    def get_location_sun_schedule(self, location_id: str) -> dict:
        logger.info(
            f"get_location_sun_schedule: Retrieving sun schedule for location: {location_id}"
        )
        sun_schedule = self.get(f"locations/{location_id}/sunschedule", auth=True)
        return sun_schedule
