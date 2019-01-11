package model

import "errors"

// GoogleDeviceType : Google Device basic info
type GoogleDeviceType struct {
	Type       string
	Traits     []string
	Attributes map[string]interface{}
}

// DigitalType : Google Device definition for our digital types
var DigitalType = GoogleDeviceType{
	Type:   "action.devices.types.SWITCH",
	Traits: []string{"action.devices.traits.OnOff"},
}

// ThermostatType : Google Device definition for our thermostat types
var ThermostatType = GoogleDeviceType{
	Type:       "action.devices.types.THERMOSTAT",
	Traits:     []string{"action.devices.traits.TemperatureSetting"},
	Attributes: map[string]interface{}{"availableThermostatModes": "off,heat,on", "thermostatTemperatureUnit": "C"},
}

// GetGoogleDeviceType : From our device type get the Google characteristics
func GetGoogleDeviceType(apiType string) (GoogleDeviceType, error) {
	switch apiType {
	case "digital":
		return DigitalType, nil
	case "thermostat":
		return ThermostatType, nil
	default:
		return GoogleDeviceType{}, errors.New("Device type not supported")
	}
}
