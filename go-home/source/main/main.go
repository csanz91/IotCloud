package main

import (
	"customlogger"
	"encoding/json"
	"model"
	"mqtt"
	"net/http"
)

var (
	agentID = "homeAPI"
	logger  = customlogger.GetInstance()
)

func handle(w http.ResponseWriter, r *http.Request) {
	// Save a copy of this request for debugging.
	/* 	requestDump, err := httputil.DumpRequest(r, true)
	   	if err != nil {
	   		fmt.Println(err)
	   	}
	   	fmt.Println(string(requestDump)) */

	// Set the content type of the response
	w.Header().Set("Content-Type", "application/json")

	// Decode the response
	dfReq := model.DeviceRequest{}
	if dfErr := json.NewDecoder(r.Body).Decode(&dfReq); dfErr != nil {
		model.ReturnAPIErrorProtocolError(w, "Not_Available")
		return
	}

	// Process the inputs
	for _, input := range dfReq.Inputs {
		switch input.Intent {
		case "action.devices.SYNC":
			handleDeviceSync(w, r, dfReq, input)
		case "action.devices.QUERY":
			handleDeviceQuery(w, r, dfReq, input)
		case "action.devices.EXECUTE":
			handleDeviceExecute(w, r, dfReq, input)
		case "action.devices.DISCONNECT":
			handleDeviceDisconnect(w, r, dfReq, input)
		default:
			model.ReturnAPIErrorNotSupported(w, dfReq.RequestID)
			returnAPIErrorMessage(w, dfReq.RequestID)
			return
		}
	}
}

func main() {

	logger.Println("Starting...")

	// Start the mqtt connection to talk with the devices
	mqtt.Connect()

	// Startup the server
	http.HandleFunc("/", handle)
	http.ListenAndServe(":5001", nil)
}
