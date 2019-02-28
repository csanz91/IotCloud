package model

import "errors"

// GoogleDeviceType : Google Device basic info
type GoogleDeviceType struct {
	Type       string
	Traits     []string
	Attributes map[string]interface{}
}

// SwitchType : Google Device definition for our digital types
var SwitchType = GoogleDeviceType{
	Type:   "action.devices.types.SWITCH",
	Traits: []string{"action.devices.traits.OnOff"},
}

// ThermostatType : Google Device definition for our thermostat types
var ThermostatType = GoogleDeviceType{
	Type:       "action.devices.types.THERMOSTAT",
	Traits:     []string{"action.devices.traits.TemperatureSetting"},
	Attributes: map[string]interface{}{"availableThermostatModes": "off,heat,on", "thermostatTemperatureUnit": "C"},
}

// ToogleType : Google Device definition for our toogle types
var ToogleType = GoogleDeviceType{
	Type:   "action.devices.types.DOOR",
	Traits: []string{"action.devices.traits.OpenClose"},
}

// dataTypesSupported : Struct for a dataTypesSupported model
type dataTypesSupported struct {
	Name              string                 `json:"name"`
	DataType          map[string]interface{} `json:"data_type"`
	DefaultDeviceUnit string                 `json:"default_device_unit"`
}

// AnalogType : Google Device definition for our toogle types
var AnalogType = GoogleDeviceType{
	Type:   "action.devices.types.SENSOR",
	Traits: []string{"action.devices.traits.Sensor"},
	Attributes: map[string]interface{}{"dataTypesSupported": []map[string]interface{}{
		{"name": "temperature",
			"data_type": []map[string]interface{}{
				{"type_synonym": []string{"temperature"}, "lang": "en"},
				{"type_synonym": []string{"temperatura"}, "lang": "es"}},
			"default_device_unit": "°C"},
		{"name": "humidity",
			"data_type": []map[string]interface{}{
				{"type_synonym": []string{"humidity"}, "lang": "en"},
				{"type_synonym": []string{"humedad"}, "lang": "es"}},
			"default_device_unit": "%"}}},
}

// GetGoogleDeviceType : From our device type get the Google characteristics
func GetGoogleDeviceType(apiType string) (GoogleDeviceType, error) {
	switch apiType {
	case "analog":
		return AnalogType, nil
	case "switch":
		return SwitchType, nil
	case "thermostat":
		return ThermostatType, nil
	case "toogle":
		return ToogleType, nil
	default:
		return GoogleDeviceType{}, errors.New("Device type not supported")
	}
}
