import logging
import requests
import threading

from docker_secrets import getDocketSecrets
import dbinterface

logger = logging.getLogger(__name__)

googleHomegraphKey = getDocketSecrets("google_homegraph_key")


def resync(db, userId, locationId):
    locationUsers = dbinterface.getLocationUsers(db, locationId)
    if not locationUsers:
        threading.Thread(target=requestResync, args=(userId,)).start()
        return

    ownerUserId = None
    for share in locationUsers:
        threading.Thread(target=requestResync, args=(share["sharedToUserId"],)).start()
        ownerUserId = share["ownerUserId"]
    threading.Thread(target=requestResync, args=(ownerUserId,)).start()


def requestResync(agentUserId):
    logger.info("Requesting resync for the userId: %s" % agentUserId)
    url = (
        "https://homegraph.googleapis.com/v1/devices:requestSync?key=%s"
        % googleHomegraphKey
    )
    try:
        result = requests.post(url, json={"agentUserId": agentUserId})
    except:
        logger.error(
            "The resync requests has failed. Exception: ",
            exc_info=True,
            extra={"area": "google_home"},
        )
        return

    if result.status_code != 200:
        logger.error(
            f"The resync requests has failed. Status code: {result.status_code}, response: {result.text}",
            extra={"area": "google_home"},
        )
