package model

import (
	"encoding/json"
	"net/http"
)

// ReturnAPIErrorAuthExpired : Credentials have expired.
func ReturnAPIErrorAuthExpired(w http.ResponseWriter, requestID string) {
	returnAPIErrorMessage(w, requestID, "authExpired")
}

// ReturnAPIErrorAuthFailure : General failure to authenticate.
func ReturnAPIErrorAuthFailure(w http.ResponseWriter, requestID string) {
	returnAPIErrorMessage(w, requestID, "authFailure")
}

// ReturnAPIErrorDeviceOffline : The target is unreachable.
func ReturnAPIErrorDeviceOffline(w http.ResponseWriter, requestID string) {
	returnAPIErrorMessage(w, requestID, "deviceOffline")
}

// ReturnAPIErrorTimeout : Internal timeout.
func ReturnAPIErrorTimeout(w http.ResponseWriter, requestID string) {
	returnAPIErrorMessage(w, requestID, "timeout")
}

// ReturnAPIErrorDeviceTurnedOff : The device is known to be turned
// hard off (if distinguishable from unreachable).
func ReturnAPIErrorDeviceTurnedOff(w http.ResponseWriter, requestID string) {
	returnAPIErrorMessage(w, requestID, "deviceTurnedOff")
}

// ReturnAPIErrorDeviceNotFound : The device doesn't exist on the partner's side.
// This normally indicates a failure in data synchronization or a race condition.
func ReturnAPIErrorDeviceNotFound(w http.ResponseWriter, requestID string) {
	returnAPIErrorMessage(w, requestID, "deviceNotFound")
}

// ReturnAPIErrorValueOutOfRange : The range in parameters is out of bounds.
func ReturnAPIErrorValueOutOfRange(w http.ResponseWriter, requestID string) {
	returnAPIErrorMessage(w, requestID, "valueOutOfRange")
}

// ReturnAPIErrorNotSupported : The command or its parameters are unsupported
// (this should generally not happen, as traits and business logic should prevent it).
func ReturnAPIErrorNotSupported(w http.ResponseWriter, requestID string) {
	returnAPIErrorMessage(w, requestID, "notSupported")
}

// ReturnAPIErrorProtocolError : Failure in processing the request.
func ReturnAPIErrorProtocolError(w http.ResponseWriter, requestID string) {
	returnAPIErrorMessage(w, requestID, "protocolError")
}

// ReturnAPIErrorUnknownError : Everything else, although anything that
// throws this should be replaced with a real error code.
func ReturnAPIErrorUnknownError(w http.ResponseWriter, requestID string) {
	returnAPIErrorMessage(w, requestID, "unknownError")
}

func returnAPIErrorMessage(w http.ResponseWriter, requestID string, errorCode string) {
	json.NewEncoder(w).Encode(DeviceResponseError{
		RequestID: requestID,
		Payload: ResponsePayloadError{
			ErrorCode: errorCode,
		},
	})
}
