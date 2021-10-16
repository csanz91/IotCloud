package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"iotcloud"
	"model"
	"net/http"
	"net/http/httputil"
	"regexp"
	"strings"
)

type targetRequested struct {
	Type   string `json:"type"`
	Target string `json:"target"`
}

func (s *server) search(w http.ResponseWriter, r *http.Request) {
	requestDump, err := httputil.DumpRequest(r, true)
	if err != nil {
		fmt.Println(err)
	}
	fmt.Println(string(requestDump))

	// 1. Get the requested target
	var q bytes.Buffer
	_, err = q.ReadFrom(r.Body)
	if err != nil {
		model.ReturnAPIErrorProtocolError(w)
		return
	}

	target := &targetRequested{}
	err = json.Unmarshal(q.Bytes(), target)
	if err != nil {
		model.ReturnAPIErrorProtocolError(w)
		return
	}

	var targetsValues []iotcloud.Tag
	if target.Target != "" {
		// Get location sensors tags
		if strings.HasSuffix(target.Target, ".*") {
			var re = regexp.MustCompile(`(?m)LocationID:(\S*)\.SensorID\.\*`)
			for i, match := range re.FindAllStringSubmatch(target.Target, -1) {
				locationID := match[i+1]
				userTags, err := iotcloud.GetTags(r, locationID)
				if err != nil {
					logger.Println("Cannot get tags")
					model.ReturnAPIErrorProtocolError(w)
					return
				}
				targetsValues = userTags.SensorTags
				break
			}
			// Get generic tags
		} else {
			userTags, err := iotcloud.GetTags(r, "*")
			if err != nil {
				logger.Println("Cannot get tags")
				model.ReturnAPIErrorProtocolError(w)
				return
			}
			switch target.Target {
			case model.LocationID:
				targetsValues = userTags.LocationTags
			case model.DeviceID:
				targetsValues = userTags.DeviceTags
			case model.SensorID:
				targetsValues = userTags.SensorTags
			default:
				targetsValues = []iotcloud.Tag{}
			}
		}

	} else {
		// Generic search -> measurements available
		targetsValues = []iotcloud.Tag{
			iotcloud.Tag{
				Text:  model.Analog,
				Value: model.Analog,
			},
			iotcloud.Tag{
				Text:  model.SensorActions,
				Value: model.SensorActions,
			},
			iotcloud.Tag{
				Text:  model.LocationActions,
				Value: model.LocationActions,
			},
			iotcloud.Tag{
				Text:  model.LocationDevicesStatusStats,
				Value: model.LocationDevicesStatusStats,
			},
			iotcloud.Tag{
				Text:  model.LocationDeviceStatusStats,
				Value: model.LocationDeviceStatusStats,
			},
		}
	}

	resp, err := json.Marshal(targetsValues)
	if err != nil {
		writeError(w, err, "cannot marshal targets response")
	}
	w.Write(resp)
}
