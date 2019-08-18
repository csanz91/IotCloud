from pymongo import MongoClient
from pymongo.results import InsertOneResult, DeleteResult
from bson.objectid import ObjectId
import time
import inspect
import logging
from collections import OrderedDict
import json
from bson import json_util
import random
import copy

import api_utils

from dbcache import DBCache
import request_home_resync

logger = logging.getLogger(__name__)

cache = DBCache()

#####################################################
## Auxiliar Functions
#####################################################

def joinDicts(d1, d2):
    d = d1.copy()  
    d.update(d2)   
    return d

def checkArgs(*argchecks):      
    def checkAllArgs(func):  
        def func_wrapper(*args, **kwargs):
            dArgs = joinDicts(dict(zip(inspect.getargspec(func).args, args)), kwargs)
            for arg in argchecks:
                if not dArgs[arg]:
                    logger.warning("The argument: '%s' is not valid, is empty" % (arg))
                    raise ValueError("Invalid parameters.")
            return func(*args, **kwargs)
        return func_wrapper
    return checkAllArgs


def validateDbResult(result):
    try:
        assert(result.acknowledged)
        if type(result) is DeleteResult:
            assert(result.deleted_count==1)
        elif type(result) is InsertOneResult:
            pass
        else:
            assert(result.modified_count==1)
    except AssertionError:
        logger.error("The database operation could not be completed successfully")
        raise

#####################################################
## User Operations
#####################################################

@checkArgs("db", "name", "lastName", "email", "language")
def insertUser(db, name, lastName, email, wantUpdates, 
                gdprAcceptance, language, utcAccountInitialTimestamp=None,
                userId=None):
    
    if not utcAccountInitialTimestamp:
        utcAccountInitialTimestamp = int(time.time())

    if not userId:
        userId = str(ObjectId())

    userData = {
        "_id": userId,
        "name": name,
        "lastName": lastName,
        "email": email,
        "wantUpdates": wantUpdates,
        "gdprAcceptance": gdprAcceptance,
        "language": language,
        "utcAccountInitialTimestamp": utcAccountInitialTimestamp,
        "utcAccountUpdatedTimestamp": utcAccountInitialTimestamp,
        "locations": [],
        "otherUsersLocations": []
    }

    result = db.usersData.insert_one(userData)
    validateDbResult(result)

    # Save the user data in the cache
    cache.update(str(userId), userData)

    return userId

@checkArgs("db", "userId")
def updateUser(db, userId, updatedData):

    # These are the only fields allowed to be updated
    allowedFieldsToUpdate = ["name", "lastName", "wantUpdates", "language"]

    # Select only the fields that can be modified
    updatedData = {field: updatedData[field] for field in allowedFieldsToUpdate if field in updatedData and updatedData[field] is not ""}
    if not updatedData:
        return True

    updatedData['utcAccountUpdatedTimestamp'] = int(time.time())

    result = db.usersData.update_one(
        {"_id": userId},
        {"$set": updatedData}
    )
    validateDbResult(result)

    # Clear the cache as the data is not longer updated
    cache.clearCache(userId)

    return True 

@checkArgs("db", "userId")
def selectUser(db, userId):

    # Try to get the data first from the cache,
    # if it is not found look into the database
    try:
        userData = cache[userId]
    except KeyError:
        userData = db.usersData.find_one(
            {"_id": userId}
        )
        # Save the user data in the cache
        cache.update(userId, userData)

    return userData

@checkArgs("db", "userId")
def selectUserInheritedData(db, userId):

    # Try to get the data first from the cache,
    # if it is not found look into the database
    try:
        userData = cache[userId]
    except KeyError:
        userData = db.usersData.find_one(
            {"_id": userId}
        )
        # Save the user data in the cache
        cache.update(userId, userData)

    returnData = copy.deepcopy(userData)
    returnData['locations'] += list(getInheritedLocations(db, userId))
        
    return returnData

@checkArgs("db", "userId")
def deleteUser(db, userId):

    # Delete all the shares related to the user
    db.locationsAuthorizations.delete_many(
        {"$or": [{"sharedToUserId": userId}, {"ownerUserId": userId}]}
    )
        
    result = db.usersData.delete_one(
        {"_id": userId}
    )
    validateDbResult(result)

    # Save the user data in the cache
    cache.clearCache(userId)

    return True

@checkArgs("db", "email")
def findUserIdByEmail(db, email):
    userId = db.usersData.find_one(
            {"email": email},
            {"_id": True}
        )

    return userId["_id"]


#####################################################
## Users Locations Permissions Operations
#####################################################

@checkArgs("db", "shareId")
def selectShare(db, shareId):
    locationShare = db.locationsAuthorizations.find_one(
        {'_id': shareId}
    )
    return locationShare

@checkArgs("db", "userId")
def selectLocationsShares(db, userId):
    otherUsersLocations = db.locationsAuthorizations.find(
        {'sharedToUserId': userId,
         'validated': True}
    )
    return list(otherUsersLocations)

@checkArgs("db", "sharedToUserId", "ownerUserId", "locationId")
def existsShare(db, sharedToUserId, ownerUserId, locationId):
    locationShare = db.locationsAuthorizations.find_one(
        {'sharedToUserId': sharedToUserId,
        'ownerUserId': ownerUserId,
         'locationId': locationId}
    )
    return bool(locationShare)

@checkArgs("db", "locationId")
def getLocationUsers(db, locationId):
    logger.info(locationId)
    usersIds = db.locationsAuthorizations.find(
        {"locationId": locationId,
         "validated": True},
        {"ownerUserId": True,
        "sharedToUserId": True,
        "_id": False}
    )
    return list(usersIds)

@checkArgs("db", "userId")
def getPendingValidateShares(db, userId):
    pendingShares = db.locationsAuthorizations.find(
        {'sharedToUserId': userId,
        'validated': False}
    )
    return list(pendingShares)

@checkArgs("db", "userId", "locationId")
def selectUserLocationShare(db, userId, locationId):
    
    locationsShares = selectLocationsShares(db, userId)
    for locationShare in locationsShares:
        sharedLocationId = locationShare['locationId']
        if locationId!=sharedLocationId:
            continue

        return locationShare

@checkArgs("db", "userId", "locationId")
def selectUserLocationRole(db, userId, locationId):
    
    # Check if the user is the owner of the location
    if any(locationId==location["_id"] for location in selectLocations(db, userId)):
        return api_utils.Roles.owner

    locationShare = selectUserLocationShare(db, userId, locationId)
    if not locationShare:
        return
    return locationShare['role']
    

@checkArgs("db", "shareId", "updatedData")
def updateUserLocationShare(db, shareId, updatedData):

    allowedFieldsToUpdate = ["role", "validated"] + individualLocationFields
    dataToUpdate = getDataToUpdate(updatedData, allowedFieldsToUpdate)
    if not dataToUpdate:
        return True

    dataToUpdate['utcLocationUpdatedTimestamp'] = int(time.time())

    result = db.locationsAuthorizations.update_one(
        {"_id": shareId},
        {"$set": dataToUpdate}
    )
    validateDbResult(result)

    return True

@checkArgs("db", "sharedToUserId", "ownerUserId", "locationId", "email", "role")
def insertUserLocationShare(db, sharedToUserId, ownerUserId, locationId, email, role):

    # Check the integrety of the role
    assert(api_utils.Roles.validateRole(role))

    location = selectLocation(db, ownerUserId, locationId)

    _id = str(ObjectId())
    shareData = {"_id": _id,
                "sharedToUserId": sharedToUserId, 
                "ownerUserId": ownerUserId,
                "locationId": locationId,
                "email": email,
                "validated": False,
                "role": role}

    # Copy the individual fields to the share
    for field in individualLocationFields:
        shareData[field]=location[field] 

    result = db.locationsAuthorizations.insert_one(shareData)
    validateDbResult(result)

    return _id

@checkArgs("db", "userId", "shareId")
def deleteUserLocationShare(db, userId, shareId):
    result = db.locationsAuthorizations.delete_one(
        {"_id": shareId,
        "$or": [{"sharedToUserId": userId}, {"ownerUserId": userId}]}
    )
    validateDbResult(result)

    return True


#####################################################
## Locations Operations
#####################################################

@checkArgs("db", "userId", "locationName", "postalCode", "city")
def insertLocation(db, userId, locationName, postalCode, city, utcLocationInitialTimestamp=None, color=None, thirdPartiesVisible=True):

    if not utcLocationInitialTimestamp:
        utcLocationInitialTimestamp = int(time.time())

    if not color:
        color = "ff%06x" % random.randint(0, 0xFFFFFF)

    _id = str(ObjectId())
    result = db.usersData.update_one(
        {"_id": userId},
        {"$push":   {  "locations" :
                        {
                        "_id": _id,
                        "locationName": locationName,
                        "postalCode": postalCode,
                        "city": city,
                        "utcLocationInitialTimestamp": utcLocationInitialTimestamp,
                        "utcLocationUpdatedTimestamp": utcLocationInitialTimestamp,
                        "devices": [],
                        "usersPermissions": [],
                        "color": color,
                        "role": api_utils.Roles.owner,
                        "rooms": [],
                        "thirdPartiesVisible": False
                        }
                    }
        }
    )
    validateDbResult(result)

    cache.clearCache(userId)
    return _id

def getDataToUpdate(updatedData, allowedFieldsToUpdate):
    updatedData = {field: updatedData[field] for field in allowedFieldsToUpdate if field in updatedData}
    return updatedData

individualLocationFields = ["locationName", "color", "thirdPartiesVisible"]
sharedLocationFields = ["postalCode", "city"]

@checkArgs("db", "userId", "locationId")
def updateLocation(db, userId, locationId, updatedData):

    ourLocationRole = selectUserLocationRole(db, userId, locationId)
    if not ourLocationRole:
        return False

    # If we are updating a location which we are not the owners
    # we can modify either individual or shared fields
    locationShare = selectUserLocationShare(db, userId, locationId)
    if locationShare:
        ownerUserId = locationShare['ownerUserId']
        shareId = locationShare['_id']
        # Edit the individual fields of the location
        dataToUpdate = getDataToUpdate(updatedData, individualLocationFields)
        if dataToUpdate:
            updateUserLocationShare(db, shareId, dataToUpdate)

        # With a role lower than editor we can only edit the individual fields
        if ourLocationRole < api_utils.Roles.editor:
            return True

        # Now we are going to edit the location of the other user
        userId = ownerUserId
        allowedFieldsToUpdate = sharedLocationFields
    else:
        # We are the owners of the location, we can edit all the fields
        allowedFieldsToUpdate = individualLocationFields + sharedLocationFields

    dataToUpdate = getDataToUpdate(updatedData, allowedFieldsToUpdate)
    if not dataToUpdate:
        return True

    dataToUpdate['utcLocationUpdatedTimestamp'] = int(time.time())

    result = db.usersData.update_one(
        {"_id": userId, "locations._id": locationId},
        {"$set": {"locations.$.%s" % field: value for field, value in dataToUpdate.items()}}
    )
    validateDbResult(result)

    # Clear the cache as the data is not longer updated
    cache.clearCache(userId)

    if "thirdPartiesVisible" in dataToUpdate:
        # Resync the Google home devices
        request_home_resync.resync(db, userId, locationId)

    return True

# Yield to optimize when selecting only one location
def yieldLocations(db, userId, includeInherited=False):
    try:
        userData = cache[userId]
    except KeyError:
        userData = selectUser(db, userId)

    for location in userData['locations']:
        yield location

    if includeInherited:
        inheritedLocations = getInheritedLocations(db, userId)
        for inheritedLocation in inheritedLocations:
            yield inheritedLocation


def getInheritedLocations(db, userId):
    locationsShares = selectLocationsShares(db, userId) 
    for locationShare in locationsShares:
        ownerUserId = locationShare['ownerUserId']
        locationId = locationShare['locationId']
        role = locationShare['role']

        # Combine the individual and shared fields for the location
        otherUserLocation = selectLocation(db, ownerUserId, locationId)
        otherUserLocation['role'] = role

        for field in individualLocationFields:
            otherUserLocation[field] = locationShare[field]

        yield otherUserLocation

@checkArgs("db", "userId")
def selectLocations(db, userId, includeInherited=False):
    locations = list(yieldLocations(db, userId, includeInherited=includeInherited))
    return locations


@checkArgs("db", "userId", "locationId")
def selectLocation(db, userId, locationId, includeInherited=False):
    locations = yieldLocations(db, userId, includeInherited=includeInherited)
    for location in locations:
        if location["_id"]==locationId:
            return copy.deepcopy(location)

    return None


@checkArgs("db", "userId", "locationId")
def deleteLocation(db, userId, locationId):

    locationShare = selectUserLocationShare(db, userId, locationId)
    # If the location is shared
    if locationShare:
        shareId = locationShare['_id']
        deleteUserLocationShare(db, userId, shareId)
    # If we are the owners of the location
    else:
        db.locationsAuthorizations.delete_many(
            {"locationId": locationId}
        )

        result = db.usersData.update_one(
            {"_id": userId,
            "locations._id": locationId},
            {"$pull": {"locations": {"_id": locationId}}}
        )
        validateDbResult(result)

        # Clear the cache as the data is not longer updated
        cache.clearCache(userId)

    # Resync the Google home devices
    request_home_resync.resync(db, userId, locationId)

    return True

@checkArgs("db", "userId", "locationId", "roomName")
def insertRoom(db, userId, locationId, roomName):

    ourLocationRole = selectUserLocationRole(db, userId, locationId)
    if not ourLocationRole:
        return False

    locationShare = selectUserLocationShare(db, userId, locationId)
    if locationShare:

        if ourLocationRole < api_utils.Roles.editor:
            return False

        ownerUserId = locationShare['ownerUserId']
        # Now we are going to edit the location of the other user
        userId = ownerUserId

    _id = str(ObjectId())
    result = db.usersData.update_one(
        {"_id": userId,
        "locations._id": locationId},
        {"$push":   {  "locations.$.rooms" :
                        {
                        "roomId": _id,
                        "roomName": roomName,
                        }
                    }
        }
    )
    validateDbResult(result)

    cache.clearCache(userId)
    return _id

@checkArgs("db", "userId", "locationId", "roomId", "updatedData")
def updateRoom(db, userId, locationId, roomId, updatedData):

    allowedFieldsToUpdate = ["roomName"]
    dataToUpdate = getDataToUpdate(updatedData, allowedFieldsToUpdate)

    result = db.usersData.update_one(
        {"_id": userId},
        {"$set": {"locations.$[i].rooms.$[j].%s" % field: value for field, value in dataToUpdate.items()}},
        array_filters= [
            {"i._id": locationId},
            {"j.roomId": roomId}
        ]
    )
    validateDbResult(result)

    # Clear the cache as the data is not longer updated
    cache.clearCache(userId)
    return True

@checkArgs("db", "userId", "locationId", "roomId")
def deleteRoom(db, userId, locationId, roomId):

    result = db.usersData.update_many(
        {"_id": userId, "locations._id": locationId},
        {"$pull": {"locations.$.rooms": {"roomId": roomId}}}
    )
    validateDbResult(result)

    # Clear the cache as the data is not longer updated
    cache.clearCache(userId)

    return True

@checkArgs("db", "userId", "locationId")
def selectRooms(db, userId, locationId):
    location = selectLocation(db, userId, locationId)
    try:
        rooms = location['rooms']
    except KeyError:
        rooms = []
    return rooms

@checkArgs("db", "userId", "locationId", "roomId")
def selectRoom(db, userId, locationId, roomId):

    rooms = selectRooms(db, userId, locationId)
    for room in rooms:
        if room['roomId']==roomId:
            return room

    return {}

#####################################################
## Location Permissions Operations
#####################################################

@checkArgs("db", "userId", "locationId")
def selectLocationShares(db, userId, locationId):

    locationShares = db.locationsAuthorizations.find(
        {'ownerUserId': userId,
        'locationId': locationId}
    )
    return list(locationShares)


@checkArgs("db", "shareId")
def validateLocationPermissions(db, shareId):

    updatedData = {'validated': True}
    result = updateUserLocationShare(db, shareId, updatedData)

    # Resync the Google home devices for the user
    if result:
        share = selectShare(db, shareId)
        request_home_resync.resync(db, share['ownerUserId'], share['locationId'])

    return result

#####################################################
## Devices Operations
#####################################################

@checkArgs("db", "userId", "locationId", "deviceVersion", "deviceInternalId", "receivedSensors")
def insertDevice(db, 
                userId, 
                locationId, 
                deviceVersion, 
                deviceInternalId,
                receivedSensors,
                deviceTargetVersion=None,
                utcDeviceFirstSeenTimestamp=None,
                deviceId=None):

    if not utcDeviceFirstSeenTimestamp:
        utcDeviceFirstSeenTimestamp = int(time.time())

    sensorsOrder = getSensorsOrder(db, userId, locationId)
        
    sensors = []
    for sensor in receivedSensors:
        # Calculate the order index of the sensor
        try:
            orderIndex = sensor['orderIndex']
            assert orderIndex
            assert orderIndex not in sensorsOrder
        except (KeyError, AssertionError):
            orderIndex = max(sensorsOrder or [-1])+1
            sensorsOrder.append(orderIndex)

        sensors.append({'sensorId': sensor['sensorId'],
                        'sensorName': sensor['sensorName'],
                        'sensorType': sensor['sensorType'],
                        'sensorMetadata': sensor.get('sensorMetadata', None),
                        'color': sensor.get('color', "ff%06x" % random.randint(0, 0xFFFFFF)),
                        'orderIndex': orderIndex,
                        'roomId': sensor['roomId'],
                        }
        )

    # If the device existed in this location, remove it
    result = db.usersData.update_many(
        {"_id": userId, "locations._id": locationId},
        {"$pull": {"locations.$.devices": {"deviceInternalId": deviceInternalId}}}
    )

    _id = deviceId or str(ObjectId())
    result = db.usersData.update_one(
        {"_id": userId,
        "locations._id": locationId},
        {"$push":   {  "locations.$.devices" :
                        {
                        "deviceId": _id,
                        "deviceVersion": deviceVersion,
                        "deviceTargetVersion": deviceTargetVersion,
                        "deviceInternalId": deviceInternalId,
                        "utcDeviceFirstSeenTimestamp": utcDeviceFirstSeenTimestamp,
                        "utcDeviceUpdatedTimestamp": utcDeviceFirstSeenTimestamp,
                        "utcDeviceLastSeenTimestamp": utcDeviceFirstSeenTimestamp,
                        "sensors": sensors
                        }
                    }
        }
    )
    validateDbResult(result)

    # Clear the cache as the data is not longer updated
    cache.clearCache(userId)

    # Resync the Google home devices
    request_home_resync.resync(db, userId, locationId)

    return _id

@checkArgs("db", "userId", "locationId", "deviceId")
def updateDevice(db, 
                userId, 
                locationId,
                deviceId,
                deviceVersion=None, 
                deviceTargetVersion=None):

    args = locals()
    fieldsToUpdate = ["deviceVersion",
                      "deviceTargetVersion"]

    updatedData = {field: args[field] for field in fieldsToUpdate if field in args and args[field]}
    if not updatedData:
        return True
        
    updatedData['utcDeviceUpdatedTimestamp'] = int(time.time())

    result = db.usersData.update_one(
        {"_id": userId},
        {"$set": {"locations.$[i].devices.$[j].%s" % field: value for field, value in updatedData.items()}},
        array_filters= [
            {"i._id": locationId},
            {"j.deviceId": deviceId}
        ]
    )
    validateDbResult(result)

    # Clear the cache as the data is not longer updated
    cache.clearCache(userId)
    return True

@checkArgs("db", "userId", "locationId", "deviceId", "sensorId")
def updateSensor(db, 
                userId, 
                locationId,
                deviceId,
                sensorId,
                sensorName=None, 
                sensorMetadata=None,
                color=None,
                orderIndex=None,
                roomId=None):

    if orderIndex:
        sensorsOrder = getSensorsOrder(db, userId, locationId)
        if orderIndex in sensorsOrder:
            raise ValueError("There is already a sensor in this order: %s" % orderIndex)

    args = locals()
    fieldsToUpdate = [  "sensorName",
                        "sensorMetadata",
                        "color",
                        "orderIndex",
                        "roomId"]

    updatedData = {field: args[field] for field in fieldsToUpdate if field in args and args[field]}
    if not updatedData:
        return True
        
    updatedData['utcDeviceUpdatedTimestamp'] = int(time.time())

    result = db.usersData.update_one(
        {"_id": userId},
        {"$set": {"locations.$[i].devices.$[j].sensors.$[k].%s" % field: value for field, value in updatedData.items()}},
        array_filters= [
            {"i._id": locationId},
            {"j.deviceId": deviceId},
            {"k.sensorId": sensorId}
        ]
    )
    validateDbResult(result)

    # Clear the cache as the data is not longer updated
    cache.clearCache(userId)
    return True

@checkArgs("db", "userId", "locationId", "deviceId")
def deleteDevice(db, userId, locationId, deviceId):

    result = db.usersData.update_many(
        {"_id": userId, "locations._id": locationId},
        {"$pull": {"locations.$.devices": {"deviceId": deviceId}}}
    )
    validateDbResult(result)

    # Clear the cache as the data is not longer updated
    cache.clearCache(userId)

    # Resync the Google home devices
    request_home_resync.resync(db, userId, locationId)

    return True


@checkArgs("db", "userId", "locationId")
def selectDevices(db, userId, locationId):
    location = selectLocation(db, userId, locationId)
    return location['devices']

@checkArgs("db", "userId", "locationId", "deviceId")
def selectDevice(db, userId, locationId, deviceId):

    devices = selectDevices(db, userId, locationId)
    for device in devices:
        if device['deviceId']==deviceId:
            return device

    return {}

@checkArgs("db", "userId", "locationId", "deviceId", "sensorId")
def selectSensor(db, userId, locationId, deviceId, sensorId):

    devices = selectDevices(db, userId, locationId)
    for device in devices:
        if device['deviceId']==deviceId:
            for sensor in device['sensors']:
                if sensor['sensorId']==sensorId:
                    return sensor

    return {}

@checkArgs("db", "userId", "locationId")
def getSensorsOrder(db, userId, locationId):

    sensorsOrder = []
    devices = selectDevices(db, userId, locationId)
    for device in devices:
        for sensor in device['sensors']:
            try:
                sensorsOrder.append(sensor['orderIndex'])
            except KeyError:
                sensorsOrder.append(0)

    return sensorsOrder

@checkArgs("db", "userId", "locationId", "newSensorsOrder")
def orderSensors(db, userId, locationId, newSensorsOrder):

    for sensorOrder in newSensorsOrder:
        deviceId = sensorOrder['deviceId']
        sensorId = sensorOrder['sensorId']
        orderIndex = sensorOrder['orderIndex']

        updatedData = {'utcDeviceUpdatedTimestamp': int(time.time()), 'orderIndex': orderIndex}
        result = db.usersData.update_one(
            {"_id": userId},
            {"$set": {"locations.$[i].devices.$[j].sensors.$[k].%s" % field: value for field, value in updatedData.items()}},
            array_filters= [
                {"i._id": locationId},
                {"j.deviceId": deviceId},
                {"k.sensorId": sensorId}
            ]
        )
        validateDbResult(result)

    # Clear the cache as the data is not longer updated
    cache.clearCache(userId)
    return True

@checkArgs("db", "userId")
def selectUserSensors(db, userId):

    devices = []
    user = selectUserInheritedData(db, userId)
    for location in user["locations"]:
        # Only return the selected locations
        try:
            assert location['thirdPartiesVisible']
        except (KeyError, AssertionError):
            continue

        rooms = {room["roomId"]: room["roomName"] for room in location["rooms"]}
        for device in location["devices"]:
            device['locationId'] = location['_id']
            # Add the name of the room
            for sensor in device["sensors"]:
                try:
                    sensor["room"] = rooms[sensor["roomId"]]
                except KeyError:
                    pass
            devices.append(device)
    return devices

@checkArgs("db", "locationId")
def findLocation(db, locationId):

    userData = db.usersData.find_one(
                {"locations._id": locationId}
            )

    return userData["locations"][0]

@checkArgs("db", "locationId", "deviceId", "sensorId")
def findSensor(db, locationId, deviceId, sensorId):

    location = findLocation(db, locationId)
            
    for device in location["devices"]:
        if device['deviceId']==deviceId:
            for sensor in device['sensors']:
                if sensor['sensorId']==sensorId:
                    return sensor

    return {}