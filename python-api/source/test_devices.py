# -*- coding: utf-8 -*-

import api
import json

from falcon import testing
import pytest
import api_utils
import dbinterface

##############################################
# Auxiliar functions
##############################################

def validateResponse(response):
    assert(response.status_code == 200)
    jsonResponse = response.json
    assert(jsonResponse['result'])

    try:
        return jsonResponse['data']
    except KeyError:
        return None


def setAuthHeaders(token):
    headers = {"Authorization": "Bearer %s" % token}
    return headers


def tryFunction(func, expectedResult):
    if expectedResult:
        func()
    else:
        with pytest.raises(Exception):
            func()

##############################################
# Mocked objects
##############################################


class State():
    token = ""
    userData = {}

    def getOtherUserId(self, userId):
        for otherUserId in self.userData:
            if userId != otherUserId:
                return otherUserId


##############################################
# Sample data
##############################################
validUserData1 = {"email": "user@test.comxyz",
                  "name": "user1",
                  "lastName": "lastName1",
                  "password": "a12345678A",
                  "wantUpdates": True,
                  "gdprAcceptance": True,
                  "language": "es"}


validUserData2 = {"email": "user2@test.comxyz",
                  "name": "user2",
                  "lastName": "lastName2",
                  "password": "a12345678A",
                  "wantUpdates": True,
                  "gdprAcceptance": True,
                  "language": "es"}


locationsData = [{"locationName": "locationA1",
                  "postalCode": "1111",
                  "city": "AAA222"},

                 {"locationName": "locationA2",
                  "postalCode": "2222",
                  "city": "AAA222"},

                 {"locationName": "locationB1",
                  "postalCode": "3333",
                  "city": "BBB222"},

                 {"locationName": "locationB2",
                  "postalCode": "4444",
                  "city": "BBB222"}]


sensorsData = [json.dumps({"sensorName": "sensor1",
                "sensorType": "analog",
                "sensorId": "sensorId1",
                "sensorMetadata": {"engUnit": "C"}}),

               json.dumps({"sensorName": "sensor2",
               "sensorId": "sensorId2",
                "sensorType": "digital", }),

               json.dumps({"sensorName": "sensor3",
                "sensorType": "analog",
                "sensorId": "sensorId3",
                "sensorMetadata": {"description": "This is the sensor number three"}})]


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

##############################################
# Function tests
##############################################
@pytest.fixture()
def client():
    return testing.TestClient(api.app)


@pytest.fixture(scope='session')
def state():
    state = State()
    return state


@pytest.mark.parametrize("data", [
    (validUserData1),
    (validUserData2)
])
def test_userFlowRegister(client, data, state):

    response = client.simulate_post('/api/v1/user', json=data)
    userId = validateResponse(response)
    assert userId

    state.userData[userId] = {"locations": {}, "data": data}


def test_userFlowLogin(client, state):

    for userId, data in state.userData.items():
        data = {'email': data['data']['email'],
                'password': data['data']['password']}
        response = client.simulate_post('/api/v1/login', json=data)
        loginData = validateResponse(response)
        assert(userId == loginData['userId'])
        state.userData[userId]["token"] = loginData['token']


def test_userFlowGet(client, state):

    for userId, data in state.userData.items():
        # Get the data from the actual user
        headers = setAuthHeaders(state.userData[userId]['token'])
        response = client.simulate_get(
            '/api/v1/users/{userId}'.format(userId=userId), headers=headers)
        responseData = validateResponse(response)
        assert(responseData['lastName'] == data['data']['lastName'])

        # Get the data from the other user (This should fail)
        otherUserId = state.getOtherUserId(userId)
        headers = setAuthHeaders(state.userData[userId]['token'])
        with pytest.raises(Exception):
            response = client.simulate_get(
                '/api/v1/users/{userId}'.format(userId=otherUserId), headers=headers)
            validateResponse(response)


def test_addLocations(client, state):

    for i, (userId, userData) in enumerate(state.userData.items()):
        headers = setAuthHeaders(userData['token'])
        for locationIdx in xrange(2):
            locationData = locationsData[2*i+locationIdx]
            response = client.simulate_post(
                '/api/v1/users/{userId}/locations'.format(userId=userId), headers=headers, json=locationData)
            locationId = validateResponse(response)
            assert(locationId)
            state.userData[userId]["locations"][locationId] = []


def test_addDevices(client, state):

    for devicesToAdd, (userId, userData) in enumerate(state.userData.items(), 1):
        headers = setAuthHeaders(userData['token'])
        otherUserId = state.getOtherUserId(userId)

        locationId = userData['locations'].keys()[0]
        for _ in xrange(devicesToAdd):
            data = devicesData.pop()
            response = client.simulate_post('/api/v1/users/{userId}/locations/{locationId}/devices'.format(
                userId=userId, locationId=locationId), headers=headers, json=data)
            deviceId = validateResponse(response)
            userData['locations'][locationId].append(deviceId)

            # Try to add the device to other user (This must fail)
            # WARNING: In python2 the dict order is deterministic, if we use other python version than Python v2.7, v3.1 - v3.5 this will fail for sure
            otherUserLocationId = state.userData[otherUserId]['locations'].keys()[0]
            with pytest.raises(Exception):
                response = client.simulate_post('/api/v1/users/{userId}/locations/{locationId}/devices'.format(
                    userId=userId, locationId=otherUserLocationId), headers=headers, json=data)
                validateResponse(response)

            with pytest.raises(Exception):
                response = client.simulate_post('/api/v1/users/{userId}/locations/{locationId}/devices'.format(
                    userId=otherUserId, locationId=otherUserLocationId), headers=headers, json=data)
                validateResponse(response)


def test_checkInsertedDevices(client, state):
    for userId, userData in state.userData.items():
        headers = setAuthHeaders(state.userData[userId]['token'])
        otherUserId = state.getOtherUserId(userId)
        # Check all the devices
        for locationId, devicesList in userData['locations'].items():
            response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}/devices'.format(
                userId=userId, locationId=locationId), headers=headers)
            devices = validateResponse(response)
            assert(len(devices) == len(devicesList))

            # Try to get the other user devices (This must fail)
            otherUserLocationId = state.userData[otherUserId]['locations'].keys()[0]
            with pytest.raises(Exception):
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}/devices'.format(
                    userId=otherUserId, locationId=otherUserLocationId), headers=headers)
                devices = validateResponse(response)
                assert(devices)
            with pytest.raises(Exception):
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}/devices'.format(
                    userId=userId, locationId=otherUserLocationId), headers=headers)
                devices = validateResponse(response)
                assert(devices)

            # Get every device individually
            for deviceId in devicesList:
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}'.format(
                    userId=userId, locationId=locationId, deviceId=deviceId), headers=headers)
                device = validateResponse(response)
                assert(device['deviceId'] == deviceId)


def test_updateDevices(client, state):

    for devicesToAdd, (userId, userData) in enumerate(state.userData.items(), 1):
        headers = setAuthHeaders(userData['token'])
        otherUserId = state.getOtherUserId(userId)

        locationId = userData['locations'].keys()[0]
        for i in xrange(devicesToAdd):
            deviceId = userData['locations'][locationId][i]
            data = {'deviceVersion': deviceId+userId}
            response = client.simulate_put('/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}'.format(
                userId=userId, locationId=locationId, deviceId=deviceId), headers=headers, json=data)
            validateResponse(response)

            # Try to update the device to other user (These all must fail)
            otherUserLocationId = state.userData[otherUserId]['locations'].keys()[0]
            with pytest.raises(Exception):
                response = client.simulate_put('/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}'.format(
                    userId=userId, locationId=otherUserLocationId, deviceId=deviceId), headers=headers, json=data)
                validateResponse(response)
            with pytest.raises(Exception):
                response = client.simulate_put('/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}'.format(
                    userId=otherUserId, locationId=otherUserLocationId, deviceId=deviceId), headers=headers, json=data)
                validateResponse(response)
            with pytest.raises(Exception):
                otherUserHeaders = setAuthHeaders(state.userData[otherUserId]['token'])
                response = client.simulate_put('/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}'.format(
                    userId=otherUserId, locationId=otherUserLocationId, deviceId=deviceId), headers=otherUserHeaders, json=data)
                validateResponse(response)



def test_checkUpdateDevices(client, state):

    for userId, userData in state.userData.items():
        headers = setAuthHeaders(state.userData[userId]['token'])
        otherUserId = state.getOtherUserId(userId)
        # Check all the devices
        for locationId, devicesList in userData['locations'].items():
            response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}/devices'.format(
                userId=userId, locationId=locationId), headers=headers)
            devices = validateResponse(response)
            assert(len(devices) == len(devicesList))

            # Try to get the other user devices (This must fail)
            otherUserLocationId = state.userData[otherUserId]['locations'].keys()[0]
            with pytest.raises(Exception):
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}/devices'.format(
                    userId=otherUserId, locationId=otherUserLocationId), headers=headers)
                device = validateResponse(response)
                assert(devices)
            with pytest.raises(Exception):
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}/devices'.format(
                    userId=userId, locationId=otherUserLocationId), headers=headers)
                devices = validateResponse(response)
                assert(devices)

            # Get every device individually
            for deviceId in devicesList:
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}'.format(
                    userId=userId, locationId=locationId, deviceId=deviceId), headers=headers)
                device = validateResponse(response)
                assert(device['deviceVersion'] == deviceId+userId)


def test_deleteDevices(client, state):

    for devicesToAdd, (userId, userData) in enumerate(state.userData.items(), 1):
        headers = setAuthHeaders(userData['token'])
        otherUserId = state.getOtherUserId(userId)

        locationId = userData['locations'].keys()[0]
        for i in xrange(devicesToAdd):
            deviceId = userData['locations'][locationId][i]
            response = client.simulate_delete('/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}'.format(
                userId=userId, locationId=locationId, deviceId=deviceId), headers=headers)
            validateResponse(response)

            # Try to update the device to other user (These all must fail)
            otherUserLocationId = state.userData[otherUserId]['locations'].keys()[
                0]
            with pytest.raises(Exception):
                response = client.simulate_delete('/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}'.format(
                    userId=userId, locationId=otherUserLocationId, deviceId=deviceId), headers=headers)
                validateResponse(response)
            with pytest.raises(Exception):
                response = client.simulate_delete('/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}'.format(
                    userId=otherUserId, locationId=otherUserLocationId, deviceId=deviceId), headers=headers)
                validateResponse(response)
            with pytest.raises(Exception):
                otherUserHeaders = setAuthHeaders(
                    state.userData[otherUserId]['token'])
                response = client.simulate_delete('/api/v1/users/{userId}/locations/{locationId}/devices/{deviceId}'.format(
                    userId=otherUserId, locationId=otherUserLocationId, deviceId=deviceId), headers=otherUserHeaders)
                validateResponse(response)


def test_checkDeletedDevices(client, state):
    for userId, userData in state.userData.items():
        headers = setAuthHeaders(state.userData[userId]['token'])

        # Check all the devices
        for locationId in userData['locations']:
            response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}/devices'.format(
                userId=userId, locationId=locationId), headers=headers)
            devices = validateResponse(response)
            assert(not devices)


def test_deleteUsers(client, state):

    for userId, userData in state.userData.items():
        headers = setAuthHeaders(userData['token'])
        response = client.simulate_delete(
            '/api/v1/users/{userId}'.format(userId=userId), headers=headers)
        validateResponse(response)
