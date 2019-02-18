package iotcloud

import (
	"customlogger"
	"dockersecret"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"
)

var (
	authURL            = ""
	apiURL             = ""
	clientID           = ""
	clientSecret       = ""
	audience           = ""
	apiAuth            = Auth0Token{}
	logger             = customlogger.GetInstance()
	devicesCache       = map[string]deviceCacheModel{}
	tokensCache        = map[string]tokenCacheModel{}
	cacheMaxTime int64 = 3600
)

func init() {
	var err error
	authURL, err = dockersecret.ReadSecret("auth_url")
	if err != nil {
		logger.Fatalln("The auth url cannot be read")
	}
	apiURL, err = dockersecret.ReadSecret("api_url")
	if err != nil {
		logger.Fatalln("The api url cannot be read")
	}
	clientID, err = dockersecret.ReadSecret("client_id")
	if err != nil {
		logger.Fatalln("The client id cannot be read")
	}
	clientSecret, err = dockersecret.ReadSecret("client_secret")
	if err != nil {
		logger.Fatalln("The client id cannot be read")
	}
	audience, err = dockersecret.ReadSecret("audience")
	if err != nil {
		logger.Fatalln("The client id cannot be read")

	}
}

func getUserInfo(token string) (UserInfo, error) {

	req, err := http.NewRequest("GET", authURL+"userinfo", nil)
	if err != nil {
		return UserInfo{}, err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	response, err := http.DefaultClient.Do(req)
	if err != nil || response.StatusCode != http.StatusOK {
		logger.Printf("The HTTP request failed with error %s\n", err)
		logger.Printf("Status code %v\n", response.StatusCode)
		return UserInfo{}, errors.New("The HTTP request failed")
	}
	dfReq := UserInfo{}
	if dfErr := json.NewDecoder(response.Body).Decode(&dfReq); dfErr != nil {
		logger.Printf("The HTTP request cannot be decoded %s\n", dfErr)
		return UserInfo{}, errors.New("The HTTP request cannot be decoded")
	}
	return dfReq, nil
}

func getAPIToken() (Auth0Token, error) {

	postData := map[string]string{
		"client_id":     clientID,
		"client_secret": clientSecret,
		"audience":      audience,
		"grant_type":    "client_credentials",
	}
	postDataStr, err := json.Marshal(postData)
	if err != nil {
		logger.Println("Cannot serialize the post data")
		return Auth0Token{}, err
	}

	payload := strings.NewReader(string(postDataStr))
	req, err := http.NewRequest("POST", authURL+"oauth/token", payload)
	if err != nil {
		return Auth0Token{}, err
	}
	req.Header.Add("content-type", "application/json")
	response, err := http.DefaultClient.Do(req)
	if err != nil || response.StatusCode != http.StatusOK {
		logger.Printf("The HTTP request failed with error %s\n", err)
		logger.Printf("Status code %v\n", response.StatusCode)
		return Auth0Token{}, errors.New("The HTTP request failed")
	}

	dfReq := Auth0Token{}
	if dfErr := json.NewDecoder(response.Body).Decode(&dfReq); dfErr != nil {
		logger.Printf("The HTTP request cannot be decoded %s\n", dfErr)
		return Auth0Token{}, errors.New("The HTTP request cannot be decoded")
	}

	return dfReq, nil
}

func getDevices(userID string, disableCache bool) ([]Device, error) {

	currentTimestamp := time.Now().Unix()
	// Try to get the devices first from the cache
	if deviceCached, ok := devicesCache[userID]; ok {
		// If the cache is not expired
		if !disableCache && deviceCached.timestamp > currentTimestamp-cacheMaxTime {
			return deviceCached.Devices, nil
		}
	}

	maxRetries := 2
	for numRetries := 0; numRetries < maxRetries; numRetries++ {
		req, err := http.NewRequest("GET", apiURL+"users/"+userID+"/sensors", nil)
		if err != nil {
			return []Device{}, err
		}
		req.Header.Set("Authorization", "Bearer "+apiAuth.AccessToken)
		response, err := http.DefaultClient.Do(req)
		if err != nil || response.StatusCode != http.StatusOK {
			// Get a new token
			if response.StatusCode == http.StatusUnauthorized {
				newToken, err := getAPIToken()
				// If the token could not be retrieved abort
				if err != nil {
					break
				}
				// Set the new token and try again
				apiAuth = newToken
				continue
			}
			logger.Printf("The HTTP request failed with error %s\n", err)
			logger.Printf("Status code %v\n", response.StatusCode)
		}
		// Decode the response
		dfReq := APIResponse{}
		if dfErr := json.NewDecoder(response.Body).Decode(&dfReq); dfErr != nil {
			logger.Printf("The HTTP request cannot be decoded %s\n", dfErr)
			continue
		}
		// Save into the cache
		devicesCache[userID] = deviceCacheModel{
			timestamp: currentTimestamp,
			Devices:   dfReq.Data,
		}
		return dfReq.Data, nil
	}
	return []Device{}, errors.New("Cannot get the user devices")

}

func getUserID(token string) (string, error) {
	currentTimestamp := time.Now().Unix()
	// Try to get the devices first from the cache
	if tokenCached, ok := tokensCache[token]; ok {
		// If the cache is not expired
		if tokenCached.timestamp > currentTimestamp-cacheMaxTime {
			return tokenCached.UserID, nil
		}
	}
	userInfo, err := getUserInfo(token)
	if err != nil {
		return "", err
	}

	tokensCache[token] = tokenCacheModel{
		timestamp: currentTimestamp,
		UserID:    userInfo.Sub,
	}
	return userInfo.Sub, nil
}

// GetUserDevices : From an auth0 token, retrieve all the sensors associated
func GetUserDevices(token string, disableCache bool) ([]Device, string, error) {
	userID, err := getUserID(token)
	if err != nil {
		return nil, "", err
	}

	devices, err := getDevices(userID, disableCache)
	if err != nil {
		return nil, "", err
	}
	return devices, userID, nil
}

// UserInfo : Struct for the Auth0 userinfo response
type UserInfo struct {
	Sub           string `json:"sub"`
	Nickname      string `json:"nickname"`
	Name          string `json:"name"`
	Picture       string `json:"picture"`
	UpdatedAt     string `json:"updated_at"`
	Email         string `json:"email"`
	EmailVerified bool   `json:"email_verified"`
}

// Auth0Token : Struct for the Auth0 token response
type Auth0Token struct {
	AccessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
}

// APIResponse : Standar struct for the API response
type APIResponse struct {
	Result bool     `json:"result"`
	Data   []Device `json:"data"`
}

// Device : Standar struct for a device received through the API
type Device struct {
	DeviceID              string   `json:"deviceId"`
	RegistrationTimestamp int      `json:"utcDeviceFirstSeenTimestamp"`
	DeviceVersion         string   `json:"deviceVersion"`
	DeviceTargetVersion   string   `json:"deviceTargetVersion"`
	LocationID            string   `json:"locationId"`
	Sensors               []Sensor `json:"sensors"`
}

// Sensor : Standar struct for a sensor received through the API
type Sensor struct {
	ID       string                 `json:"sensorId"`
	Name     string                 `json:"sensorName"`
	Metadata map[string]interface{} `json:"sensorMetadata"`
	Type     string                 `json:"sensorType"`
}

type deviceCacheModel struct {
	timestamp int64
	Devices   []Device
}

type tokenCacheModel struct {
	timestamp int64
	UserID    string
}
