package main

import (
	"bytes"
	"encoding/json"
	"main/iotcloud"
	"main/model"
	"net/http"
	"regexp"
	"strings"
)

type timeRange struct {
	From string `json:"from"`
	To   string `json:"to"`
	Raw  struct {
		From string `json:"from"`
		To   string `json:"to"`
	} `json:"raw"`
}

type searchRequest struct {
	Payload struct {
		Target string `json:"target"`
	} `json:"payload"`
	Range timeRange `json:"range"`
}

type searchResponse struct {
	Text  string `json:"__text"`
	Value string `json:"__value"`
}

func (s *server) search(w http.ResponseWriter, r *http.Request) {
	// requestDump, err := httputil.DumpRequest(r, true)
	// if err != nil {
	// 	fmt.Println(err)
	// }
	// fmt.Println(string(requestDump))

	var q bytes.Buffer
	_, err := q.ReadFrom(r.Body)
	if err != nil {
		model.ReturnAPIErrorProtocolError(w)
		return
	}

	searchReq := &searchRequest{}
	err = json.Unmarshal(q.Bytes(), searchReq)
	if err != nil {
		model.ReturnAPIErrorProtocolError(w)
		return
	}

	var responseValues []searchResponse

	if strings.HasSuffix(searchReq.Payload.Target, ".*") {
		// Updated regex to be more explicit and capture the full ID
		var re = regexp.MustCompile(`LocationID:([\w\d]+)\.SensorID\.\*`)
		matches := re.FindAllStringSubmatch(searchReq.Payload.Target, -1)
		
		if len(matches) > 0 {
			locationID := matches[0][1]  // Changed to use first match, first capture group
			userTags, err := iotcloud.GetTags(r, locationID)
			if err != nil {
				logger.Println("Cannot get location tags for locationID: ", locationID)
				logger.Println(err)
				model.ReturnAPIErrorProtocolError(w)
				return
			}

			for _, tag := range userTags.SensorTags {
				responseValues = append(responseValues, searchResponse{
					Text:  tag.Text,
					Value: tag.Value,
				})
				}
			} else {
				logger.Println("No matches found for regex pattern")
				model.ReturnAPIErrorProtocolError(w)
				return
			}
	} else {
		userTags, err := iotcloud.GetTags(r, "*")
		if err != nil {
			logger.Println("Cannot get generic tags")
			logger.Println(err)
			model.ReturnAPIErrorProtocolError(w)
			return
		}
		var sourceTags []iotcloud.Tag
		switch searchReq.Payload.Target {
		case model.LocationID:
			sourceTags = userTags.LocationTags
		case model.DeviceID:
			sourceTags = userTags.DeviceTags
		case model.SensorID:
			sourceTags = userTags.SensorTags
		}
		for _, tag := range sourceTags {
			responseValues = append(responseValues, searchResponse{
				Text:  tag.Text,
				Value: tag.Value,
			})
		}
	}

	resp, err := json.Marshal(responseValues)
	if err != nil {
		writeError(w, err, "cannot marshal targets response")
		logger.Println("Cannot marshal targets response")
		return
	}
	w.Write(resp)
}
