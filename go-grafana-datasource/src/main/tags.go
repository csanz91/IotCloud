package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"iotcloud"
	"model"
	"net/http"
	"net/http/httputil"
)

type tagKeyResponse struct {
	KeyType string `json:"type"`
	Text    string `json:"text"`
}

type tagValueResponse struct {
	Text string `json:"text"`
}

type tagValueRequested struct {
	Key string `json:"key"`
}

func (s *server) tagKeys(w http.ResponseWriter, r *http.Request) {

	var targets = []tagKeyResponse{
		tagKeyResponse{"string", model.LocationID},
		tagKeyResponse{"string", model.SensorID},
	}
	resp, err := json.Marshal(targets)
	if err != nil {
		writeError(w, err, "cannot marshal targets response")
	}
	w.Write(resp)
}

func (s *server) tagValues(w http.ResponseWriter, r *http.Request) {

	requestDump, err := httputil.DumpRequest(r, true)
	if err != nil {
		fmt.Println(err)
	}
	fmt.Println(string(requestDump))

	if (*r).Method == "OPTIONS" {
		return
	}

	// 1. Get the requested key
	var q bytes.Buffer
	_, err = q.ReadFrom(r.Body)
	if err != nil {
		model.ReturnAPIErrorProtocolError(w)
		return
	}

	tagValueRequested := &tagValueRequested{}
	err = json.Unmarshal(q.Bytes(), tagValueRequested)
	if err != nil {
		model.ReturnAPIErrorProtocolError(w)
		return
	}

	// 2. Retrieve the user tags from the API
	tagsData, err := iotcloud.GetTags(r, "*")
	if err != nil {
		logger.Println("Cannot get tags")
		writeError(w, err, "API Error")
		return
	}

	// 3. Parse the tags and construct the response
	var tagsValues []iotcloud.Tag
	switch tagValueRequested.Key {
	case model.LocationID:
		tagsValues = tagsData.LocationTags
	case model.DeviceID:
		tagsValues = tagsData.DeviceTags
	case model.SensorID:
		tagsValues = tagsData.SensorTags
	default:
		tagsValues = []iotcloud.Tag{}
	}

	//4. Send the response
	jsonResp, err := json.Marshal(tagsValues)
	if err != nil {
		writeError(w, err, "cannot marshal timeseries response")
	}

	w.Write(jsonResp)
}
