import logging

import requests


logger = logging.getLogger(__name__)

weatherServiceUrl = "http://weather:5003/api"


def getTimeZone(postalCode):

    r = requests.get(f"{weatherServiceUrl}/postalcode/{postalCode}/timezone")
    result = r.json()
    return result["data"]