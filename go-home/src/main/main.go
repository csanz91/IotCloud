package main

import (
	"encoding/json"
	"home/customlogger"
	"home/model"
	"home/mqtt"
	"net/http"
)

var (
	logger = customlogger.GetInstance()
)

type loggingResponseWriter struct {
	http.ResponseWriter
	body []byte
}

func (lrw *loggingResponseWriter) Write(b []byte) (int, error) {
	lrw.body = append(lrw.body, b...)
	return lrw.ResponseWriter.Write(b)
}

func handle(w http.ResponseWriter, r *http.Request) {
	// Save a copy of this request for debugging.
	/* 	requestDump, err := httputil.DumpRequest(r, true)
	   	if err != nil {
	   		fmt.Println(err)
	   	}
	   	fmt.Println(string(requestDump)) */

	// Create a custom ResponseWriter
	lrw := &loggingResponseWriter{ResponseWriter: w}

	// Set the content type of the response
	lrw.Header().Set("Content-Type", "application/json")

	// Decode the response
	dfReq := model.DeviceRequest{}
	if dfErr := json.NewDecoder(r.Body).Decode(&dfReq); dfErr != nil {
		model.ReturnAPIErrorProtocolError(lrw, "Not_Available")
		return
	}

	// Process the inputs
	for _, input := range dfReq.Inputs {
		switch input.Intent {
		case "action.devices.SYNC":
			handleDeviceSync(lrw, r, dfReq, input)
		case "action.devices.QUERY":
			handleDeviceQuery(lrw, r, dfReq, input)
		case "action.devices.EXECUTE":
			handleDeviceExecute(lrw, r, dfReq, input)
		case "action.devices.DISCONNECT":
			handleDeviceDisconnect(lrw, r, dfReq, input)
		default:
			model.ReturnAPIErrorNotSupported(lrw, dfReq.RequestID)
			returnAPIErrorMessage(lrw, dfReq.RequestID)
			return
		}
	}

	// Access the response content for debugging
	// fmt.Println("Response Body:", string(lrw.body))

}

func main() {

	logger.Println("Starting...")

	// Start the mqtt connection to talk with the devices
	mqtt.Connect()

	// Startup the server
	http.HandleFunc("/", handle)
	http.ListenAndServe(":5001", nil)
}
