package main

import (
	"encoding/json"
	"home/model"
	"net/http"
)

// handleDeviceDisconnect: 200 Ok with an empty JSON body is all that is needed.
func handleDeviceDisconnect(w http.ResponseWriter, r *http.Request, dfReq model.DeviceRequest, input model.InputModel) {
	json.NewEncoder(w).Encode(struct{}{})
}
