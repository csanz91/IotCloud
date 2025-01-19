package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"main/iotcloud"
	"main/model"
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
type query struct {
	App         string `json:"app"`
	RequestID   string `json:"requestId"`
	Timezone    string `json:"timezone"`
	Range       struct {
		From string `json:"from"`
		To   string `json:"to"`
		Raw  struct {
			From string `json:"from"`
			To   string `json:"to"`
		} `json:"raw"`
	} `json:"range"`
	Interval      string `json:"interval"`
	IntervalMs    int    `json:"intervalMs"`
	Targets       []target `json:"targets"`
	MaxDataPoints int    `json:"maxDataPoints"`
	ScopedVars   map[string]Tag `json:"scopedVars"`
	StartTime    int64  `json:"startTime"`
	RangeRaw     struct {
		From string `json:"from"`
		To   string `json:"to"`
	} `json:"rangeRaw"`
	DashboardUID   string `json:"dashboardUID"`
	PanelID        int    `json:"panelId"`
	PanelPluginID  string `json:"panelPluginId"`
}

type target struct {
	Data       string `json:"data"`
	Datasource struct {
		Type string `json:"type"`
		UID  string `json:"uid"`
	} `json:"datasource"`
	EditorMode string `json:"editorMode"`
	Hide       bool   `json:"hide"`
	RefID      string `json:"refId"`
	Target     string `json:"target"`
	Type       string `json:"type"`
	Payload    struct {
		LocationID string `json:"locationID"`
		SensorID   string `json:"sensorId"`
	} `json:"payload"`
}

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
	Columns []column        `json:"columns"`
	Rows    [][]interface{} `json:"rows"`
	Type    string          `json:"type"`
}

func (s *server) query(w http.ResponseWriter, r *http.Request) {

	// requestDump, err := httputil.DumpRequest(r, true)
	// if err != nil {
	// 	fmt.Println(err)
	// }
	// fmt.Println(string(requestDump))

	if (*r).Method == "OPTIONS" {
		return
	}

	// 1. Get the token from the headers
	authToken, err := iotcloud.GetTokenFromHeaders(r)
	if err != nil {
		a := "11"
		w.WriteHeader(http.StatusUnauthorized)
		w.Write([]byte("{\"error\": \" Unauthorized: " + a + "\"}"))
		logger.Println(err)
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

	// Update for first target
	if len(query.Targets) == 0 {
		writeError(w, errors.New("no targets specified"), "Parameters error")
		return
	}

	// Validate locationID
	if query.Targets[0].Payload.LocationID == "" {
		writeError(w, errors.New("The location ID is required"), "Parameters error")
		return
	}

	// 5. Retrieve and return the data
	switch query.Targets[0].Type {
	case "timeseries":
		s.sendTimeseries(w, query, userID)
	case "table":
		s.sendTable(w, query, userID)
	default:
		http.Error(w, "Fall Through", http.StatusNotImplemented)
	}
}

func getDataPointsFromTarget(target string, q *query, userID string) ([][]interface{}, error) {
	locationID := q.Targets[0].Payload.LocationID
	sensorID := q.Targets[0].Payload.SensorID

	switch target {
	case model.Analog:
		return iotcloud.GetSensorData(
			userID,
			locationID,
			sensorID,
			q.Range.From,
			q.Range.To,
			q.MaxDataPoints)
	case model.SensorActions:
		return iotcloud.GetSensorActionData(
			userID,
			locationID,
			sensorID,
			q.Range.From,
			q.Range.To)
	case model.LocationActions:
		return iotcloud.GetLocationActionData(
			userID,
			locationID,
			q.Range.From,
			q.Range.To)
	case model.LocationDevicesStatusStats:
		return iotcloud.GetLocationDevicesStatusData(
			userID,
			locationID,
			q.Range.From,
			q.Range.To)
	case model.LocationDeviceStatusStats:
		return iotcloud.GetLocationDeviceStatus(
			userID,
			locationID,
			q.Targets[0].Payload.SensorID,
			q.Range.From,
			q.Range.To)
	case model.Notifications:
		return iotcloud.GetLocationNotifications(
			userID,
			locationID,
			q.Range.From,
			q.Range.To)
	}
	return nil, errors.New("Undefined target")
}

// sendTimeseries creates and writes a JSON response to a request for time series data.
func (s *server) sendTimeseries(w http.ResponseWriter, q *query, userID string) {

	response := []timeseriesResponse{}

	for _, t := range q.Targets {
		target := t.Target

		datapoints, err := getDataPointsFromTarget(target, q, userID)
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

func getColumnsFromTarget(target string) ([]column, error) {

	switch target {
	case model.LocationActions:
		columns := []column{
			column{
				Text: "Time",
				Type: "time",
			},
			column{
				Text: "Sensor",
				Type: "string",
			},
			column{
				Text: "Action",
				Type: "string",
			},
		}
		return columns, nil
	case model.SensorActions:
		columns := []column{
			column{
				Text: "Action",
				Type: "string",
			},
			column{
				Text: "Time",
				Type: "time",
			},
		}
		return columns, nil
	case model.LocationDevicesStatusStats:
		columns := []column{
			column{
				Text: "Time",
				Type: "time",
			},
			column{
				Text: "Sensors",
				Type: "string",
			},
			column{
				Text: "Reconnections",
				Type: "number",
			},
		}
		return columns, nil
	case model.LocationDeviceStatusStats:
		columns := []column{
			column{
				Text: "Status",
				Type: "string",
			},
			column{
				Text: "Time",
				Type: "time",
			},
		}
		return columns, nil
	case model.Notifications:
		columns := []column{
			{
				Text: "Time",
				Type: "time",
			},
			{
				Text: "Title",
				Type: "string",
			},
			{
				Text: "Message",
				Type: "string",
			},
		}
		return columns, nil
	}
	return nil, errors.New("Undefined target")
}

// sendTable creates and writes a JSON response to a request for table data
func (s *server) sendTable(w http.ResponseWriter, q *query, userID string) {

	response := []tableResponse{}

	for _, t := range q.Targets {
		target := t.Target

		datapoints, err := getDataPointsFromTarget(target, q, userID)
		if err != nil {
			writeError(w, err, "Cannot get metric for target "+target)
			return
		}

		columns, err := getColumnsFromTarget(target)
		if err != nil {
			writeError(w, err, "Cannot get metric for target "+target)
			return
		}

		response = append(response, tableResponse{
			Columns: columns,
			Rows:    datapoints,
			Type:    "table",
		})
	}

	jsonResp, err := json.Marshal(response)
	if err != nil {
		writeError(w, err, "cannot marshal table response")
	}

	w.Write(jsonResp)

}
