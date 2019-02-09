package main

import (
	"encoding/json"
	"errors"
	"iotcloud"
	"model"
	"mqtt"
	"net/http"
	"strconv"
	"strings"
)

func returnAPIErrorMessage(w http.ResponseWriter, requestID string) {
	json.NewEncoder(w).Encode(model.DeviceResponseError{
		RequestID: requestID,
		Payload: model.ResponsePayloadError{
			ErrorCode: "Please try later",
		},
	})
}

func getTokenFromHeaders(r *http.Request) (string, error) {
	// Retrieve the auth token. And get the token from the header 'Bearer 1234567'
	authToken := strings.Split(r.Header.Get("Authorization"), " ")[1]
	if authToken == "" {
		return "", errors.New("The token could not be retrieved")
	}
	return authToken, nil
}

func requestedDeviceExist(r *http.Request, devices []model.DeviceModel) error {
	// Check the devices requested belong to the user
	authToken, err := getTokenFromHeaders(r)
	if err != nil {
		return errors.New("Auth failure")
	}

	apiDevices, _, err := iotcloud.GetUserDevices(authToken, false)
	if err != nil {
		return errors.New("The sensor could not be found")
	}

	// Iterate the devices requested
	for _, device := range devices {
		ID := device.ID
		subIds := strings.Split(ID, "$")
		deviceID := subIds[0]
		sensorID := subIds[1]

		// Try to match the requested device with one from the user
		for deviceIndex, apiDevice := range apiDevices {
			deviceFound := false
			if apiDevice.DeviceID == deviceID {
				// Device found, now find the sensor
				deviceFound = true
				for sensorIndex, sensor := range apiDevice.Sensors {
					if sensor.ID == sensorID {
						break
					}
					// If all the sensors have been checked and no match
					// has been found raise an error
					if sensorIndex == len(apiDevice.Sensors)-1 {
						return errors.New("The sensor could not be found")
					}
				}
			}
			// If the sensor is NOT found, the error is raised before
			// arriving here
			if deviceFound {
				break
			}
			if deviceIndex == len(apiDevices)-1 {
				return errors.New("The device could not be found")
			}
		}

	}
	return nil
}

func getDeviceStates(ID, deviceType string) (model.DeviceProperties, error) {

	subIds := strings.Split(ID, "$")
	deviceID := subIds[0]
	sensorID := subIds[1]

	status, err := mqtt.GetStatus(deviceID)
	if err != nil {
		status = false
	}
	state, err := mqtt.GetState(deviceID, sensorID)
	if err != nil {
		state = false
	}

	deviceProperties := model.DeviceProperties{
		Online: status,
		ON:     state,
	}

	if deviceType == "thermostat" {
		value, err := mqtt.GetValue(deviceID, sensorID)
		if err != nil {
			return model.DeviceProperties{}, err
		}
		deviceProperties.ThermostatTemperatureAmbient = value

		auxValues, err := mqtt.GetAux(deviceID, sensorID)
		if err != nil {
			return model.DeviceProperties{}, err
		}

		if state {
			deviceProperties.ThermostatMode = "heat"
		} else {
			deviceProperties.ThermostatMode = "off"
		}

		humidity, err := strconv.ParseFloat(auxValues["humidity"], 32)
		if err == nil {
			deviceProperties.ThermostatHumidityAmbient = float32(humidity)
		}
		setpoint, err := strconv.ParseFloat(auxValues["setpoint"], 32)
		if err == nil {
			deviceProperties.ThermostatTemperatureSetpoint = float32(setpoint)
		}
	}

	return deviceProperties, nil
}