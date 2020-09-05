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

// TvType : Google Device definition for our TV types
var TvType = GoogleDeviceType{
	Type: "action.devices.types.TV",
	Traits: []string{
		"action.devices.traits.InputSelector",
		"action.devices.traits.OnOff",
		"action.devices.traits.Volume",
		"action.devices.traits.TransportControl"},
}

// dataTypesSupported : Struct for a dataTypesSupported model
type dataTypesSupported struct {
	Name              string                 `json:"name"`
	DataType          map[string]interface{} `json:"data_type"`
	DefaultDeviceUnit string                 `json:"default_device_unit"`
}

// AnalogType : Google Device definition for our analog types (not working)
var AnalogType = GoogleDeviceType{
	Type: "action.devices.types.SENSOR",
	Traits: []string{
		"action.devices.traits.HumiditySetting",
		"action.devices.traits.TemperatureControl",
	},
	Attributes: map[string]interface{}{
		"queryOnlyHumiditySetting":    true,
		"queryOnlyTemperatureControl": true,
		"temperatureUnitForUX":        "C",
	},
}

// RGBType : Google Device definition for our RGB type
var RGBType = GoogleDeviceType{
	Type:       "action.devices.types.LIGHT",
	Traits:     []string{"action.devices.traits.OnOff", "action.devices.traits.Brightness", "action.devices.traits.ColorSetting"},
	Attributes: map[string]interface{}{"colorModel": "rgb", "commandOnlyColorSetting": false},
}

// LEDType : Google Device definition for our LED type
var LEDType = GoogleDeviceType{
	Type:   "action.devices.types.LIGHT",
	Traits: []string{"action.devices.traits.OnOff", "action.devices.traits.Brightness"},
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
	case "ledRGB":
		return RGBType, nil
	case "led":
		return LEDType, nil
	case "TV":
		return TvType, nil
	default:
		return GoogleDeviceType{}, errors.New("Device type not supported")
	}
}
