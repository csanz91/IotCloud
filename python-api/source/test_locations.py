# -*- coding: utf-8 -*-

import api

from falcon import testing
import pytest
import api_utils

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
            if userId!=otherUserId:
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

tokenValid = {}

tokenExpired = '''eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ik1VSTJOM
                  FF5UlVNM1JqQkdNelV5TURBMFFqWTNNalJHTnpjMk5VTkdOREUxTX
                  pNeVJURTROZyJ9.eyJpc3MiOiJodHRwczovL2lvdGF1dGguZXUuYX
                  V0aDAuY29tLyIsInN1YiI6ImF1dGgwfDViYWNkMjc5ZjNmM2NkMWI
                  xODAzYjYxZiIsImF1ZCI6ImZhbGNvbkFQSSIsImlhdCI6MTUzODIz
                  Mzc5MywiZXhwIjoxNTM4MzIwMTkzLCJhenAiOiJESTZOZVk2YjdCY
                  Wd1elMzaVp1VlVMcHlJM2R1bWcwTyIsImd0eSI6InBhc3N3b3JkIn
                  0.OcuvvM12OOr6uzArayamH8-N7yoQw9og9MN3LYHaiWXoaA_Qv5F
                  ZlTVTbqoYS6h7rxph4ed5kE2InP91065JK9DMzAEUKdcDbya81-13
                  XR1LqGXq3XrHbY-6BTXq__zS1NxhLmng0ExomTXbR6fupmO9UwN6Q
                  _WiYKCiWfVQWdWgznLw1D9TWC_8G-CPxODSko0fdAK51GWx2nIorX
                  -TlXUf9iiIqN4etNbXfvBwYuLwAO2pAoz307izGe6wbd_HZteaoIo
                  tNzGJiLKrqhwZdV-7drH5Ad6H8-NjaD_Uja9K4TpIgsW3CsD9YKdQ
                  NPxenRJRUVOrc8-YLeBhoneQqw'''


tokenInvalidSignature = '''eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6
                           Ik1VSTJOMFF5UlVNM1JqQkdNelV5TURBMFFqWTNNalJH
                           TnpjMk5VTkdOREUxTXpNeVJURTROZyJ9.eyJpc3MiOiJ
                           odHRwczovL2lvdGF1dGguZXUuYXV0aDAuY29tLyIsInN
                           1YiI6ImF1dGgwfDViYWNkMjc5ZjNmM2NkMWIxODAzYjY
                           xZiIsImF1ZCI6ImZhbGNvbkFQSSIsImlhdCI6MTUzODU
                           wMDAwNiwiZXhwIjoxNTM4NTg2NDA2LCJhenAiOiJESTZ
                           OZVk2YjdCYWd1elMzaVp1VlVMcHlJM2R1bWcwTyIsInN
                           jb3BlIjoicmVhZDpkZXZpY2VzIiwiZ3R5IjoicGFzc3d
                           vcmQifQ.rAvNa9lXQmqeJuKHqoN9v0vLbw1GW497-ewb
                           HK4JJaBUXPWgMxsOn-CbvmAotbz8hE09rFktASV8UaCT
                           ouFnuKz1CaPpu88gV51u6RPSiK-Jft7o172Khfqkfn5_
                           b5wBzd3tsV7HlxIIGc8Ba-gMSz31oT6DckXMVE85lZwK
                           O8rxgEcs6DZ7xXlcxRm3aRrhsURv6KXPWuaoE179VIcC
                           V7DqCa0scMoAxGwc5L0_oV731B-ds0-QSMhXeQhGypTS
                           2HmS796drNPHw6ePk1uD2qJ3iee3Vm0JyyClzf90-1of
                           wFXvxbDiW-jx1VHaA3L2QXqvvFvu2gWxTlz0XFB02H'''


locationsData = [{"locationName":"locationA1",
                "postalCode":"1111",
                "city":"AAA111"},
                {"locationName":"locationA2",
                "postalCode":"2222",
                "city":"AAA222"},
                {"locationName":"locationB1",
                "postalCode":"4444",
                "city":"BBB444"},
                {"locationName":"locationB2",
                "postalCode":"5555",
                "city":"BBB555"}]


##############################################
# Function tests
##############################################


@pytest.fixture()
def client():
    return testing.TestClient(api.app)


@pytest.mark.parametrize("token", [
    (tokenExpired),
    (tokenInvalidSignature)
])
def test_tokens(client, token):

    userId = "auth0|5bacd279f3f3cd1b1803b61f"
    headers = setAuthHeaders(token)
    with pytest.raises(Exception):
        response = client.simulate_get('/api/v1/users/{userId}'.format(userId), headers=headers)
        validateResponse(response)

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

    state.userData[userId] = {"locations": [], "data": data}


def test_userFlowLogin(client, state):

    for userId, data in state.userData.items():
        data = {'email': data['data']['email'], 'password': data['data']['password']}
        response = client.simulate_post('/api/v1/login', json=data)
        loginData = validateResponse(response)
        assert(userId==loginData['userId'])
        state.userData[userId]["token"] = loginData['token']


def test_userFlowGet(client, state):

    for userId, data in state.userData.items():
        # Get the data from the actual user
        headers = setAuthHeaders(state.userData[userId]['token'])
        response = client.simulate_get('/api/v1/users/{userId}'.format(userId=userId), headers=headers)
        responseData = validateResponse(response)
        assert(responseData['lastName']==data['data']['lastName'])

        # Get the data from the other user (This should fail)
        otherUserId = state.getOtherUserId(userId)
        headers = setAuthHeaders(state.userData[userId]['token'])
        with pytest.raises(Exception):
            response = client.simulate_get('/api/v1/users/{userId}'.format(userId=otherUserId), headers=headers)
            validateResponse(response)


def test_addLocations(client, state):

    for i, (userId, userData) in enumerate(state.userData.items()):
        headers = setAuthHeaders(userData['token'])
        for locationIdx in xrange(2):
            locationData = locationsData[2*i+locationIdx]
            response = client.simulate_post('/api/v1/users/{userId}/locations'.format(userId=userId), headers=headers, json=locationData)
            locationId = validateResponse(response)
            assert(locationId)
            state.userData[userId]["locations"].append(locationId)

            # Set the data from the other user (This should fail)
            otherUserId = state.getOtherUserId(userId)
            headers = setAuthHeaders(state.userData[userId]['token'])
            with pytest.raises(Exception):
                response = client.simulate_post('/api/v1/users/{userId}/locations'.format(userId=otherUserId), headers=headers, json=locationData)
                validateResponse(response)


def test_getLocations(client, state):

    for i, (userId, userData) in enumerate(state.userData.items()):
        headers = setAuthHeaders(userData['token'])

        response = client.simulate_get('/api/v1/users/{userId}/locations'.format(userId=userId), headers=headers)
        assert(len(validateResponse(response))==2)

        for locationIdx in xrange(2):
            locationDataExpected = locationsData[2*i+locationIdx]
            response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}'.format(userId=userId, locationId=userData['locations'][locationIdx]), headers=headers)
            locationData = validateResponse(response)
            assert(locationData['_id']==userData['locations'][locationIdx])
            assert(locationData['locationName']==locationDataExpected['locationName'])

            # Set the data from the other user (This should fail)
            otherUserId = state.getOtherUserId(userId)
            headers = setAuthHeaders(state.userData[userId]['token'])
            with pytest.raises(Exception):
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}'.format(userId=otherUserId, locationId=userData['locations'][locationIdx]), headers=headers)
                validateResponse(response)

            headers = setAuthHeaders(state.userData[userId]['token'])
            with pytest.raises(Exception):
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}'.format(userId=userId, locationId=state.userData[otherUserId]['locations'][locationIdx]), headers=headers)
                location = validateResponse(response)
                assert(location)


def test_requestLocationPermissions(client, state):

    for userId, userData in state.userData.items():
        headers = setAuthHeaders(userData['token'])

        locationId = userData['locations'][0]
        otherUserId = state.getOtherUserId(userId)
        combinations = [({"email": state.userData[otherUserId]['data']['email'], "role": api_utils.Roles.viewer}, locationId, True), 
                        ({"email": userData['data']['email'], "role": api_utils.Roles.viewer}, locationId, False),
                        ({"email": state.userData[otherUserId]['data']['email'], "role": 8}, locationId, False),
                        ({"emil": state.userData[otherUserId]['data']['email'], "role": api_utils.Roles.viewer}, locationId, False),
                        ({"email": state.userData[otherUserId]['data']['email'], "rol": api_utils.Roles.viewer}, locationId, False)]

        for combination, locationId, expectedResult in combinations:
            def func():
                response = client.simulate_post('/api/v1/users/{userId}/locations/{locationId}/permissions'.format(userId=userId, locationId=locationId), headers=headers, json=combination)
                shareId = validateResponse(response)
                userData['shareId'] = shareId
            tryFunction(func, expectedResult)

        # Get the data from the other user (This should fail)
        headers = setAuthHeaders(state.userData[userId]['token'])
        with pytest.raises(Exception):
            response = client.simulate_get('/api/v1/users/{userId}/locations'.format(userId=otherUserId), headers=headers)
            validateResponse(response)


def test_getLocationsAfterAddingPermissions(client, state):

    for userId in state.userData:

        otherUserId = state.getOtherUserId(userId)

        # The number of locations must be exactly 2
        headers = setAuthHeaders(state.userData[userId]['token'])
        response = client.simulate_get('/api/v1/users/{userId}/locations'.format(userId=userId), headers=headers)
        locations = validateResponse(response)
        assert(len(locations)==2)

        # Try to get the location from the other user
        locationId = state.userData[otherUserId]['locations'][0]
        combinations = [(userId, False),
                        (otherUserId, True)]
        for userId, expectedResult in combinations:
            def func():
                headers = setAuthHeaders(state.userData[userId]['token'])
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}'.format(userId=userId, locationId=locationId), headers=headers)
                location = validateResponse(response)
                assert(location)
            tryFunction(func, expectedResult)


def test_validatePermissions(client, state):
    for userId, userData in state.userData.items():

        otherUserId = state.getOtherUserId(userId)
        otherLocationId = state.userData[otherUserId]['locations'][0]
        shareId = userData['shareId']
        otherShareId = state.userData[otherUserId]['shareId']

        headers = setAuthHeaders(userData['token'])

        combinations = [({'shareId': otherShareId}, True),
                        ({'shareId': shareId}, False),
                        ({'shaeId': shareId}, False)]

        for combination, expectedResult in combinations:

            def func():
                response = client.simulate_post('/api/v1/users/{userId}/permissionvalidation'.format(userId=userId), headers=headers, json=combination)
                validateResponse(response)

            tryFunction(func, expectedResult)


def test_getLocationsAfterValidatingPermissions(client, state):

    for userId in state.userData:

        otherUserId = state.getOtherUserId(userId)

        # The number of locations must be exactly 3
        headers = setAuthHeaders(state.userData[userId]['token'])
        response = client.simulate_get('/api/v1/users/{userId}/locations'.format(userId=userId), headers=headers)
        locations = validateResponse(response)
        assert(len(locations)==3)

        # Try to get the location from the other user
        locationId1 = state.userData[otherUserId]['locations'][0]
        locationId2 = state.userData[otherUserId]['locations'][1]
        combinations = [(userId, locationId1, True),
                        (userId, locationId2, False)]
        for userId, locationId, expectedResult in combinations:
            def func():
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}'.format(userId=userId, locationId=locationId), headers=headers)
                location = validateResponse(response)
                assert(location)
            tryFunction(func, expectedResult)


def test_updateLocation(client, state):

    for userId in state.userData:

        otherUserId = state.getOtherUserId(userId)

        # The number of locations must be exactly 3
        headers = setAuthHeaders(state.userData[userId]['token'])
        response = client.simulate_get('/api/v1/users/{userId}/locations'.format(userId=userId), headers=headers)
        locations = validateResponse(response)
        assert(len(locations)==3)

        # Try to update the location from the other user
        locationId1 = state.userData[userId]['locations'][0]
        locationId2 = state.userData[userId]['locations'][1]
        otherLocationId1 = state.userData[otherUserId]['locations'][0]
        otherLocationId2 = state.userData[otherUserId]['locations'][1]

        # Edit the individual fields
        combinations = [(locationId1, True),
                        (locationId2, True),
                        (otherLocationId1, True),
                        (otherLocationId2, False)]
        for locationId, expectedResult in combinations:
            def func():
                data = {"locationName": userId+locationId}
                response = client.simulate_put('/api/v1/users/{userId}/locations/{locationId}'.format(userId=userId, locationId=locationId), headers=headers, json=data)
                validateResponse(response)
            tryFunction(func, expectedResult)

        # Edit the shared fields
        combinations = [(locationId1, True),
                        (locationId2, True),
                        (otherLocationId1, True), # Dont return failure but the field is not updated
                        (otherLocationId2, False)]
        for locationId, expectedResult in combinations:
            def func2():
                data = {"postalCode": userId+locationId}
                response = client.simulate_put('/api/v1/users/{userId}/locations/{locationId}'.format(userId=userId, locationId=locationId), headers=headers, json=data)
                validateResponse(response)
            tryFunction(func2, expectedResult)


def test_checkLocationAfterUpdate(client, state):

    for userId, userData in state.userData.items():
        headers = setAuthHeaders(state.userData[userId]['token'])
        response = client.simulate_get('/api/v1/users/{userId}/locations'.format(userId=userId), headers=headers)
        for locationId in userData['locations']:
            response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}'.format(userId=userId, locationId=locationId), headers=headers)
            location = validateResponse(response)
            # Individual fields can always be updated
            assert(userId+locationId==location['locationName'])
            # Shared fields should haven't been updated
            assert(userId+locationId==location['postalCode'])    


def test_updatePermissions(client, state):
    for userId, userData in state.userData.items():
        headers = setAuthHeaders(state.userData[userId]['token'])
        sharedToUserId = state.getOtherUserId(userId)
        locationId = userData['locations'][0]
        shareId = userData['shareId']
        data = {'newRole': api_utils.Roles.editor}
        response = client.simulate_put('/api/v1/users/{userId}/permissions/{shareId}'.format(userId=userId, shareId=shareId), headers=headers, json=data)
        validateResponse(response)


def test_updateOtherUserLocation(client, state):

    for userId in state.userData:

        otherUserId = state.getOtherUserId(userId)
        headers = setAuthHeaders(state.userData[userId]['token'])

        # Try to get the location from the other user
        locationId = state.userData[userId]['locations'][0]
        locationId2 = state.userData[userId]['locations'][1]
        otherLocationId = state.userData[otherUserId]['locations'][0]
        otherLocationId2 = state.userData[otherUserId]['locations'][1]
        combinations = [(userId, locationId2, True),
                        (userId, otherLocationId, True),
                        (userId, otherLocationId2, False),
                        (otherUserId, otherLocationId2, False)]
        for locationOwnerId, locationId, expectedResult in combinations:
            def func():
                data = {"postalCode": locationId+userId}
                response = client.simulate_put('/api/v1/users/{userId}/locations/{locationId}'.format(userId=locationOwnerId, locationId=locationId), headers=headers, json=data)
                validateResponse(response)
            tryFunction(func, expectedResult)


def test_checkLocationAfterUpdate2(client, state):
    for userId, userData in state.userData.items():
        headers = setAuthHeaders(state.userData[userId]['token'])

        otherUserId = state.getOtherUserId(userId)

        # Try to get the location from the other user
        locationId = userData['locations'][0]
        locationId2 = userData['locations'][1]
        otherLocationId = state.userData[otherUserId]['locations'][0]
        otherLocationId2 = state.userData[otherUserId]['locations'][1]
        combinations = [(userId, locationId2, True),
                        (userId, otherLocationId, True),
                        (userId, otherLocationId2, False),
                        (otherUserId, otherLocationId2, False)]
        for locationOwnerId, locationId, expectedResult in combinations:
            def func():
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}'.format(userId=locationOwnerId, locationId=locationId), headers=headers)
                location = validateResponse(response)
                assert(location['postalCode']==locationId+userId)
            tryFunction(func, expectedResult)


def test_removePermissions(client, state):
    for userId, userData in state.userData.items():
        headers = setAuthHeaders(state.userData[userId]['token'])
        sharedToUserId = state.getOtherUserId(userId)
        locationId = userData['locations'][0]
        shareId = userData['shareId']
        response = client.simulate_delete('/api/v1/users/{userId}/permissions/{shareId}'.format(userId=userId, shareId=shareId), headers=headers)
        validateResponse(response)


def test_getLocationsAfterRemovingPermissions(client, state):

    for userId in state.userData:

        otherUserId = state.getOtherUserId(userId)

        # The number of locations must be exactly 2
        headers = setAuthHeaders(state.userData[userId]['token'])
        response = client.simulate_get('/api/v1/users/{userId}/locations'.format(userId=userId), headers=headers)
        locations = validateResponse(response)
        assert(len(locations)==2)

        # Try to get the location from the other user
        locationId = state.userData[otherUserId]['locations'][0]
        combinations = [(userId, False),
                        (otherUserId, True)]
        for userId, expectedResult in combinations:
            def func():
                headers = setAuthHeaders(state.userData[userId]['token'])
                response = client.simulate_get('/api/v1/users/{userId}/locations/{locationId}'.format(userId=userId, locationId=locationId), headers=headers)
                location = validateResponse(response)
                assert(location)
            tryFunction(func, expectedResult)


def test_deleteLocation(client, state):
    for userId in state.userData:

        otherUserId = state.getOtherUserId(userId)

        # Try to update the location from the other user
        locationId = state.userData[userId]['locations'][0]

        combinations = [(userId, locationId, True),
                        (otherUserId, locationId, False),]
        for userId, locationId, expectedResult in combinations:
            def func():
                headers = setAuthHeaders(state.userData[userId]['token'])
                response = client.simulate_delete('/api/v1/users/{userId}/locations/{locationId}'.format(userId=userId, locationId=locationId), headers=headers)
                validateResponse(response)
            tryFunction(func, expectedResult)


def test_getLocations2(client, state):
    for userId, userData in state.userData.items():
        headers = setAuthHeaders(userData['token'])

        response = client.simulate_get('/api/v1/users/{userId}/locations'.format(userId=userId), headers=headers)
        assert(len(validateResponse(response))==1)


def test_deleteUsers(client, state):
    for userId, userData in state.userData.items():
        headers = setAuthHeaders(userData['token'])
        response = client.simulate_delete('/api/v1/users/{userId}'.format(userId=userId), headers=headers)
        validateResponse(response)
