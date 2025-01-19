package iotcloud

import (
	"encoding/base64"
	"encoding/json"
	"errors"
	"main/customlogger"
	"main/dockersecret"
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
	tagsCache          = map[string]tagsCacheModel{}
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

func GetTokenFromHeaders(r *http.Request) (string, error) {
	// Retrieve the auth token. And get the token from the header
	authToken := r.Header.Get("X-Id-Token")
	if authToken == "" {
		return "", errors.New("The token could not be retrieved")
	}
	return authToken, nil
}

func GetAPIToken() (Auth0Token, error) {

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
				newToken, err := GetAPIToken()
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

type JWTClaims struct {
	Sub string `json:"sub"`
}

func GetUserID(token string) (string, error) {
	currentTimestamp := time.Now().Unix()
	// Try to get the user ID first from the cache
	if tokenCached, ok := tokensCache[token]; ok {
		// If the cache is not expired
		if tokenCached.timestamp > currentTimestamp-cacheMaxTime {
			return tokenCached.UserID, nil
		}
	}

	// Decode JWT token
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return "", errors.New("invalid token format")
	}

	// Decode the claims (second part of the token)
	claimJSON, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return "", err
	}

	var claims JWTClaims
	if err := json.Unmarshal(claimJSON, &claims); err != nil {
		return "", err
	}

	if claims.Sub == "" {
		return "", errors.New("no sub claim in token")
	}

	// Cache the result
	tokensCache[token] = tokenCacheModel{
		timestamp: currentTimestamp,
		UserID:    claims.Sub,
	}

	return claims.Sub, nil
}

func GetTags(r *http.Request, locationID string) (TagsData, error) {
	// 1. Get the token from the headers
	authToken, err := GetTokenFromHeaders(r)
	if err != nil {
		return TagsData{}, err
	}

	// 2. Get the user ID
	userID, err := GetUserID(authToken)
	if err != nil {
		return TagsData{}, err
	}

	// 4. Retrieve the user tags from the API
	tagsData, err := getUserTags(userID, locationID, false)
	if err != nil {
		logger.Println("Cannot get tags for the user: " + userID)
		return TagsData{}, err
	}

	return tagsData, nil
}

// GetUserDevices : From an auth0 token, retrieve all the sensors associated
func GetUserDevices(token string, disableCache bool) ([]Device, string, error) {
	userID, err := GetUserID(token)
	if err != nil {
		return nil, "", err
	}

	devices, err := getDevices(userID, disableCache)
	if err != nil {
		return nil, "", err
	}
	return devices, userID, nil
}

// GetSensorData :
func GetSensorData(userID, locationID, sensorID, from, to string, maxDataPoints int) ([][]interface{}, error) {

	postData := map[string]interface{}{
		"from":          from,
		"to":            to,
		"maxDataPoints": maxDataPoints,
	}
	postDataStr, err := json.Marshal(postData)
	if err != nil {
		logger.Println("Cannot serialize the post data")
		return nil, err
	}

	maxRetries := 2
	for numRetries := 0; numRetries < maxRetries; numRetries++ {
		payload := strings.NewReader(string(postDataStr))
		req, err := http.NewRequest("POST", apiURL+"users/"+userID+"/locations/"+locationID+"/m2msensorsdata/"+sensorID, payload)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+apiAuth.AccessToken)
		req.Header.Add("content-type", "application/json")
		response, err := http.DefaultClient.Do(req)
		if err != nil || response.StatusCode != http.StatusOK {
			// Get a new token
			if response.StatusCode == http.StatusUnauthorized {
				newToken, err := GetAPIToken()
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
		dfReq := APIDataResponse{}
		if dfErr := json.NewDecoder(response.Body).Decode(&dfReq); dfErr != nil {
			logger.Printf("The HTTP request cannot be decoded %s\n", dfErr)
			continue
		}
		return dfReq.Data, nil
	}

	return nil, errors.New("It was not possible to retrieve the data")
}

// GetSensorActionData :
func GetSensorActionData(userID, locationID, sensorID, from, to string) ([][]interface{}, error) {

	postData := map[string]interface{}{
		"from": from,
		"to":   to,
	}
	postDataStr, err := json.Marshal(postData)
	if err != nil {
		logger.Println("Cannot serialize the post data")
		return nil, err
	}

	maxRetries := 2
	for numRetries := 0; numRetries < maxRetries; numRetries++ {
		payload := strings.NewReader(string(postDataStr))
		req, err := http.NewRequest("POST", apiURL+"users/"+userID+"/locations/"+locationID+"/m2msensoractiondata/"+sensorID, payload)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+apiAuth.AccessToken)
		req.Header.Add("content-type", "application/json")
		response, err := http.DefaultClient.Do(req)
		if err != nil || response.StatusCode != http.StatusOK {
			// Get a new token
			if response.StatusCode == http.StatusUnauthorized {
				newToken, err := GetAPIToken()
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
		dfReq := APIDataResponse{}
		if dfErr := json.NewDecoder(response.Body).Decode(&dfReq); dfErr != nil {
			logger.Printf("The HTTP request cannot be decoded %s\n", dfErr)
			continue
		}
		return dfReq.Data, nil
	}

	return nil, errors.New("It was not possible to retrieve the data")
}

// GetLocationActionData :
func GetLocationActionData(userID, locationID, from, to string) ([][]interface{}, error) {

	postData := map[string]interface{}{
		"from": from,
		"to":   to,
	}
	postDataStr, err := json.Marshal(postData)
	if err != nil {
		logger.Println("Cannot serialize the post data")
		return nil, err
	}

	maxRetries := 2
	for numRetries := 0; numRetries < maxRetries; numRetries++ {
		payload := strings.NewReader(string(postDataStr))
		req, err := http.NewRequest("POST", apiURL+"users/"+userID+"/locations/"+locationID+"/m2mlocationactiondata", payload)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+apiAuth.AccessToken)
		req.Header.Add("content-type", "application/json")
		response, err := http.DefaultClient.Do(req)
		if err != nil || response.StatusCode != http.StatusOK {
			// Get a new token
			if response.StatusCode == http.StatusUnauthorized {
				newToken, err := GetAPIToken()
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
		dfReq := APIDataResponse{}
		if dfErr := json.NewDecoder(response.Body).Decode(&dfReq); dfErr != nil {
			logger.Printf("The HTTP request cannot be decoded %s\n", dfErr)
			continue
		}
		return dfReq.Data, nil
	}

	return nil, errors.New("It was not possible to retrieve the data")
}

// GetLocationDevicesStatusData :
func GetLocationDevicesStatusData(userID, locationID, from, to string) ([][]interface{}, error) {

	postData := map[string]interface{}{
		"from": from,
		"to":   to,
	}
	postDataStr, err := json.Marshal(postData)
	if err != nil {
		logger.Println("Cannot serialize the post data")
		return nil, err
	}

	maxRetries := 2
	for numRetries := 0; numRetries < maxRetries; numRetries++ {
		payload := strings.NewReader(string(postDataStr))
		req, err := http.NewRequest("POST", apiURL+"users/"+userID+"/locations/"+locationID+"/m2mdevicesstatusstats", payload)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+apiAuth.AccessToken)
		req.Header.Add("content-type", "application/json")
		response, err := http.DefaultClient.Do(req)
		if err != nil || response.StatusCode != http.StatusOK {
			// Get a new token
			if response.StatusCode == http.StatusUnauthorized {
				newToken, err := GetAPIToken()
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
		dfReq := APIDataResponse{}
		if dfErr := json.NewDecoder(response.Body).Decode(&dfReq); dfErr != nil {
			logger.Printf("The HTTP request cannot be decoded %s\n", dfErr)
			continue
		}
		return dfReq.Data, nil
	}

	return nil, errors.New("It was not possible to retrieve the data")
}

// GetLocationDeviceStatus :
func GetLocationDeviceStatus(userID, locationID, deviceID, from, to string) ([][]interface{}, error) {

	postData := map[string]interface{}{
		"from": from,
		"to":   to,
	}
	postDataStr, err := json.Marshal(postData)
	if err != nil {
		logger.Println("Cannot serialize the post data")
		return nil, err
	}

	maxRetries := 2
	for numRetries := 0; numRetries < maxRetries; numRetries++ {
		payload := strings.NewReader(string(postDataStr))
		req, err := http.NewRequest("POST", apiURL+"users/"+userID+"/locations/"+locationID+"/devices/"+deviceID+"/m2mstatus", payload)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+apiAuth.AccessToken)
		req.Header.Add("content-type", "application/json")
		response, err := http.DefaultClient.Do(req)
		if err != nil || response.StatusCode != http.StatusOK {
			// Get a new token
			if response.StatusCode == http.StatusUnauthorized {
				newToken, err := GetAPIToken()
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
		dfReq := APIDataResponse{}
		if dfErr := json.NewDecoder(response.Body).Decode(&dfReq); dfErr != nil {
			logger.Printf("The HTTP request cannot be decoded %s\n", dfErr)
			continue
		}
		return dfReq.Data, nil
	}

	return nil, errors.New("It was not possible to retrieve the data")
}

// NotificationData represents a single notification entry
type NotificationData struct {
    Time       string `json:"time"`
    Body       string `json:"body"`
    Title      string `json:"title"`
    LocationID string `json:"locationId"`
    SensorID   string `json:"sensorId"`
}

// APINotificationResponse represents the API response for notifications
type APINotificationResponse struct {
    Result bool              `json:"result"`
    Data   []NotificationData `json:"data"`
}

// GetLocationNotifications retrieves notifications for a location
func GetLocationNotifications(userID, locationID, from, to string) ([][]interface{}, error) {
    postData := map[string]interface{}{
        "from": from,
        "to":   to,
    }
    postDataStr, err := json.Marshal(postData)
    if err != nil {
        logger.Println("Cannot serialize the post data")
        return nil, err
    }

    maxRetries := 2
    for numRetries := 0; numRetries < maxRetries; numRetries++ {
        payload := strings.NewReader(string(postDataStr))
        req, err := http.NewRequest("POST", apiURL+"users/"+userID+"/locations/"+locationID+"/m2mnotifications", payload)
        if err != nil {
            return nil, err
        }
        req.Header.Set("Authorization", "Bearer "+apiAuth.AccessToken)
        req.Header.Add("content-type", "application/json")
        response, err := http.DefaultClient.Do(req)
        if err != nil || response.StatusCode != http.StatusOK {
            if response.StatusCode == http.StatusUnauthorized {
                newToken, err := GetAPIToken()
                if err != nil {
                    break
                }
                apiAuth = newToken
                continue
            }
            logger.Printf("The HTTP request failed with error %s\n", err)
            logger.Printf("Status code %v\n", response.StatusCode)
            continue
        }

        dfReq := APINotificationResponse{}
        if dfErr := json.NewDecoder(response.Body).Decode(&dfReq); dfErr != nil {
            logger.Printf("The HTTP request cannot be decoded %s\n", dfErr)
            continue
        }

        // Convert notifications to [][]interface{}
        result := make([][]interface{}, len(dfReq.Data))
        for i, notification := range dfReq.Data {
            result[i] = []interface{}{
                notification.Time,
                notification.Title,
                notification.Body,
                notification.LocationID,
                notification.SensorID,
            }
        }
        return result, nil
    }

    return nil, errors.New("It was not possible to retrieve the notifications")
}

func getUserTags(userID, locationID string, disableCache bool) (TagsData, error) {

	currentTimestamp := time.Now().Unix()
	// Try to get the devices first from the cache
	if tagsCached, ok := tagsCache[userID+locationID]; ok {
		// If the cache is not expired
		if !disableCache && tagsCached.timestamp > currentTimestamp-cacheMaxTime {
			logger.Println("Returning tags from cache")
			return tagsCached.Tags, nil
		}
	}

	maxRetries := 2
	for numRetries := 0; numRetries < maxRetries; numRetries++ {
		req, err := http.NewRequest("GET", apiURL+"users/"+userID+"/locations/"+locationID+"/tags", nil)
		if err != nil {
			return TagsData{}, err
		}
		req.Header.Set("Authorization", "Bearer "+apiAuth.AccessToken)
		response, err := http.DefaultClient.Do(req)
		if err != nil || response.StatusCode != http.StatusOK {
			// Get a new token
			if response.StatusCode == http.StatusUnauthorized {
				newToken, err := GetAPIToken()
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
		dfReq := APITagsResponse{}
		if dfErr := json.NewDecoder(response.Body).Decode(&dfReq); dfErr != nil {
			logger.Printf("The HTTP request cannot be decoded %s\n", dfErr)
			continue
		}
		// Save into the cache
		tagsCache[userID+locationID] = tagsCacheModel{
			timestamp: currentTimestamp,
			Tags:      dfReq.Data,
		}
		return dfReq.Data, nil
	}
	return TagsData{}, errors.New("Cannot get the user tags")

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

// Tag : ...
type Tag struct {
	Text  string `json:"text"`
	Value string `json:"value"`
}

// TagsData : ...
type TagsData struct {
	LocationTags []Tag `json:"locationTags"`
	DeviceTags   []Tag `json:"deviceTags"`
	SensorTags   []Tag `json:"sensorTags"`
}

// APIDataResponse : Standar struct for the API data response
type APIDataResponse struct {
	Result bool            `json:"result"`
	Data   [][]interface{} `json:"data"`
}

// APITagsResponse : Standar struct for the API tags response
type APITagsResponse struct {
	Result bool     `json:"result"`
	Data   TagsData `json:"data"`
}

// Device : Standard struct for a device received through the API
type Device struct {
	DeviceID              string   `json:"deviceId"`
	RegistrationTimestamp int      `json:"utcDeviceFirstSeenTimestamp"`
	DeviceVersion         string   `json:"deviceVersion"`
	DeviceTargetVersion   string   `json:"deviceTargetVersion"`
	LocationID            string   `json:"locationId"`
	Sensors               []Sensor `json:"sensors"`
}

// Sensor : Standard struct for a sensor received through the API
type Sensor struct {
	ID       string                 `json:"sensorId"`
	Name     string                 `json:"sensorName"`
	Metadata map[string]interface{} `json:"sensorMetadata"`
	Type     string                 `json:"sensorType"`
	Room     string                 `json:"room"`
}

type deviceCacheModel struct {
	timestamp int64
	Devices   []Device
}

type tokenCacheModel struct {
	timestamp int64
	UserID    string
}

type tagsCacheModel struct {
	timestamp int64
	Tags      TagsData
}
