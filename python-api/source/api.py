import logging
import os

logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler(
    "../logs/server.log", mode="a", maxBytes=1024 * 1024 * 10, backupCount=2
)
formatter = logging.Formatter(
    "%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s"
)
logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

import falcon
import falcon_auth0
from pymongo import MongoClient
import paho.mqtt.client as mqtt

from docker_secrets import getDocketSecrets
import influx
from user_management import Login, RecoverPassword, UserManagement
from auth0_api import Auth0Api
from locations import (
    UserLocations,
    Locations,
    LocationsPermissions,
    LocationPermission,
    LocationRooms,
    LocationRoom,
)
from devices import (
    LocationDevices,
    Devices,
    Sensors,
    OrderSensors,
    MqttDeviceToken,
    MqttSubdeviceToken,
    SensorData,
    SensorDataTrend,
    SensorDataStats,
    SensorStateTime,
    SensorActionData,
    LastSeen,
    TotalizerStats,
    HourlyAccumulation,
    DeviceIP,
)
from users import (
    Users,
    ValidateLocationPermissions,
    ChangePassword,
    MqttUserToken,
    FirebaseUserToken,
)
from m2m import (
    UserSensors,
    FindSensor,
    LocationSunSchedule,
    SendNotification,
    M2MSensorData,
    M2MUserTags,
    M2MLocationDevices,
    M2MSensorActionData,
    M2MLocationActionData,
    M2MLocationDevicesStatusStats,
    M2MLocationDeviceStatus,
    M2MModulesLocations,
)
from mqtt import MqttAuth, MqttAcl, MqttSuperUser
from weather_api import Weather, SunSchedule
from bitcoin.bitcoin_api import BitcoinCurrent, BitcoinHistorical, BitcoinPrice

##############################################
# Configuration
##############################################


cfg = {
    "alg": ["RS256"],
    "audience": getDocketSecrets("auth0_audience"),
    "domain": getDocketSecrets("auth0_full_domain"),
    "jwks_uri": getDocketSecrets("auth0_jwks_uri"),
}

claims = {
    "email_verified": "verified",
    "email": "email",
    "clientID": "id",
    "updated_at": "updated",
    "name": "name",
    "picture": "avatar",
    "user_id": "user_id",
    "nickname": "profile_name",
    "identities": "profiles",
    "created_at": "created",
    "scope": "scope",
    "iss": "issuer",
    "sub": "subject",
    "aud": "audience",
    "iat": "issued",
    "exp": "expires",
    "gty": "grant_type",
    "at_hash": "hash",
    "nonce": "its_a_secret_to_everyone",
}


##############################################
# Data Connection
##############################################
client = MongoClient(os.environ["MONGODB_HOST"])
db = client.data
influx_client = influx.InfluxDBClient(
    database=os.environ["INFLUXDB_DB"], host=os.environ["INFLUXDB_HOST"]
)

##############################################
# Auth Server Connection
##############################################
auth0 = Auth0Api()


##############################################
# MQTT Server Connection
##############################################
def onConnect(self, mosq, obj, rc):
    logger.info("MQTT Connected",)


mqttclient = mqtt.Client()
token = getDocketSecrets("mqtt_token")
mqttclient.username_pw_set(token, "_")
mqttclient.on_connect = onConnect

# Connect
mqttclient.connect("mosquitto")
mqttclient.loop_start()

##############################################
# Api instance
##############################################
middleware = falcon_auth0.Auth0Middleware(cfg, claims)
app = falcon.App(middleware=[middleware])
app.req_options.auto_parse_form_urlencoded = True

##############################################
# Routes
##############################################
app.add_route("/api/v1/login", Login(auth0, middleware))
app.add_route("/api/v1/recoverpassword", RecoverPassword(auth0))
app.add_route("/api/v1/user", UserManagement(db, auth0))

app.add_route("/api/v1/users/{userId}", Users(db, auth0))
app.add_route("/api/v1/users/{userId}/changepassword", ChangePassword(auth0))
app.add_route(
    "/api/v1/users/{userId}/permissionvalidation", ValidateLocationPermissions(db)
)
app.add_route("/api/v1/users/{userId}/mqttauth", MqttUserToken())
app.add_route("/api/v1/users/{userId}/locations", UserLocations(db, mqttclient))
app.add_route("/api/v1/users/{userId}/weather", Weather())
app.add_route("/api/v1/users/{userId}/sunschedule", SunSchedule())
app.add_route("/api/v1/users/{userId}/sensors", UserSensors(db))
app.add_route("/api/v1/users/{userId}/permissions/{shareId}", LocationPermission(db))
app.add_route("/api/v1/users/{userId}/bitcoin/current", BitcoinCurrent())
app.add_route("/api/v1/users/{userId}/bitcoin/historical", BitcoinHistorical())
app.add_route("/api/v1/users/{userId}/bitcoin", BitcoinPrice())
app.add_route("/api/v1/users/{userId}/firebasetoken", FirebaseUserToken(db))
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}", Locations(db, mqttclient)
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices",
    LocationDevices(db, mqttclient),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/ordersensors", OrderSensors(db, mqttclient)
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/permissions",
    LocationsPermissions(db),
)
app.add_route("/api/v1/users/{userId}/locations/{locationId}/rooms", LocationRooms(db))
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/rooms/{roomId}", LocationRoom(db)
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}",
    Devices(db, mqttclient),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/mqttauth",
    MqttDeviceToken(db),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/subdevice/mqttauth",
    MqttSubdeviceToken(db),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/lastseen",
    LastSeen(influx_client, db),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/deviceip",
    DeviceIP(influx_client, db),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/sensors/{sensorId}",
    Sensors(db, mqttclient),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/sensorsdata/{sensorId}",
    SensorData(influx_client, db),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/sensorsdatatrend/{sensorId}",
    SensorDataTrend(influx_client, db),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/sensorsdatastats/{sensorId}",
    SensorDataStats(influx_client, db),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/sensorsstatetime/{sensorId}",
    SensorStateTime(influx_client, db),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/sensoractiondata/{sensorId}",
    SensorActionData(influx_client, db),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/totalizerstats/{sensorId}",
    TotalizerStats(influx_client, db),
)
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/hourlyaccumulation/{sensorId}",
    HourlyAccumulation(influx_client, db),
)

app.add_route("/api/v1/locations/{locationId}/sunschedule", LocationSunSchedule(db))
app.add_route(
    "/api/v1/locations/{locationId}/devices/{deviceId}/sensors/{sensorId}",
    FindSensor(db),
)
app.add_route(
    "/api/v1/locations/{locationId}/locationnotification", SendNotification(db)
)
app.add_route("/api/v1/locations/{locationId}/devices", M2MLocationDevices(db))
app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/m2msensorsdata/{sensorId}",
    M2MSensorData(influx_client, db),
)
app.add_route("/api/v1/users/{userId}/locations/{locationId}/tags", M2MUserTags(db))

app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/m2msensoractiondata/{sensorId}",
    M2MSensorActionData(influx_client, db),
)

app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/m2mlocationactiondata",
    M2MLocationActionData(influx_client, db),
)

app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/m2mdevicesstatusstats",
    M2MLocationDevicesStatusStats(influx_client, db),
)

app.add_route(
    "/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}/m2mstatus",
    M2MLocationDeviceStatus(influx_client, db),
)
app.add_route("/api/v1/locations/modulesEnabled", M2MModulesLocations(db))

app.add_route("/api/v1/mqtt/auth", MqttAuth())
app.add_route("/api/v1/mqtt/superuser", MqttSuperUser())
app.add_route("/api/v1/mqtt/acl", MqttAcl(db))
