package model

// DeviceRequest : Struct for a generic Google Home Actions request
type DeviceRequest struct {
	RequestID string       `json:"requestId"`
	Inputs    []InputModel `json:"inputs"`
}

// InputModel : Struct for an DeviceRequest Input model
type InputModel struct {
	Intent  string       `json:"intent"`
	Payload PayloadModel `json:"payload"`
}

// PayloadModel : Struct for an Input Payload model
type PayloadModel struct {
	Intent   string                 `json:"intent"`
	Commands []RequestCommandsModel `json:"commands"`
	Devices  []DeviceModel          `json:"devices"`
}

// DeviceModel : Struct for an Payload Device model
type DeviceModel struct {
	ID         string                 `json:"id"`
	CustomData map[string]interface{} `json:"customData"`
}

// RequestCommandsModel : Struct for an Payload Command model
type RequestCommandsModel struct {
	Devices   []DeviceModel    `json:"devices"`
	Execution []ExecutionModel `json:"execution"`
}

// ExecutionModel : Struct for a Command execution model
type ExecutionModel struct {
	Command string                 `json:"command"`
	Params  map[string]interface{} `json:"params"`
}
