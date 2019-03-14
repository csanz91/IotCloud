package main

import (
	"encoding/json"
	"iotcloud"
	"model"
	"net/http"
)

func handleDeviceSync(w http.ResponseWriter, r *http.Request, dfReq model.DeviceRequest, input model.InputModel) {

	authToken, err := getTokenFromHeaders(r)
	if err != nil {
		model.ReturnAPIErrorAuthFailure(w, dfReq.RequestID)
		return
	}

	apiDevices, userID, err := iotcloud.GetUserDevices(authToken, true)
	if err != nil {
		model.ReturnAPIErrorDeviceNotFound(w, dfReq.RequestID)
		return
	}

	var googleDevices = []model.ResponseDeviceModel{}
	for _, device := range apiDevices {
		for _, sensor := range device.Sensors {
			googleDeviceType, err := model.GetGoogleDeviceType(sensor.Type)
			if err != nil {
				continue
			}
			newGoogleDevice := model.ResponseDeviceModel{
				ID:     device.DeviceID + "$" + sensor.ID,
				Type:   googleDeviceType.Type,
				Traits: googleDeviceType.Traits,
				Name: model.DeviceNameModel{
					Name: sensor.Name,
				},
				WillReportState: false,
				RoomHint:        sensor.Room,
				DeviceInfo: model.DeviceInfo{
					Manufacturer: "csm",
					Model:        sensor.Type,
					SwVersion:    device.DeviceVersion,
				},
				Attributes: googleDeviceType.Attributes,
				CustomData: map[string]interface{}{"type": sensor.Type, "locationId": device.LocationID},
			}
			googleDevices = append(googleDevices, newGoogleDevice)
		}
	}

	json.NewEncoder(w).Encode(model.DeviceResponseSync{
		RequestID: dfReq.RequestID,
		Payload: model.ResponsePayloadSync{
			AgentUserID: userID,
			Devices:     googleDevices,
		},
	})
}
