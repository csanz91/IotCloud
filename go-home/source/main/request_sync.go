package main

import (
	"dockersecret"
	"errors"
	"net/http"
	"strings"
)

var (
	googleHomegraphKey = ""
)

func init() {
	var err error
	googleHomegraphKey, err = dockersecret.ReadSecret("google_homegraph_key")
	if err != nil {
		logger.Fatalln("The google Homegraph key cannot be read")
	}
}

func requestResync() error {
	url := "https://homegraph.googleapis.com/v1/devices:requestSync?key=" + googleHomegraphKey
	payload := strings.NewReader("{\"agentUserId\":\"" + agentID + "\"}")
	req, err := http.NewRequest("POST", url, payload)
	if err != nil {
		return err
	}
	req.Header.Add("content-type", "application/json")
	response, err := http.DefaultClient.Do(req)
	if err != nil || response.StatusCode != http.StatusOK {
		logger.Printf("The HTTP request failed with error %s\n", err)
		logger.Printf("Status code %v\n", response.StatusCode)
		return errors.New("The HTTP request failed")
	}

	return nil
}
