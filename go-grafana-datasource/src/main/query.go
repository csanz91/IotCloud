package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"iotcloud"
	"model"
	"net/http"
)

// Anything to sort out /query can go here

type adhocFilters struct {
	Key      string `json:"key"`
	Operator string `json:"operator"`
	Value    string `json:"value"`
}

// Tag : Grafana tag structure.
type Tag struct {
	Text  string      `json:"text"`
	Value interface{} `json:"value"`
}

// query is a `/query` request from Grafana.
//
// All JSON-related structs were generated from the JSON examples
// of the "SimpleJson" data source documentation
// using [JSON-to-Go](https://mholt.github.io/json-to-go/),
// with a little tweaking afterwards.
type query struct {
	PanelID int `json:"panelId"`
	Range   struct {
		From string `json:"from"`
		To   string `json:"to"`
		Raw  struct {
			From string `json:"from"`
			To   string `json:"to"`
		} `json:"raw"`
	} `json:"range"`
	RangeRaw struct {
		From string `json:"from"`
		To   string `json:"to"`
	} `json:"rangeRaw"`
	Interval   string `json:"interval"`
	IntervalMs int    `json:"intervalMs"`
	Targets    []struct {
		Target string `json:"target"`
		RefID  string `json:"refId"`
		Type   string `json:"type"`
	} `json:"targets"`
	AdhocFilters  []adhocFilters `json:"adhocFilters"`
	Format        string         `json:"format"`
	MaxDataPoints int            `json:"maxDataPoints"`
	ScopedVars    map[string]Tag `json:"scopedVars"`
}

// row is used in timeseriesResponse and tableResponse.
// Grafana's JSON contains weird arrays with mixed types!
type row []interface{}

// column is used in tableResponse.
type column struct {
	Text string `json:"text"`
	Type string `json:"type"`
}

// timeseriesResponse is the response to a `/query` request
// if "Type" is set to "timeserie".
// It sends time series data back to Grafana.
type timeseriesResponse struct {
	Target     string          `json:"target"`
	Datapoints [][]interface{} `json:"datapoints"`
}

// tableResponse is the response to send when "Type" is "table".
type tableResponse struct {
	Columns []column `json:"columns"`
	Rows    []row    `json:"rows"`
	Type    string   `json:"type"`
}

func (s *server) query(w http.ResponseWriter, r *http.Request) {

	if (*r).Method == "OPTIONS" {
		return
	}

	// 1. Get the token from the headers
	authToken, err := iotcloud.GetTokenFromHeaders(r)
	if err != nil {
		a := "11"
		w.WriteHeader(http.StatusUnauthorized)
		w.Write([]byte("{\"error\": \" Unauthorized: " + a + "\"}"))
		return
	}
	// 2. Get the user ID
	userID, err := iotcloud.GetUserID(authToken)
	if err != nil {
		model.ReturnAPIErrorAuthFailure(w)
		return
	}

	// 3. Unmarshall the query
	var q bytes.Buffer

	_, err = q.ReadFrom(r.Body)
	if err != nil {
		model.ReturnAPIErrorProtocolError(w)
		return
	}

	query := &query{}
	err = json.Unmarshal(q.Bytes(), query)
	if err != nil {
		logger.Println(err)
		model.ReturnAPIErrorProtocolError(w)
		return
	}

	// 4. Retrieve the queried device
	d, err := getDeviceFromFilter(query.ScopedVars)
	if err != nil {
		writeError(w, err, "Parameters error")
		return
	}
	d.UserID = userID

	// 5. Retrieve and return the data
	switch query.Targets[0].Type {
	case "timeseries":
		s.sendTimeseries(w, query, d)
	case "table":
		http.Error(w, "Sorry not yet", http.StatusNotImplemented)

	default:
		http.Error(w, "Fall Through", http.StatusNotImplemented)
	}
}

func getDeviceFromFilter(filters map[string]Tag) (model.Device, error) {

	d := model.Device{}
	if value, ok := filters[model.LocationID]; ok {
		d.LocationID = value.Value.(string)
	} else {
		return model.Device{}, errors.New("The location ID is required")
	}
	if value, ok := filters[model.SensorID]; ok {
		d.SensorID = value.Value.(string)
	} else {
		return model.Device{}, errors.New("The sensor ID is required")
	}

	return d, nil
}

func getDataPointsFromTarget(target string, q *query, device model.Device) ([][]interface{}, error) {
	switch target {
	case model.Analog:
		datapoints, err := iotcloud.GetSensorData(
			device.UserID,
			device.LocationID,
			device.SensorID,
			q.Range.From,
			q.Range.To,
			q.MaxDataPoints)
		if err != nil {
			return nil, err
		}
		return datapoints, nil
	}
	return nil, errors.New("Undefined target")
}

// sendTimeseries creates and writes a JSON response to a request for time series data.
func (s *server) sendTimeseries(w http.ResponseWriter, q *query, device model.Device) {

	response := []timeseriesResponse{}

	for _, t := range q.Targets {
		target := t.Target

		datapoints, err := getDataPointsFromTarget(target, q, device)
		if err != nil {
			writeError(w, err, "Cannot get metric for target "+target)
			return
		}

		response = append(response, timeseriesResponse{
			Target:     target,
			Datapoints: datapoints,
		})
	}

	jsonResp, err := json.Marshal(response)
	if err != nil {
		writeError(w, err, "cannot marshal timeseries response")
	}

	w.Write(jsonResp)

}
