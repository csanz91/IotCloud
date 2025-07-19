import logging
import json

import firebase_admin
from firebase_admin import messaging
from docker_secrets import get_docker_secrets

logger = logging.getLogger(__name__)

firebaseCredentials = {
    "type": get_docker_secrets("type"),
    "project_id": get_docker_secrets("project_id"),
    "private_key_id": get_docker_secrets("private_key_id"),
    "private_key": get_docker_secrets("private_key"),
    "client_email": get_docker_secrets("client_email"),
    "client_id": get_docker_secrets("client_id"),
    "auth_uri": get_docker_secrets("auth_uri"),
    "token_uri": get_docker_secrets("token_uri"),
    "auth_provider_x509_cert_url": get_docker_secrets("auth_provider_x509_cert_url"),
    "client_x509_cert_url": get_docker_secrets("client_x509_cert_url"),
}

cred = firebase_admin.credentials.Certificate(firebaseCredentials)
firebase_admin.initialize_app(cred)


def sendLocationNotification(
    locationId,
    notificationTitle,
    notificationBody,
    userToken,
    notificationTitleArgs=None,
    notificationBodyArgs=None,
):
    logger.info("sending notification to: %s" % userToken)

    message = firebase_admin.messaging.Message(
        android=firebase_admin.messaging.AndroidConfig(
            priority="normal",
            notification=messaging.AndroidNotification(
                title=notificationTitle,
                body=notificationBody,
                title_loc_key=notificationTitle,
                body_loc_key=notificationBody,
                title_loc_args=notificationTitleArgs,
                body_loc_args=notificationBodyArgs,
                icon="ic_stat_name",
                color="#3671a8",
            ),
        ),
        data={
            "title_loc_key": notificationTitle,
            "body_loc_key": notificationBody,
            "title_loc_args": json.dumps(notificationTitleArgs),
            "body_loc_args": json.dumps(notificationBodyArgs),
        },
        token=userToken,
    )
    try:
        firebase_admin.messaging.send(message)
    except firebase_admin.exceptions.FirebaseError:
        logger.error(
            f"Cannot send the notification for the userToken: {userToken}",
            exc_info=True,
        )
    except:
        logger.error(
            f"Cannot send the notification for the userToken: {userToken}",
            exc_info=True,
        )
