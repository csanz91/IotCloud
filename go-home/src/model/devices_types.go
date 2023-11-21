package model

import (
	"errors"
	"regexp"
)

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
	Type:       "action.devices.types.DOOR",
	Traits:     []string{"action.devices.traits.OpenClose"},
	Attributes: map[string]interface{}{"discreteOnlyOpenClose": true, "commandOnlyOpenClose": true},
}

// TvType : Google Device definition for our TV types
var TvType = GoogleDeviceType{
	Type: "action.devices.types.TV",
	Traits: []string{
		"action.devices.traits.InputSelector",
		"action.devices.traits.OnOff",
		"action.devices.traits.Volume",
		"action.devices.traits.TransportControl"},
	Attributes: map[string]interface{}{
		"commandOnlyVolume":        true,
		"commandOnlyOnOff":         true,
		"commandOnlyInputSelector": true,
		"volumeMaxLevel":           50,
		"volumeDefaultPercentage":  10,
		"transportControlSupportedCommands": []string{
			"PAUSE",
			"RESUME",
		},
		"availableInputs": OptionElement{
			Key: "HDMI",
			Names: []LocalizedOption{
				{
					Lang:        "en",
					NameSynonym: []string{"HDMI"},
				},
			},
		},
	},
}

// TempType : Google Device definition for our analog types (not working)
var TempType = GoogleDeviceType{
	Type: "action.devices.types.SENSOR",
	Traits: []string{
		"action.devices.traits.TemperatureControl",
	},
	Attributes: map[string]interface{}{
		"queryOnlyTemperatureControl": true,
		"temperatureUnitForUX":        "C",
	},
}

// HumType : Google Device definition for our analog types (not working)
var HumType = GoogleDeviceType{
	Type: "action.devices.types.SENSOR",
	Traits: []string{
		"action.devices.traits.HumiditySetting",
	},
	Attributes: map[string]interface{}{
		"queryOnlyHumiditySetting": true,
	},
}

// CO2Type : Google Device definition for our analog types (not working)
var CO2Type = GoogleDeviceType{
	Type: "action.devices.types.SENSOR",
	Traits: []string{
		"action.devices.traits.SensorState",
	},
	Attributes: map[string]interface{}{
		"sensorStatesSupported": []SensorStateSync{
			{
				Name: "CarbonMonoxideLevel",
				NumericCapabilities: NumericCaps{
					RawValueUnit: "PARTS_PER_MILLION",
				},
			},
		},
	},
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

const (
	NONE int = iota
	TEMP
	HUM
	CO2
)

// LEDType : Google Device definition for our LED type
var LEDType = GoogleDeviceType{
	Type:   "action.devices.types.LIGHT",
	Traits: []string{"action.devices.traits.OnOff", "action.devices.traits.Brightness"},
}

func GetAnalogSensorDataAttr(sensorID string) (int, error) {

	// Define a regular expression to match the CO2 part
	re := regexp.MustCompile(`_([^_]+)$`)

	// Find the matches
	matches := re.FindStringSubmatch(sensorID)

	var analogType = ""
	// Check if there is a match
	if len(matches) >= 2 {
		analogType = matches[1]
	} else {
		return NONE, errors.New("device type not correctly formatted")
	}

	switch analogType {
	case "T":
		return TEMP, nil
	case "H":
		return HUM, nil
	case "CO2":
		return CO2, nil
	default:
		return NONE, errors.New("device type not supported")
	}
}

// GetGoogleDeviceType : From our device type get the Google characteristics
func GetGoogleDeviceType(apiType string, sensorID string) (GoogleDeviceType, error) {
	switch apiType {
	case "analog":
		analogType, err := GetAnalogSensorDataAttr(sensorID)
		if err != nil {
			return GoogleDeviceType{}, err
		}
		switch analogType {
		case TEMP:
			return TempType, nil
		case HUM:
			return HumType, nil
		case CO2:
			return CO2Type, nil
		default:
			return AnalogType, nil
		}
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
		return GoogleDeviceType{}, errors.New("device type not supported")
	}
}
