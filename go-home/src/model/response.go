package model

// DeviceResponseSync : Struct for a generic Google Home Actions request
type DeviceResponseSync struct {
	RequestID string              `json:"requestId"`
	Payload   ResponsePayloadSync `json:"payload"`
}

// ResponsePayloadSync : Struct for an DeviceRequest Input model
type ResponsePayloadSync struct {
	AgentUserID string                `json:"agentUserId"`
	Devices     []ResponseDeviceModel `json:"devices"`
}

// DeviceResponseQuery : Struct for a generic Google Home Actions request
type DeviceResponseQuery struct {
	RequestID string               `json:"requestId"`
	Payload   ResponsePayloadQuery `json:"payload"`
}

// ResponsePayloadQuery : Struct for an DeviceRequest Input model
type ResponsePayloadQuery struct {
	Devices map[string]DeviceProperties `json:"devices"`
}

// DeviceResponseExecute : Struct for a generic Google Home Actions request
type DeviceResponseExecute struct {
	RequestID string                 `json:"requestId"`
	Payload   ResponsePayloadExecute `json:"payload"`
}

// ResponsePayloadExecute : Struct for an DeviceRequest Input model
type ResponsePayloadExecute struct {
	Commands []ResponseCommandsModel `json:"commands"`
}

// DeviceResponseError : Struct for a generic Google Home Actions request
type DeviceResponseError struct {
	RequestID string               `json:"requestId"`
	Payload   ResponsePayloadError `json:"payload"`
}

// ResponsePayloadError : Struct for an DeviceRequest Input model
type ResponsePayloadError struct {
	ErrorCode string `json:"errorCode"`
}

// ResponseDeviceModel : Struct for an Payload Device model
type ResponseDeviceModel struct {
	ID              string                 `json:"id"`
	Type            string                 `json:"type"`
	Traits          []string               `json:"traits"`
	Name            DeviceNameModel        `json:"name"`
	WillReportState bool                   `json:"willReportState"`
	RoomHint        string                 `json:"roomHint"`
	DeviceInfo      DeviceInfo             `json:"deviceInfo"`
	CustomData      map[string]interface{} `json:"customData"`
	Attributes      map[string]interface{} `json:"attributes"`
}

// DeviceNameModel : Struct for a Payload Command model
type DeviceNameModel struct {
	DefaultNames []string `json:"defaultNames"`
	Name         string   `json:"name"`
	Nicknames    []string `json:"nicknames"`
}

// DeviceInfo : Struct for a Payload Command model
type DeviceInfo struct {
	Manufacturer string `json:"manufacturer"`
	Model        string `json:"model"`
	HwVersion    string `json:"hwVersion"`
	SwVersion    string `json:"swVersion"`
}

// LocalizedOption : Struct for a localized option
type LocalizedOption struct {
	Lang        string   `json:"lang"`
	NameSynonym []string `json:"name_synonym"`
}

// OptionElement : Struct for an list element option
type OptionElement struct {
	Key   string            `json:"key"`
	Names []LocalizedOption `json:"on"`
}

// SensorStateSync represents the structure of a sensor state
type SensorStateSync struct {
	Name                string      `json:"name"`
	NumericCapabilities NumericCaps `json:"numericCapabilities"`
}

// SensorState represents the structure of a sensor state
type SensorStateQuery struct {
	Name     string  `json:"name"`
	RawValue float32 `json:"rawValue"`
}

// NumericCaps represents the numeric capabilities of a sensor state
type NumericCaps struct {
	RawValueUnit string `json:"rawValueUnit"`
}

// DeviceProperties : Struct for a Command execution model
type DeviceProperties struct {
	ON                            bool               `json:"on"`
	Online                        bool               `json:"online"`
	Brightness                    int                `json:"brightness"`
	Color                         uint64             `json:"spectrumRgb"`
	ThermostatMode                string             `json:"thermostatMode,omitempty"`
	ThermostatTemperatureSetpoint float32            `json:"thermostatTemperatureSetpoint,omitempty"`
	ThermostatTemperatureAmbient  float32            `json:"thermostatTemperatureAmbient,omitempty"`
	ThermostatHumidityAmbient     float32            `json:"thermostatHumidityAmbient,omitempty"`
	TemperatureSetpointCelsius    float32            `json:"temperatureSetpointCelsius,omitempty"`
	TemperatureAmbientCelsius     float32            `json:"temperatureAmbientCelsius,omitempty"`
	HumidityAmbientPercent        float32            `json:"humidityAmbientPercent,omitempty"`
	CurrentSensorStateData        []SensorStateQuery `json:"currentSensorStateData,omitempty"`
}

// DevicePropertyColor : Struct for a Command execution model
type DevicePropertyColor struct {
	Name        string `json:"name"`
	SpectrumRGB int    `json:"spectrumRGB"`
}

// ResponseCommandsModel : Struct for a Command execution model
type ResponseCommandsModel struct {
	Ids    []string `json:"ids"`
	Status string   `json:"status"`
	//States    DeviceProperties `json:"states"`
	ErrorCode string `json:"errorCode"`
}
