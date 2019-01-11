# -*- coding: utf-8 -*-


import api

from falcon import testing
import pytest

##############################################
## Auxiliar functions
##############################################
def validateResponse(response):
    assert(response.status_code==200)
    jsonResponse = response.json
    assert(jsonResponse['result'])

    try:
        return jsonResponse['data']
    except KeyError:
        return None

def validateToken(token):
    req = Request()
    api.middleware.verifyToken(req, token)
    assert("auth0" in req.context['auth']['subject'])

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
## Mocked objects
##############################################
class Request():
    context={}

class State():
    userId = ""
    token = ""
    userData = {}

##############################################
## Sample data
##############################################
validUserData={"email":"user@test.comxyz",
                "name":"Pepito",
                "lastName":"de los palotes",
                "password":"a12345678A",
                "wantUpdates": True,
                "gdprAcceptance": True,
                "language":"es"}

gdprMissingUserData={"email":"user@test.comxyz",
                    "name":"Pepito",
                    "lastName":"de los palotes",
                    "password":"a12345678A",
                    "wantUpdates": False,
                    "gdprAcceptance": True,
                    "language":"es"}

mailMissingUserData={"name":"Pepito",
                    "lastName":"de los palotes",
                    "password":"a12345678A",
                    "wantUpdates": True,
                    "gdprAcceptance": True,
                    "language":"es"}

weakPasswordUserData={"name":"Pepito",
                    "lastName":"de los palotes",
                    "password":"12345678",
                    "wantUpdates": False,
                    "gdprAcceptance": True,
                    "language":"es"}

badUserData={}
                    

##############################################
## Function tests
##############################################
@pytest.fixture()
def client():
    return testing.TestClient(api.app)


@pytest.mark.parametrize("data, expectedResult", [
    ({'email': 'user@test.comxzy', 'password': 'a12345678A'}, True),
    ({'email': 'user@test.comxzy', 'password': '1234'}, False),
    ({'email': 'user@test.comxzy', 'pass': 'a12345678A'}, False),
    ({'em': 'user@test.comxzy', 'pass': 'a12345678Añ'}, False),
    ({}, False)
])
def test_login(client, data, expectedResult):

    response = client.simulate_post('/api/v1/login', json=data)
    def func():
        loginData = validateResponse(response)
        token = loginData['token']
        validateToken(token)
    tryFunction(func, expectedResult)
    

@pytest.mark.skip(reason="Recover Limit reached")
@pytest.mark.parametrize("data, expectedResult", [
    ({'email': 'user@test.comxzy'}, True),
    ({'emai': 'user@test.comxzy', 'password': '1234'}, False),
    ({'pass': 'a12345678A'}, False),
    ({}, False)
])
def test_recoverpassword(client, data, expectedResult):

    response = client.simulate_post('/api/v1/recoverpassword', json=data)

    def func():
        text = validateResponse(response)
        assert text == "We've just sent you an email to reset your password."
    tryFunction(func, expectedResult)
    

@pytest.fixture(scope='session')
def state():
    state = State()
    return state


@pytest.mark.parametrize("data, expectedResult", [
    (validUserData, True),
    (gdprMissingUserData, False),
    (mailMissingUserData, False),
    (weakPasswordUserData, False),
    (badUserData, False),
    ({}, False)
])
def test_userFlowRegister(client, data, expectedResult, state):

    response = client.simulate_post('/api/v1/user', json=data)

    def func():
        userId = validateResponse(response)
        assert userId
        state.userId = userId
        state.userData = data

    tryFunction(func, expectedResult)


def test_userFlowLogin(client, state):

    data = {'email': state.userData['email'], 'password': state.userData['password']}

    response = client.simulate_post('/api/v1/login', json=data)
    loginData = validateResponse(response)
    token = loginData['token']
    validateToken(token)

    state.token = token


def test_userFlowGet(client, state):

    headers = setAuthHeaders(state.token)
    response = client.simulate_get('/api/v1/users/{userId}'.format(userId=state.userId), headers=headers)
    userData = validateResponse(response)
    assert(userData['lastName']==state.userData['lastName'])


@pytest.mark.parametrize("data, expectedResult", [
    ({'lastName': "lastname1"}, True),
    ({'name': "name1"}, True),
    ({'othervalue': "othervalue1"}, False)
])
def test_userFlowUpdate(client, data, expectedResult, state):

    headers = setAuthHeaders(state.token)
    response = client.simulate_put('/api/v1/users/{userId}'.format(userId=state.userId), headers=headers, json=data)
    validateResponse(response)


@pytest.mark.parametrize("data, expectedResult", [
    ({'lastName': "lastname1"}, True),
    ({'name': "name1"}, True),
    ({'othervalue': "othervalue1"}, False)
])
def test_userFlowGetUpdatedValues(client, data, expectedResult, state):

    headers = setAuthHeaders(state.token)

    response = client.simulate_get('/api/v1/users/{userId}'.format(userId=state.userId), headers=headers)
    userData = validateResponse(response)
    
    for key, value in data.items():
        def func():
            assert(userData[key]==value)
        tryFunction(func, expectedResult)

def test_userFlowDelete(client, state):

    headers = setAuthHeaders(state.token)
    response = client.simulate_delete('/api/v1/users/{userId}'.format(userId=state.userId), headers=headers)
    validateResponse(response)