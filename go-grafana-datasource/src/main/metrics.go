package main

import (
	"encoding/json"
	"main/model"
	"net/http"
)

type metricsRequest struct {
	Metric  string `json:"metric"`
	Payload struct {
		Cloud     string `json:"cloud"`
		Namespace string `json:"namespace"`
	} `json:"payload"`
}

type payloadOption struct {
	Label string `json:"label"`
	Value string `json:"value"`
}

type payloadField struct {
	Label        string         `json:"label,omitempty"`
	Name         string         `json:"name"`
	Type         string         `json:"type"`
	Placeholder  string         `json:"placeholder,omitempty"`
	ReloadMetric bool          `json:"reloadMetric,omitempty"`
	Width        int           `json:"width,omitempty"`
	Options      []payloadOption `json:"options,omitempty"`
}

type metricResponse struct {
	Label    string         `json:"label,omitempty"`
	Value    string         `json:"value"`
	Payloads []payloadField `json:"payloads"`
}

func (s *server) metrics(w http.ResponseWriter, r *http.Request) {
	metrics := []metricResponse{
		{
			Label: "Analog Values",
			Value: model.Analog,
			Payloads: sensorPayloads(),
		},
		{
			Label: "State Values",
			Value: model.State,
			Payloads: sensorPayloads(),
		},
		{
			Label: "Sensor Actions",
			Value: model.SensorActions,
			Payloads: sensorPayloads(),
		},
		{
			Label: "Location Actions",
			Value: model.LocationActions,
			Payloads: locationPayloads(),
		},
		{
			Label: "Location Devices Status Stats",
			Value: model.LocationDevicesStatusStats,
			Payloads: locationPayloads(),
		},
		{
			Label: "Location Device Status Stats",
			Value: model.LocationDeviceStatusStats,
			Payloads: locationPayloads(),
		},
		{
			Label: "Status",
			Value: model.Status,
			Payloads: sensorPayloads(),
		},
		{
			Label: "Totalizer",
			Value: model.Totalizer,
			Payloads: sensorPayloads(),
		},
		{
			Label: "Notifications",
			Value: model.Notifications,
			Payloads: locationPayloads(),
		},
	}

	resp, err := json.Marshal(metrics)
	if err != nil {
		writeError(w, err, "cannot marshal metrics response")
		return
	}
	w.Write(resp)
}

func sensorPayloads() []payloadField {
	return []payloadField{
		{
			Label: "Location ID",
			Name:  "LocationID",
			Type:  "select",
		},
		{
			Label: "Sensor ID", 
			Name:  "SensorID",
			Type:  "select",
		},
	}
}

func locationPayloads() []payloadField {
	return []payloadField{
		{
			Label: "Location ID",
			Name:  "LocationID",
			Type:  "select",
		},
	}
}

