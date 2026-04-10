package contracttest

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// mockAgent is a minimal agent for testing.
type mockAgent struct {
	ID   string `json:"id"`
	Name string `json:"name"`
	Role string `json:"role"`
}

// TestValidateBackend_MockServer tests the ValidateBackend helper against
// a minimal net/http/httptest.Server that implements the contract.
func TestValidateBackend_MockServer(t *testing.T) {
	mux := http.NewServeMux()

	agents := []mockAgent{
		{ID: "test-agent", Name: "Test Agent", Role: "Testing"},
	}

	var lastConvID string

	// GET /agents
	mux.HandleFunc("GET /agents", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(agents)
	})

	// GET /health
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, `{"status":"ok"}`)
	})

	// POST /conversations
	mux.HandleFunc("POST /conversations", func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			AgentID string `json:"agent_id"`
		}
		json.NewDecoder(r.Body).Decode(&req)
		lastConvID = "conv-test-001"
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]string{
			"id":       lastConvID,
			"agent_id": req.AgentID,
		})
	})

	// POST /conversations/{id}/messages
	mux.HandleFunc("POST /conversations/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		// Check this is a /conversations/{id}/messages request
		if !strings.HasSuffix(r.URL.Path, "/messages") {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")
		w.WriteHeader(http.StatusOK)

		flusher, ok := w.(http.Flusher)
		if !ok {
			http.Error(w, "streaming not supported", http.StatusInternalServerError)
			return
		}

		// Send a message.delta event
		fmt.Fprint(w, "event: message.delta\ndata: {\"delta\":\"Hello \"}\n\n")
		flusher.Flush()

		fmt.Fprint(w, "event: message.delta\ndata: {\"delta\":\"world!\"}\n\n")
		flusher.Flush()

		// Send message.complete
		fmt.Fprint(w, "event: message.complete\ndata: {\"content\":\"Hello world!\",\"input_tokens\":10,\"output_tokens\":5}\n\n")
		flusher.Flush()
	})

	server := httptest.NewServer(mux)
	defer server.Close()

	ValidateBackend(t, server.URL)
}
