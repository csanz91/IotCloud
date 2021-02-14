import logging
import json
import time

import falcon

import dbinterface
import influxdb_interface
import api_utils
import inspect
from api_utils import grantLocationOwnerPermissions, Roles, getResponseModel
from mqtt import generateMqttToken, MqttRoles
from datetime import datetime, timedelta
import datetime_utils
import calendar


logger = logging.getLogger(__name__)


class LocationDevices:
    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.editor)
    def on_post(self, req, resp, userId, locationId):

        try:

            deviceId = dbinterface.insertDevice(
                self.db,
                userId,
                locationId,
                req.media.get("deviceVersion"),
                req.media.get("deviceInternalId"),
                [json.loads(sensor) for sensor in req.media.get("sensors")],
                deviceTargetVersion=req.media.get("deviceTargetVersion", None),
                deviceId=req.media.get("deviceId", None),
            )

        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )

            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, deviceId)

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId):

        try:
            devices = dbinterface.selectDevices(self.db, userId, locationId)

        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )
        resp.media = getResponseModel(True, devices)


class Devices:
    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.editor)
    def on_put(self, req, resp, userId, locationId, deviceId):

        try:
            result = dbinterface.updateDevice(
                self.db,
                userId,
                locationId,
                deviceId,
                req.media.get("deviceVersion", None),
                req.media.get("deviceTargetVersion", None),
            )

        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}, deviceId: {deviceId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(result)

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId):

        try:
            device = dbinterface.selectDevice(self.db, userId, locationId, deviceId)
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}, deviceId: {deviceId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, device)

    @grantLocationOwnerPermissions(Roles.editor)
    def on_delete(self, req, resp, userId, locationId, deviceId):

        try:
            result = dbinterface.deleteDevice(self.db, userId, locationId, deviceId)
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}, deviceId: {deviceId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(result)


class Sensors:
    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId, sensorId):

        try:
            sensor = dbinterface.selectSensor(
                self.db, userId, locationId, deviceId, sensorId
            )
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}, deviceId: {deviceId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, sensor)

    @grantLocationOwnerPermissions(Roles.editor)
    def on_put(self, req, resp, userId, locationId, deviceId, sensorId):

        try:
            result = dbinterface.updateSensor(
                self.db,
                userId,
                locationId,
                deviceId,
                sensorId,
                req.media.get("sensorName", None),
                req.media.get("sensorMetadata", None),
                req.media.get("color", None),
                req.media.get("orderIndex", None),
                req.media.get("roomId", None),
            )

        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}, deviceId: {deviceId}, sensorId: {sensorId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(result)


class OrderSensors:
    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.editor)
    def on_post(self, req, resp, userId, locationId):

        try:
            result = dbinterface.orderSensors(
                self.db, userId, locationId, req.media["newSensorsOrder"]
            )

        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}, "
                f"newSensorsOrder: {req.media['newSensorsOrder']}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = api_utils.getResponseModel(result)


class MqttDeviceToken:
    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.editor)
    def on_get(self, req, resp, userId, locationId, deviceId):

        try:
            token = generateMqttToken(
                userId, MqttRoles.device, locationId=locationId, deviceId=deviceId
            )
            assert token
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, token)


class MqttSubdeviceToken:
    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.editor)
    def on_get(self, req, resp, userId, locationId, deviceId):

        subdeviceId = req.get_param("subdeviceId")

        try:
            token = generateMqttToken(
                userId,
                MqttRoles.subdevice,
                locationId=locationId,
                deviceId=deviceId,
                subdeviceId=subdeviceId,
            )
            assert token
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, token)


class LastSeen:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId):

        try:
            lastSeen = influxdb_interface.getDeviceLastTimeSeen(
                self.influxdb, locationId, deviceId
            )
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, lastSeen)


class SensorData:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_post(self, req, resp, userId, locationId, deviceId, sensorId):

        try:
            data = influxdb_interface.getData(
                self.influxdb,
                locationId,
                sensorId,
                req.media["initialTimestamp"],
                req.media["finalTimestamp"],
            )
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, data)


class SensorDataTrend:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId, sensorId):

        finalTimestamp = int(time.time())
        initialTimestamp = finalTimestamp - 3600 * 6

        try:
            data = influxdb_interface.getData(
                self.influxdb,
                locationId,
                sensorId,
                initialTimestamp,
                finalTimestamp,
                maxValues=50,
            )
            data = [float(value["value"]) for value in data]
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, data)


class SensorDataStats:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId, sensorId):

        selectedDatetime = req.get_param_as_datetime("selectedDatetime")
        if not selectedDatetime:
            selectedDatetime = datetime.now()

        timeZoneId = req.get_param("timeZoneId")

        (
            todayLocalMidnightTimestamp,
            todayLocalEndDayTimestamp,
        ) = datetime_utils.getDayTimestamps(selectedDatetime, timeZoneId)
        (
            thisWeekLocalMidnightTimestamp,
            thisWeekLocalEndDayTimestamp,
        ) = datetime_utils.getThisWeekTimestamps(selectedDatetime, timeZoneId)
        (
            thisMonthLocalMidnightTimestamp,
            thisMonthLocalEndDayTimestamp,
        ) = datetime_utils.getThisMonthTimestamps(selectedDatetime, timeZoneId)

        try:
            todayStats = influxdb_interface.getStats(
                self.influxdb,
                locationId,
                sensorId,
                todayLocalMidnightTimestamp,
                todayLocalEndDayTimestamp,
            )
            thisWeekStats = influxdb_interface.getStats(
                self.influxdb,
                locationId,
                sensorId,
                thisWeekLocalMidnightTimestamp,
                thisWeekLocalEndDayTimestamp,
            )
            thisMonthStats = influxdb_interface.getStats(
                self.influxdb,
                locationId,
                sensorId,
                thisMonthLocalMidnightTimestamp,
                thisMonthLocalEndDayTimestamp,
            )
            data = {
                "todayStats": todayStats[0],
                "thisWeekStats": thisWeekStats[0],
                "thisMonthStats": thisMonthStats[0],
            }
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, data)


class SensorStateTime:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId, sensorId):

        datetimeNow = datetime.now()
        includeHeating = req.get_param_as_bool("includeHeating")

        timeZoneId = req.get_param("timeZoneId")

        initialTimestamp = req.get_param_as_int("initialTimestamp")
        finalTimestamp = req.get_param_as_int("finalTimestamp")

        stateTimes = []
        if initialTimestamp and finalTimestamp:
            dataToAdd = {"timestamp": initialTimestamp}
            try:
                stateTime = influxdb_interface.getStateTime(
                    self.influxdb,
                    locationId,
                    deviceId,
                    sensorId,
                    initialTimestamp,
                    finalTimestamp,
                )
                dataToAdd["stateTime"] = stateTime
                if includeHeating:
                    heatingTime = influxdb_interface.getHeatingTime(
                        self.influxdb,
                        locationId,
                        deviceId,
                        sensorId,
                        initialTimestamp,
                        finalTimestamp,
                    )
                    dataToAdd["heatingTime"] = heatingTime
                stateTimes.append(dataToAdd)
            except:
                logger.error(
                    "Exception. userId: %s, locationId %s" % (userId, locationId),
                    exc_info=True,
                )
                raise falcon.HTTPBadRequest(
                    "Bad Request", "The request can not be completed."
                )
        else:
            # Go back 10 days
            for dayIndex in range(10):
                # Get the timestamps from the selected period
                pastDay = datetimeNow - timedelta(days=dayIndex)
                (
                    pastDayLocalMidnightTimestamp,
                    pastDayLocalEndDayTimestamp,
                ) = datetime_utils.getDayTimestamps(pastDay, timeZoneId)

                # If the last state is on and [pastDayLocalEndDayTimestamp] is in the future, we just need
                # to count up to now, otherwise it will count until the end of the current day
                pastDayLocalEndDayTimestamp = min(
                    calendar.timegm(datetimeNow.timetuple()),
                    pastDayLocalEndDayTimestamp,
                )
                try:
                    dataToAdd = {"timestamp": pastDayLocalMidnightTimestamp}
                    stateTime = influxdb_interface.getStateTime(
                        self.influxdb,
                        locationId,
                        deviceId,
                        sensorId,
                        pastDayLocalMidnightTimestamp,
                        pastDayLocalEndDayTimestamp,
                    )
                    dataToAdd["stateTime"] = stateTime
                    if includeHeating:
                        heatingTime = influxdb_interface.getHeatingTime(
                            self.influxdb,
                            locationId,
                            deviceId,
                            sensorId,
                            pastDayLocalMidnightTimestamp,
                            pastDayLocalEndDayTimestamp,
                        )
                        dataToAdd["heatingTime"] = heatingTime

                    stateTimes.append(dataToAdd)
                except:
                    logger.error(
                        "Exception. userId: %s, locationId %s" % (userId, locationId),
                        exc_info=True,
                    )
                    raise falcon.HTTPBadRequest(
                        "Bad Request", "The request can not be completed."
                    )

        resp.media = getResponseModel(True, stateTimes)


class TotalizerStats:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId, sensorId):

        datetimeNow = datetime.utcnow()
        timestampNow = calendar.timegm(datetimeNow.timetuple())
        oneHourAgo = timestampNow - 3600
        oneDayAgo = timestampNow - 3600 * 24

        try:
            currentRate = influxdb_interface.getTotalizerCurrentRate(
                self.influxdb, locationId, sensorId
            )
            try:
                currentRate = currentRate[0]["rate"]
            except (TypeError, KeyError):
                currentRate = 0

            accumulatedLastHour = influxdb_interface.getHourlyAccumulation(
                self.influxdb, locationId, sensorId, oneHourAgo, timestampNow
            )
            try:
                accumulatedLastHour = accumulatedLastHour[0]["value"]
            except (TypeError, KeyError):
                accumulatedLastHour = 0

            accumulatedLastDay = influxdb_interface.getHourlyAccumulation(
                self.influxdb, locationId, sensorId, oneDayAgo, timestampNow
            )
            try:
                accumulatedLastDay = sum(
                    accumulated["value"] or 0.0 for accumulated in accumulatedLastDay
                )
            except (TypeError, KeyError):
                accumulatedLastDay = 0

            trendRate = influxdb_interface.getTotalizerTrendRate(
                self.influxdb, locationId, sensorId
            )
            try:
                trendRate = [float(value["rate"]) for value in trendRate]
            except (TypeError, KeyError):
                trendRate = 0

            data = {
                "currentRate": currentRate,
                "accumulatedLastHour": accumulatedLastHour,
                "accumulatedLastDay": accumulatedLastDay,
                "trendRate": trendRate,
            }
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, data)


class HourlyAccumulation:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_post(self, req, resp, userId, locationId, deviceId, sensorId):

        try:
            data = influxdb_interface.getHourlyAccumulation(
                self.influxdb,
                locationId,
                sensorId,
                req.media["initialTimestamp"],
                req.media["finalTimestamp"],
            )
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, data)


class DeviceIP:
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId):

        try:
            ip = influxdb_interface.getDeviceIP(self.influxdb, locationId, deviceId)
        except:
            logger.error(
                f"Exception. userId: {userId}, locationId: {locationId}",
                exc_info=True,
                extra={"area": "devices"},
            )
            raise falcon.HTTPBadRequest(
                "Bad Request", "The request can not be completed."
            )

        resp.media = getResponseModel(True, ip)
