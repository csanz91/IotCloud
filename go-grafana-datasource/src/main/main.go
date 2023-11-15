package main

import (
	"log"
	"main/customlogger"
	"net/http"
)

var (
	logger = customlogger.GetInstance()
)

func main() {

	logger.Println("Starting...")

	s := newServer()

	// Startup the server
	// initialize routes, and start http server
	http.HandleFunc("/", cors(s.root))
	http.HandleFunc("/search", cors(s.search))
	http.HandleFunc("/tag-keys", cors(s.tagKeys))
	http.HandleFunc("/tag-values", cors(s.tagValues))
	http.HandleFunc("/query", cors(s.query))
	http.HandleFunc("/ok", cors(s.ok))
	if err := http.ListenAndServe(":5002", nil); err != nil {
		log.Fatal(err)
	}
}
