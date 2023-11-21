package main

import (
	"bytes"
	"encoding/json"
	"home/model"
	"io"
	"net/http"
)

func handleDeviceQuery(w http.ResponseWriter, r *http.Request, dfReq model.DeviceRequest, input model.InputModel) {

	var log bytes.Buffer
	rsp := io.MultiWriter(w, &log)

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

	json.NewEncoder(rsp).Encode(model.DeviceResponseQuery{
		RequestID: dfReq.RequestID,
		Payload: model.ResponsePayloadQuery{
			Devices: devicesPropertyes,
		},
	})
}
