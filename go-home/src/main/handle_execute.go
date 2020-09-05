package main

import (
	"encoding/json"
	"fmt"
	"model"
	"mqtt"
	"net/http"
	"strconv"
)

// Aux function to add an ID to a response
func addID(responseModel model.ResponseCommandsModel, ID string) model.ResponseCommandsModel {
	ids := responseModel.Ids
	ids = append(ids, ID)
	responseModel.Ids = ids
	return responseModel
}

func handleDeviceExecute(w http.ResponseWriter, r *http.Request, dfReq model.DeviceRequest, input model.InputModel) {

	responseCommands := []model.ResponseCommandsModel{}
	for _, command := range input.Payload.Commands {
		if err := requestedDeviceExist(r, command.Devices); err != nil {
			model.ReturnAPIErrorDeviceNotFound(w, dfReq.RequestID)
			return
		}
		responsesModels := map[string]model.ResponseCommandsModel{}

		responsesModels["pending"] = model.ResponseCommandsModel{
			Status: "PENDING",
		}
		responsesModels["protocolError"] = model.ResponseCommandsModel{
			Status:    "ERROR",
			ErrorCode: "protocolError",
		}
		responsesModels["deviceOffline"] = model.ResponseCommandsModel{
			Status:    "ERROR",
			ErrorCode: "deviceOffline",
		}
		responsesModels["safetyShutOff"] = model.ResponseCommandsModel{
			Status:    "ERROR",
			ErrorCode: "safetyShutOff",
		}

		for _, execution := range command.Execution {
			for _, device := range command.Devices {
				ID := device.ID
				deviceID, sensorID := decodeID(ID)
				locationID := device.CustomData["locationId"].(string)
				deviceType := device.CustomData["type"].(string)

				// First check the status
				status, err := mqtt.GetStatus(deviceID)
				if err != nil {
					status = false
				}
				if !status {
					responsesModels["deviceOffline"] = addID(responsesModels["deviceOffline"], ID)
					continue
				}

				// If the device is a thermostat, check the alarm status
				if deviceType == "thermostat" {
					auxValues, err := mqtt.GetAux(deviceID, sensorID)
					if err != nil {
						continue
					}
					alarm, err := strconv.ParseBool(auxValues["alarm"])
					if err == nil && alarm {
						responsesModels["safetyShutOff"] = addID(responsesModels["safetyShutOff"], ID)
						continue
					}
				}

				// Set device state
				if execution.Command == "action.devices.commands.OnOff" {
					newState := execution.Params["on"].(bool)
					if err := mqtt.SetState(locationID, deviceID, sensorID, newState); err == nil {
						responsesModels["pending"] = addID(responsesModels["pending"], ID)
					} else {
						responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
					}

					// Toogle
				} else if execution.Command == "action.devices.commands.OpenClose" {
					openPercent := execution.Params["openPercent"].(float64)
					var action string
					if openPercent == 100.0 {
						action = "up"
					} else if openPercent == 0.0 {
						action = "down"
					}
					if err := mqtt.SetAux(locationID, deviceID, sensorID, "setToogle", action, false); err == nil {
						responsesModels["pending"] = addID(responsesModels["pending"], ID)
					} else {
						responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
					}
					// Thermostat setpoint
				} else if deviceType == "thermostat" && execution.Command == "action.devices.commands.ThermostatTemperatureSetpoint" {
					setpoint := execution.Params["thermostatTemperatureSetpoint"].(float64)
					if err := mqtt.SetAux(locationID, deviceID, sensorID, "setpoint", fmt.Sprintf("%.2f", setpoint), true); err == nil {
						responsesModels["pending"] = addID(responsesModels["pending"], ID)
					} else {
						responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
					}

				} else if deviceType == "thermostat" && execution.Command == "action.devices.commands.ThermostatSetMode" {
					thermostatMode := execution.Params["thermostatMode"].(string)
					newState := thermostatMode == "heat" || thermostatMode == "on"
					if err := mqtt.SetState(locationID, deviceID, sensorID, newState); err == nil {
						responsesModels["pending"] = addID(responsesModels["pending"], ID)
					} else {
						responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
					}
				} else if execution.Command == "action.devices.commands.ColorAbsolute" {
					intColor := int(execution.Params["color"].(map[string]interface{})["spectrumRGB"].(float64))
					color := "FF" + fmt.Sprintf("%06x", intColor)

					if err := mqtt.SetAux(locationID, deviceID, sensorID, "setColor", color, true); err == nil {
						responsesModels["pending"] = addID(responsesModels["pending"], ID)
					} else {
						responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
					}

				} else if execution.Command == "action.devices.commands.BrightnessAbsolute" {
					brightness := execution.Params["brightness"].(float64) / 100.0

					if err := mqtt.SetAux(locationID, deviceID, sensorID, "setBrightness", fmt.Sprintf("%.2f", brightness), true); err == nil {
						responsesModels["pending"] = addID(responsesModels["pending"], ID)
					} else {
						responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
					}

				} else if execution.Command == "action.devices.commands.SetInput" ||
					execution.Command == "action.devices.commands.NextInput" ||
					execution.Command == "action.devices.commands.PreviousInput" {

					if err := mqtt.SetAux(locationID, deviceID, sensorID, "command", "SOURCE", false); err == nil {
						responsesModels["pending"] = addID(responsesModels["pending"], ID)
					} else {
						responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
					}

				} else if execution.Command == "action.devices.commands.mediaPause" {

					if err := mqtt.SetAux(locationID, deviceID, sensorID, "command", "PAUSE", false); err == nil {
						responsesModels["pending"] = addID(responsesModels["pending"], ID)
					} else {
						responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
					}

				} else if execution.Command == "action.devices.commands.mediaResume" {

					if err := mqtt.SetAux(locationID, deviceID, sensorID, "command", "PLAY", false); err == nil {
						responsesModels["pending"] = addID(responsesModels["pending"], ID)
					} else {
						responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
					}

				} else if execution.Command == "action.devices.commands.volumeRelative" {
					up := execution.Params["relativeSteps"].(float64) > 0.0

					if up {
						if err := mqtt.SetAux(locationID, deviceID, sensorID, "command", "UP", false); err == nil {
							responsesModels["pending"] = addID(responsesModels["pending"], ID)
						} else {
							responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
						}
					} else {
						if err := mqtt.SetAux(locationID, deviceID, sensorID, "command", "DOWN", false); err == nil {
							responsesModels["pending"] = addID(responsesModels["pending"], ID)
						} else {
							responsesModels["protocolError"] = addID(responsesModels["protocolError"], ID)
						}
					}

				} else {
					model.ReturnAPIErrorNotSupported(w, dfReq.RequestID)
					return
				}
			}
		}
		// Add response to the list
		for _, responseModel := range responsesModels {
			if responseModel.Ids != nil {
				responseCommands = append(responseCommands, responseModel)
			}
		}
	}

	json.NewEncoder(w).Encode(model.DeviceResponseExecute{
		RequestID: dfReq.RequestID,
		Payload: model.ResponsePayloadExecute{
			Commands: responseCommands,
		},
	})
}
