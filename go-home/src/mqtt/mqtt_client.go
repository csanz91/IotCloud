package mqtt

import (
	"customlogger"
	"dockersecret"
	"errors"
	"strconv"
	"strings"

	//import the Paho Go MQTT library
	"os"

	MQTT "github.com/eclipse/paho.mqtt.golang"
)

var (
	mqttClient MQTT.Client
	sensors    = map[string]deviceValues{}
	logger     = customlogger.GetInstance()
)

//define a function for the default message handler
var f MQTT.MessageHandler = func(client MQTT.Client, msg MQTT.Message) {
	logger.Printf("TOPIC: %s\n", msg.Topic())
	logger.Printf("MSG: %s\n", msg.Payload())
}

var onStatus MQTT.MessageHandler = func(client MQTT.Client, msg MQTT.Message) {
	subtopics := strings.Split(msg.Topic(), "/") // 'v1/locationId/deviceId/status'

	status := strings.ToLower(string(msg.Payload())) == "online"
	device := sensors[subtopics[2]]
	device.Status = status
	sensors[subtopics[2]] = device
}

var onValue MQTT.MessageHandler = func(client MQTT.Client, msg MQTT.Message) {
	subtopics := strings.Split(msg.Topic(), "/") // 'v1/locationId/deviceId/sensorId/value'

	if value, err := strconv.ParseFloat(string(msg.Payload()), 32); err == nil {
		// Initialize the sensors map if it was empty
		if sensors[subtopics[2]].Sensors == nil {
			sensors[subtopics[2]] = deviceValues{
				Status:  sensors[subtopics[2]].Status,
				Sensors: map[string]sensorValues{},
			}
		}
		sensor := sensors[subtopics[2]].Sensors[subtopics[3]]
		sensor.Value = float32(value)
		sensors[subtopics[2]].Sensors[subtopics[3]] = sensor
	}
}

var onState MQTT.MessageHandler = func(client MQTT.Client, msg MQTT.Message) {
	subtopics := strings.Split(msg.Topic(), "/")

	if state, err := strconv.ParseBool(string(msg.Payload())); err == nil {
		// Initialize the sensors map if it was empty
		if sensors[subtopics[2]].Sensors == nil {
			sensors[subtopics[2]] = deviceValues{
				Status:  sensors[subtopics[2]].Status,
				Sensors: map[string]sensorValues{},
			}
		}
		sensor := sensors[subtopics[2]].Sensors[subtopics[3]]
		sensor.State = state
		sensors[subtopics[2]].Sensors[subtopics[3]] = sensor
	}
}

var onAux MQTT.MessageHandler = func(client MQTT.Client, msg MQTT.Message) {
	subtopics := strings.Split(msg.Topic(), "/")

	// Initialize the [Sensors] map if it was empty
	if sensors[subtopics[2]].Sensors == nil {
		sensors[subtopics[2]] = deviceValues{
			Status:  sensors[subtopics[2]].Status,
			Sensors: map[string]sensorValues{},
		}
	}
	// Initialize the [AuxValues] map if it was empty
	if sensors[subtopics[2]].Sensors[subtopics[3]].AuxValues == nil {
		sensor := sensors[subtopics[2]].Sensors[subtopics[3]]
		sensor.AuxValues = map[string]string{}
		sensors[subtopics[2]].Sensors[subtopics[3]] = sensor
	}

	sensor := sensors[subtopics[2]].Sensors[subtopics[3]]
	sensor.AuxValues[subtopics[len(subtopics)-1]] = string(msg.Payload())
	sensors[subtopics[2]].Sensors[subtopics[3]] = sensor
}

// Connect : Connect to the mqtt broken
func Connect() {
	//create a ClientOptions struct setting the broker address, clientid, turn
	//off trace output and set the default message handler
	// This should be replaced with env variables
	opts := MQTT.NewClientOptions().AddBroker("tcp://mosquitto:1883")
	opts.SetClientID("Home-Api")
	opts.SetDefaultPublishHandler(f)
	mqttToken, err := dockersecret.ReadSecret("token_homeapi")
	if err != nil {
		logger.Fatalln("The mqtt token cannot be read")
		return
	}
	opts.SetUsername(mqttToken)
	opts.SetPassword("_")
	opts.ConnectRetry = true
	opts.AutoReconnect = true

	opts.OnConnect = OnConnect

	opts.OnConnectionLost = func(cl MQTT.Client, err error) {
		logger.Println("Connection lost to MQTT broker")
	}
	opts.OnReconnecting = func(MQTT.Client, *MQTT.ClientOptions) {
		logger.Println("Attempting to reconnect to the MQTT broker")
	}

	//create and start a client using the above ClientOptions
	mqttClient = MQTT.NewClient(opts)

	if token := mqttClient.Connect(); token.Wait() && token.Error() != nil {
		logger.Panicf("The mqtt client could not connect. Error: %s\n", token.Error())
		panic(token.Error())
	}

}

func OnConnect(c MQTT.Client) {

	logger.Println("Connected to the MQTT broker")

	//subscribe to the topic /go-mqtt/sample and request messages to be delivered
	//at a maximum qos of zero, wait for the receipt to confirm the subscription
	if token := mqttClient.Subscribe("v1/+/+/+/value", 0, onValue); token.Wait() && token.Error() != nil {
		logger.Println(token.Error())
		os.Exit(1)
	}
	if token := mqttClient.Subscribe("v1/+/+/+/state", 2, onState); token.Wait() && token.Error() != nil {
		logger.Println(token.Error())
		os.Exit(1)
	}
	if token := mqttClient.Subscribe("v1/+/+/+/aux/+", 2, onAux); token.Wait() && token.Error() != nil {
		logger.Println(token.Error())
		os.Exit(1)
	}
	if token := mqttClient.Subscribe("v1/+/+/status", 2, onStatus); token.Wait() && token.Error() != nil {
		logger.Println(token.Error())
		os.Exit(1)
	}
}

// GetStatus : Gets the last status of the requested sensor
func GetStatus(deviceID string) (bool, error) {
	if device, ok := sensors[deviceID]; ok {
		return device.Status, nil
	}
	return false, errors.New("The status is not available")
}

// SetState : Sets the state of the requested sensor
func SetState(locationID, deviceID, sensorID string, newState bool) error {
	if mqttClient == nil || !mqttClient.IsConnected() {
		return errors.New("The mqtt client is not connected")
	}
	topic := "v1/" + locationID + "/" + deviceID + "/" + sensorID + "/setState"

	token := mqttClient.Publish(topic, 2, false, strconv.FormatBool(newState))
	token.Wait()
	return token.Error()
}

// SetAux : Sets an aux value for the requested sensor
func SetAux(locationID, deviceID, sensorID, endpoint, value string, retain bool) error {
	if mqttClient == nil || !mqttClient.IsConnected() {
		return errors.New("The mqtt client is not connected")
	}
	topic := "v1/" + locationID + "/" + deviceID + "/" + sensorID + "/aux/" + endpoint
	token := mqttClient.Publish(topic, 2, retain, value)
	token.Wait()
	return token.Error()
}

// GetValue : Gets the last value of the requested sensor
func GetValue(deviceID, sensorID string) (float32, error) {
	if device, ok := sensors[deviceID]; ok {
		if sensor, ok := device.Sensors[sensorID]; ok {
			return sensor.Value, nil
		}
	}
	return 0.0, errors.New("The value is not available")
}

// GetState : Gets the last state of the requested sensor
func GetState(deviceID, sensorID string) (bool, error) {
	if device, ok := sensors[deviceID]; ok {
		if sensor, ok := device.Sensors[sensorID]; ok {
			return sensor.State, nil
		}
	}
	return false, errors.New("The state is not available")
}

// GetAux : Gets the last aux values of the requested sensor
func GetAux(deviceID, sensorID string) (map[string]string, error) {
	if device, ok := sensors[deviceID]; ok {
		if sensor, ok := device.Sensors[sensorID]; ok {
			if sensor.AuxValues != nil {
				return sensor.AuxValues, nil
			}
		}
	}
	return nil, errors.New("The state is not available")
}

type deviceValues struct {
	Status  bool
	Sensors map[string]sensorValues
}

type sensorValues struct {
	Status    bool
	State     bool
	Value     float32
	AuxValues map[string]string
}
