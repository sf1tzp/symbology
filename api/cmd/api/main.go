package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/sf1tzp/symbology/api/internal/handlers"
)

func main() {
	port := os.Getenv("API_PORT")
	if port == "" {
		port = "8080"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", handlers.Health)

	addr := fmt.Sprintf(":%s", port)
	log.Printf("Starting API server on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
