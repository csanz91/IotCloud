package main

import (
	"context"
	"fmt"
	"net/http"
	"sync"
)

type server struct {
	sync.RWMutex

	ctx context.Context
	i   int
}

func newServer() *server {
	return &server{ctx: context.Background()}
}

// root exists so that jsonds can be successfully added as a Grafana Data Source.
//
// If this exists then Grafana emits this when adding the datasource:
//
//	Success
//	Data source is working
//
// otherwise it emits "Unknown error"
func (s *server) root(w http.ResponseWriter, r *http.Request) {
	logger.Printf("%v: %v", r.URL.Path, r.Method)
	// requestDump, err := httputil.DumpRequest(r, true)
	// if err != nil {
	// 	fmt.Println(err)
	// }
	// fmt.Println(string(requestDump))
	fmt.Fprintf(w, "ok\n")
}

func (s *server) ok(w http.ResponseWriter, r *http.Request) {
	logger.Printf("%v: %v", r.URL.Path, r.Method)
	fmt.Fprintf(w, "ok\n")
}

func writeError(w http.ResponseWriter, e error, m string) {
	w.WriteHeader(http.StatusBadRequest)
	w.Write([]byte("{\"error\": \"" + m + ": " + e.Error() + "\"}"))
}
