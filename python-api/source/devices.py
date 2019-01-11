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
import datetime
import datetime_utils


logger = logging.getLogger(__name__)

class LocationDevices():

    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.editor)
    def on_post(self, req, resp, userId, locationId):

        try:
            
            deviceId = dbinterface.insertDevice(self.db, 
                                                    userId,
                                                    locationId,
                                                    req.media.get('deviceVersion'),
                                                    req.media.get('deviceInternalId'),
                                                    [json.loads(sensor) for sensor in req.media.get('sensors')],
                                                    deviceTargetVersion = req.media.get('deviceTargetVersion', None)
                                                    )

        except:
            logger.error("Exception. userId: %s, locationId %s" % (userId, locationId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )

        resp.media = getResponseModel(True, deviceId)


    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId):

        try:
            devices = dbinterface.selectDevices(self.db, userId, locationId)
            
        except:
            logger.error("Exception. userId: %s, locationId %s" % (userId, locationId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            ) 
        resp.media = getResponseModel(True, devices)

class Devices():

    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.editor)
    def on_put(self, req, resp, userId, locationId, deviceId):


        try:
            result = dbinterface.updateDevice(self.db, 
                                                userId,
                                                locationId,
                                                deviceId,
                                                req.media.get('deviceVersion', None), 
                                                req.media.get('deviceTargetVersion', None))
            
        except:
            logger.error("Exception. userId: %s, locationId %s, deviceId: %s" % (userId, locationId, deviceId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )

        resp.media = api_utils.getResponseModel(result)

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId):
        
        try:
            device = dbinterface.selectDevice(self.db, userId, locationId, deviceId)
        except:
            logger.error("Exception. userId: %s, locationId %s, deviceId: %s" % (userId, locationId, deviceId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            ) 

        resp.media = getResponseModel(True, device)

    @grantLocationOwnerPermissions(Roles.editor)
    def on_delete(self, req, resp, userId, locationId, deviceId):

        try:
            result = dbinterface.deleteDevice(self.db, userId, locationId, deviceId)
        except:
            logger.error("Exception. userId: %s, locationId %s, deviceId: %s" % (userId, locationId, deviceId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            ) 

        resp.media = api_utils.getResponseModel(result)

class Sensors():

    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId, sensorId):
        
        try:
            sensor = dbinterface.selectSensor(self.db, userId, locationId, deviceId, sensorId)
        except:
            logger.error("Exception. userId: %s, locationId %s, deviceId: %s" % (userId, locationId, deviceId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            ) 

        resp.media = getResponseModel(True, sensor)

    @grantLocationOwnerPermissions(Roles.editor)
    def on_put(self, req, resp, userId, locationId, deviceId, sensorId):


        try:
            result = dbinterface.updateSensor(self.db, 
                                                userId,
                                                locationId,
                                                deviceId,
                                                sensorId,
                                                req.media.get('sensorName', None), 
                                                req.media.get('sensorMetadata', None), 
                                                req.media.get('color', None),
                                                req.media.get('orderIndex', None))
            
        except:
            logger.error("Exception. userId: %s, locationId %s, deviceId: %s, sensorId: %s" % (userId, locationId, deviceId, sensorId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )

        resp.media = api_utils.getResponseModel(result)

class OrderSensors():

    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.editor)
    def on_post(self, req, resp, userId, locationId):


        try:
            result = dbinterface.orderSensors(self.db, 
                                                userId,
                                                locationId,
                                                req.media['newSensorsOrder'])
            
        except:
            logger.error("Exception. userId: %s, locationId %s, newSensorsOrder: %s" % (userId, locationId, req.media['newSensorsOrder']), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )

        resp.media = api_utils.getResponseModel(result)

class MqttDeviceToken():

    def __init__(self, db):
        self.db = db

    @grantLocationOwnerPermissions(Roles.editor)
    def on_get(self, req, resp, userId, locationId, deviceId):

        try:
            token = generateMqttToken(userId, MqttRoles.device, locationId=locationId, deviceId=deviceId)
            assert token
        except:
            logger.error("Exception. userId: %s, locationId %s" % (userId, locationId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )

        resp.media = getResponseModel(True, token)


class SensorData():
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_post(self, req, resp, userId, locationId, deviceId, sensorId):

        try:
            data = influxdb_interface.getData(self.influxdb, locationId, sensorId, req.media['initialTimestamp'], req.media['finalTimestamp'])
        except:
            logger.error("Exception. userId: %s, locationId %s" % (userId, locationId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )

        resp.media = getResponseModel(True, data)


class SensorDataTrend():
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId, sensorId):

        finalTimestamp = int(time.time())
        initialTimestamp = finalTimestamp - 3600*6

        logger.info("SensorDataTrend: %s" % sensorId)


        try:
            data = influxdb_interface.getData(self.influxdb, locationId, sensorId, initialTimestamp, finalTimestamp, maxValues=50)
            data = [float(value['value']) for value in data]
        except:
            logger.error("Exception. userId: %s, locationId %s" % (userId, locationId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )

        resp.media = getResponseModel(True, data)


class SensorDataStats():
    def __init__(self, influxdb, mongodb):
        self.influxdb = influxdb
        self.db = mongodb

    @grantLocationOwnerPermissions(Roles.viewer)
    def on_get(self, req, resp, userId, locationId, deviceId, sensorId):

        datetimeNow = datetime.datetime.now()
        todayLocalMidnightTimestamp, todayLocalEndDayTimestamp = datetime_utils.getDayTimestamps(datetimeNow)
        thisWeekLocalMidnightTimestamp, thisWeekLocalEndDayTimestamp = datetime_utils.getThisWeekTimestamps(datetimeNow)
        thisMonthLocalMidnightTimestamp, thisMonthLocalEndDayTimestamp = datetime_utils.getThisMonthTimestamps(datetimeNow)

        try:
            todayStats = influxdb_interface.getStats(self.influxdb, locationId, sensorId, todayLocalMidnightTimestamp, todayLocalEndDayTimestamp)
            thisWeekStats = influxdb_interface.getStats(self.influxdb, locationId, sensorId, thisWeekLocalMidnightTimestamp, thisWeekLocalEndDayTimestamp)
            thisMonthStats = influxdb_interface.getStats(self.influxdb, locationId, sensorId, thisMonthLocalMidnightTimestamp, thisMonthLocalEndDayTimestamp)
            data = {"todayStats": todayStats[0], "thisWeekStats": thisWeekStats[0], "thisMonthStats": thisMonthStats[0]}
        except:
            logger.error("Exception. userId: %s, locationId %s" % (userId, locationId), exc_info=True)
            raise falcon.HTTPBadRequest(
                'Bad Request',
                'The request can not be completed.'
            )

        resp.media = getResponseModel(True, data)
