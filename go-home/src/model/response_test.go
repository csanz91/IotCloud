package model_test

import (
	"encoding/json"
	"model"
	"os"
	"test"
	"testing"
)

func TestResponse1Parsing(t *testing.T) {

	var req model.DeviceResponseSync

	file, _ := os.Open("./data/sample_response1.json")
	dec := json.NewDecoder(file)

	err := dec.Decode(&req)

	// test if any issues decoding file
	test.Ok(t, err)

	// assert correct parsing
	test.Equals(t, "ff36a3cc-ec34-11e6-b1a0-64510650abcf", req.RequestID)
	test.Equals(t, "1836.15267389", req.Payload.AgentUserID)
	test.Equals(t, "123", req.Payload.Devices[0].ID)
	test.Equals(t, "action.devices.traits.OnOff", req.Payload.Devices[0].Traits[0])
	test.Equals(t, "My Outlet 1234", req.Payload.Devices[0].Name.DefaultNames[0])
	test.Equals(t, "Night light", req.Payload.Devices[0].Name.Name)
	test.Equals(t, false, req.Payload.Devices[0].WillReportState)
	test.Equals(t, "kitchen", req.Payload.Devices[0].RoomHint)
	test.Equals(t, "lights-out-inc", req.Payload.Devices[0].DeviceInfo.Manufacturer)
	test.Equals(t, 74, int(req.Payload.Devices[0].CustomData["fooValue"].(float64)))
	test.Equals(t, true, req.Payload.Devices[0].CustomData["barValue"].(bool))
	test.Equals(t, "foo", req.Payload.Devices[0].CustomData["bazValue"].(string))

	test.Equals(t, "456", req.Payload.Devices[1].ID)
	test.Equals(t, "action.devices.traits.ColorSpectrum", req.Payload.Devices[1].Traits[3])
	test.Equals(t, 2000, int(req.Payload.Devices[1].Attributes["temperatureMinK"].(float64)))
}

func TestResponse2Parsing(t *testing.T) {

	var req model.DeviceResponseQuery

	file, _ := os.Open("./data/sample_response2.json")
	dec := json.NewDecoder(file)

	err := dec.Decode(&req)

	// test if any issues decoding file
	test.Ok(t, err)

	// assert correct parsing
	test.Equals(t, "ff36a3cc-ec34-11e6-b1a0-64510650abcf", req.RequestID)
	test.Equals(t, true, req.Payload.Devices["123"].ON)
	test.Equals(t, true, req.Payload.Devices["123"].Online)

	test.Equals(t, true, req.Payload.Devices["456"].Online)
	test.Equals(t, 80, req.Payload.Devices["456"].Brightness)
	test.Equals(t, "cerulean", req.Payload.Devices["456"].Color.Name)
	test.Equals(t, 31655, req.Payload.Devices["456"].Color.SpectrumRGB)
}

func TestResponse3Parsing(t *testing.T) {

	var req model.DeviceResponseExecute

	file, _ := os.Open("./data/sample_response3.json")
	dec := json.NewDecoder(file)

	err := dec.Decode(&req)

	// test if any issues decoding file
	test.Ok(t, err)

	// assert correct parsing
	test.Equals(t, "ff36a3cc-ec34-11e6-b1a0-64510650abcf", req.RequestID)
	test.Equals(t, "123", req.Payload.Commands[0].Ids[0])
	test.Equals(t, "SUCCESS", req.Payload.Commands[0].Status)
	test.Equals(t, true, req.Payload.Commands[0].States.ON)
	test.Equals(t, true, req.Payload.Commands[0].States.Online)

	test.Equals(t, "456", req.Payload.Commands[1].Ids[0])
	test.Equals(t, "ERROR", req.Payload.Commands[1].Status)
	test.Equals(t, "deviceTurnedOff", req.Payload.Commands[1].ErrorCode)
}

func TestResponse4Parsing(t *testing.T) {

	var req model.DeviceResponseError

	file, _ := os.Open("./data/sample_response4.json")
	dec := json.NewDecoder(file)

	err := dec.Decode(&req)

	// test if any issues decoding file
	test.Ok(t, err)

	// assert correct parsing
	test.Equals(t, "ff36a3cc-ec34-11e6-b1a0-64510650abcf", req.RequestID)
	test.Equals(t, "notSupported", req.Payload.ErrorCode)
}
