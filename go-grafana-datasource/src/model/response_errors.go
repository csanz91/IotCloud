package model

import (
	"net/http"
)

// ReturnAPIErrorAuthExpired : Credentials have expired.
func ReturnAPIErrorAuthExpired(w http.ResponseWriter) {
	writeError(w, "authExpired", "Credentials have expired.")
}

// ReturnAPIErrorAuthFailure : General failure to authenticate.
func ReturnAPIErrorAuthFailure(w http.ResponseWriter) {
	writeError(w, "authFailure", "General failure to authenticate.")
}

// ReturnAPIErrorDeviceOffline : The target is unreachable.
func ReturnAPIErrorDeviceOffline(w http.ResponseWriter) {
	writeError(w, "deviceOffline", "The target is unreachable.")
}

// ReturnAPIErrorTimeout : Internal timeout.
func ReturnAPIErrorTimeout(w http.ResponseWriter) {
	writeError(w, "timeout", "Internal timeout.")
}

// ReturnAPIErrorDeviceTurnedOff : The device is known to be turned
// hard off (if distinguishable from unreachable).
func ReturnAPIErrorDeviceTurnedOff(w http.ResponseWriter) {
	writeError(w, "deviceTurnedOff", "The device is known to be turned hard off.")
}

// ReturnAPIErrorDeviceNotFound : The device doesn't exist on the partner's side.
// This normally indicates a failure in data synchronization or a race condition.
func ReturnAPIErrorDeviceNotFound(w http.ResponseWriter) {
	writeError(w, "deviceNotFound", "The device doesn't exist on the partner's side.")
}

// ReturnAPIErrorValueOutOfRange : The range in parameters is out of bounds.
func ReturnAPIErrorValueOutOfRange(w http.ResponseWriter) {
	writeError(w, "valueOutOfRange", "The range in parameters is out of bounds.")
}

// ReturnAPIErrorNotSupported : The command or its parameters are unsupported
// (this should generally not happen, as traits and business logic should prevent it).
func ReturnAPIErrorNotSupported(w http.ResponseWriter) {
	writeError(w, "notSupported", "The command or its parameters are unsupported.")
}

// ReturnAPIErrorProtocolError : Failure in processing the request.
func ReturnAPIErrorProtocolError(w http.ResponseWriter) {
	writeError(w, "protocolError", "Failure in processing the request.")
}

// ReturnAPIErrorUnknownError : Everything else, although anything that
// throws this should be replaced with a real error code.
func ReturnAPIErrorUnknownError(w http.ResponseWriter) {
	writeError(w, "unknownError", "Something went wrong")
}

func writeError(w http.ResponseWriter, e, m string) {
	w.WriteHeader(http.StatusBadRequest)
	w.Write([]byte("{\"error\": \"" + m + ": " + e + "\"}"))
}
