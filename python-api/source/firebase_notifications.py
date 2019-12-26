import logging
import json

import firebase_admin
from firebase_admin import messaging
from docker_secrets import getDocketSecrets

logger = logging.getLogger(__name__)

firebaseCredentials = {
    "type": getDocketSecrets("type"),
    "project_id": getDocketSecrets("project_id"),
    "private_key_id": getDocketSecrets("private_key_id"),
    "private_key": getDocketSecrets("private_key"),
    "client_email": getDocketSecrets("client_email"),
    "client_id": getDocketSecrets("client_id"),
    "auth_uri": getDocketSecrets("auth_uri"),
    "token_uri": getDocketSecrets("token_uri"),
    "auth_provider_x509_cert_url": getDocketSecrets("auth_provider_x509_cert_url"),
    "client_x509_cert_url": getDocketSecrets("client_x509_cert_url")
}

cred = firebase_admin.credentials.Certificate(firebaseCredentials)
firebase_admin.initialize_app(cred)


def sendLocationNotification(locationId,
                             notificationTitle,
                             notificationBody,
                             userToken,
                             notificationTitleArgs=None,
                             notificationBodyArgs=None):

    logger.info("sending notification to: %s" % userToken)

    message = firebase_admin.messaging.Message(
        android=firebase_admin.messaging.AndroidConfig(
            priority='normal',
            notification=messaging.AndroidNotification(
                title_loc_key=notificationTitle,
                body_loc_key=notificationBody,
                title_loc_args=notificationTitleArgs,
                body_loc_args=notificationBodyArgs,
                icon='ic_stat_name',
                color='#3671a8',
            ),
        ),
        data={
            "title_loc_key": notificationTitle,
            "body_loc_key": notificationBody,
            "title_loc_args": json.dumps(notificationTitleArgs),
            "body_loc_args": json.dumps(notificationBodyArgs)
        },
        token=userToken
    )
    try:
        firebase_admin.messaging.send(message)
    except firebase_admin.exceptions.FirebaseError:
        logger.error("Cannot send the notification for the userToken: %s" % userToken, exc_info=True)
    except:
        logger.error("Cannot send the notification for the userToken: %s" % userToken, exc_info=True)
