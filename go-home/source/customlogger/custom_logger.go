package customlogger

import (
	"log"
	"os"
	"sync"
)

// LoggerModel : Logger model
type LoggerModel struct {
	filename string
	*log.Logger
}

var logger *LoggerModel
var once sync.Once

// GetInstance : start loggeando
func GetInstance() *LoggerModel {
	once.Do(func() {
		logger = createLogger("logs/main.log")
	})
	return logger
}

func createLogger(fname string) *LoggerModel {
	file, _ := os.OpenFile(fname, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0777)

	return &LoggerModel{
		filename: fname,
		Logger:   log.New(file, "", log.Ldate|log.Ltime|log.Lshortfile),
	}
}
