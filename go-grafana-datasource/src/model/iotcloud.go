package model

const (
	Analog                     = "analog"
	State                      = "state"
	SensorActions              = "sensorActions"
	LocationActions            = "locationActions"
	LocationDevicesStatusStats = "locationDevicesStatusStats"
	LocationDeviceStatusStats  = "locationDeviceStatusStats"
	Status                     = "status"
	Totalizer                  = "totalizer"
	LocationID                 = "LocationID"
	DeviceID                   = "DeviceID"
	SensorID                   = "SensorID"
)

// Device : Stores the information to identify the device
type Device struct {
	UserID     string
	LocationID string
	DeviceID   string
	SensorID   string
}
