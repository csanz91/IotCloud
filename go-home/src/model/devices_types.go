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

// AnalogType : Google Device definition for our toogle types
var AnalogType = GoogleDeviceType{
	Type:   "action.devices.types.SENSOR",
	Traits: []string{"action.devices.traits.Sensor, action.devices.traits.SensorState"},
}

// GetGoogleDeviceType : From our device type get the Google characteristics
func GetGoogleDeviceType(apiType string) (GoogleDeviceType, error) {
	switch apiType {
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
