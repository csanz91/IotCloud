package dockersecret

import (
	"customlogger"
	"encoding/json"
	"errors"
	"io/ioutil"
	"os"
	"path"
)

var (
	logger = customlogger.GetInstance()
)

// ReadSecret : Read the docker secret passed
func ReadSecret(secretName string) (string, error) {

	secretsPath := path.Join(string(os.PathSeparator), "run", "secrets")
	files, err := ioutil.ReadDir(secretsPath)
	if err != nil {
		logger.Println("It was not possible to access the secrets path")
		return "", err
	}
	secretsFilePath := path.Join(secretsPath, files[0].Name())

	jsonFile, err := os.Open(secretsFilePath)
	// if we os.Open returns an error then handle it
	if err != nil {
		logger.Println("It was not possible to open the secrets file")
		return "", err
	}
	// defer the closing of our jsonFile so that we can parse it later on
	defer jsonFile.Close()

	byteValue, err := ioutil.ReadAll(jsonFile)
	if err != nil {
		logger.Println("It was not possible to parse the secrets file")
		return "", err
	}

	var result map[string]interface{}
	json.Unmarshal([]byte(byteValue), &result)

	secret := result[secretName]
	if secret == nil {
		logger.Printf("The secret: %s does not exists\n", secretName)
		return "", errors.New("The secret does not exists")
	}
	return secret.(string), nil
}
