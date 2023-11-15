package main

import (
	"encoding/json"
	"home/model"
	"net/http"
)

func handleDeviceQuery(w http.ResponseWriter, r *http.Request, dfReq model.DeviceRequest, input model.InputModel) {

	if err := requestedDeviceExist(r, input.Payload.Devices); err != nil {
		model.ReturnAPIErrorDeviceNotFound(w, dfReq.RequestID)
		return
	}

	devicesPropertyes := map[string]model.DeviceProperties{}
	for _, device := range input.Payload.Devices {
		ID := device.ID

		deviceProperties, err := getDeviceStates(ID, device.CustomData["type"].(string))
		if err != nil {
			continue
		}
		devicesPropertyes[ID] = deviceProperties
	}

	json.NewEncoder(w).Encode(model.DeviceResponseQuery{
		RequestID: dfReq.RequestID,
		Payload: model.ResponsePayloadQuery{
			Devices: devicesPropertyes,
		},
	})
}
