import logging
import logging.config
import time
from threading import Thread, Lock
import typing

import paho.mqtt.client as mqtt
from docker_secrets import getDocketSecrets

from location import Location
from iotcloud_api import IotCloudApi
from utils import MqttActions, retryFunc

# Logging setup
logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler(
    "../logs/modules.log", mode="a", maxBytes=1024 * 1024 * 10, backupCount=2
)
formatter = logging.Formatter(
    "%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s"
)
logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

####################################
# Global variables
####################################
locations: typing.Dict[str, Location] = {}
locationsLock = Lock()


@retryFunc
def addLocation(locationId: str, mqttclient: mqtt.Client, api: IotCloudApi):
    locationData = api.getLocation(locationId)
    with locationsLock:
        location = Location(locationId, locationData, mqttclient, api)
        location.subscribe(mqttclient)
        locations[locationId] = location


@retryFunc
def updateLocation(locationId: str, mqttclient: mqtt.Client, api: IotCloudApi):
    locationData = api.getLocation(locationId)
    if locationId in locations:
        with locationsLock:
            locations[locationId].setLocationData(locationData, mqttclient)


def onLocationUpdated(mqttclient: mqtt.Client, userdata, message):
    locationId = message.topic.split("/")[1]
    action = message.payload.decode("utf-8")
    api: IotCloudApi = userdata["api"]
    logger.info(f"Received action: {action} from the location: {locationId}")

    if action == MqttActions.ADDED:
        Thread(
            target=addLocation, args=(locationId, mqttclient, api), daemon=True
        ).start()
    elif action == MqttActions.UPDATED:
        Thread(
            target=updateLocation, args=(locationId, mqttclient, api), daemon=True
        ).start()
    elif action == MqttActions.DELETED:
        if locationId in locations:
            with locationsLock:
                locations[locationId].unsubscribe(mqttclient)
                del locations[locationId]


def onConnect(mqttclient, userdata, flags, rc):
    logger.info("Connected to the MQTT broker")
    mqttclient.subscribe(updatedLocationTopic)
    with locationsLock:
        for location in locations.values():
            location.subscribe(mqttclient)


logger.info("Starting...")

# IotHub api setup
api = IotCloudApi()

# Setup MQTT client
mqttclient = mqtt.Client(userdata={"api": api})
token = getDocketSecrets("mqtt_token")
mqttclient.username_pw_set(token, "_")
updatedLocationTopic = "v1/+/updatedLocation"

mqttclient.message_callback_add(updatedLocationTopic, onLocationUpdated)
mqttclient.on_connect = onConnect

# Get the locations
modulesLocations = api.getModulesLocations()
for locationData in modulesLocations:
    locationId = locationData["_id"]
    locations[locationId] = Location(locationId, locationData, mqttclient, api)

# Connect
mqttclient.connect("mosquitto")
mqttclient.loop_start()

try:
    while True:
        with locationsLock:
            for location in locations.values():
                location.run()

        time.sleep(1.0)
finally:
    mqttclient.loop_stop()
    logger.info("Exiting...")
