import api
import dbinterface

validUserData1 = {"email": "user@test.comxyz",
                  "name": "user1",
                  "lastName": "lastName1",
                  "password": "a12345678A",
                  "wantUpdates": True,
                  "gdprAcceptance": True,
                  "language": "es"}

sensorsData = [{"sensorName": "sensor1",
                "sensorType": "analog",
                "sensorMetadata": {"engUnit": "C"}},

               {"sensorName": "sensor2",
                "sensorType": "digital", },

               {"sensorName": "sensor3",
                "sensorType": "analog",
                "sensorMetadata": {"description": "This is the sensor number three"}}]


devicesData = [{"deviceInternalId": "231431-asdb",
                "deviceTargetVersion": "0.1",
                "deviceVersion": "0.1",
                "sensors": [sensorsData[0]]},

               {"deviceInternalId": "231432-ccasd",
                "deviceTargetVersion": "0.1",
                "deviceVersion": "0.1",
                "sensors": [sensorsData[0], sensorsData[1]],
                "utcDeviceFirstSeenTimestamp": 1538578822},
                
                {"deviceInternalId": "231432-ccasd",
                "deviceTargetVersion": "0.3",
                "deviceVersion": "0.3",
                "sensors": [sensorsData[1], sensorsData[2]]}]


userId = 'auth0|5bacd279f3f3cd1b1803b61f'
name = validUserData1['name']
lastName = validUserData1['lastName']
email = validUserData1['email']
password = validUserData1['password']
wantUpdates = validUserData1['wantUpdates']
gdprAcceptance = validUserData1['gdprAcceptance']
language = validUserData1['language']
locationId = "5bd0d1c49303fc7ebc35c143"

# Register user in the database
#response = dbinterface.insertUser(api.db, name, lastName, email, wantUpdates,
#                                  gdprAcceptance, language, userId=userId)


for device in devicesData:
    deviceVersion = device['deviceVersion']
    deviceInternalId = device['deviceInternalId']
    deviceTargetVersion = device['deviceTargetVersion']
    sensors = device['sensors']
    utcDeviceFirstSeenTimestamp =device.get('utcDeviceFirstSeenTimestamp', None)

    response= dbinterface.insertDevice(api.db, userId, locationId,
                             deviceVersion,
                             deviceInternalId,
                             sensors,
                             deviceTargetVersion=deviceTargetVersion,
                             utcDeviceFirstSeenTimestamp=utcDeviceFirstSeenTimestamp)
    print response
