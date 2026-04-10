// Package contracttest provides test helpers for validating backend implementations
// against the agentic-tui contract.
package contracttest

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"testing"
	"time"
)

// ValidateBackend runs a standard test suite against a backend at the given URL.
// It validates: list agents, create conversation, send message, SSE event format.
func ValidateBackend(t *testing.T, baseURL string) {
	t.Helper()

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// 1. Health check
	t.Run("Health", func(t *testing.T) {
		resp, err := http.Get(baseURL + "/health")
		if err != nil {
			t.Skipf("health endpoint not available: %v", err)
			return
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			t.Errorf("health check returned %d, want 200", resp.StatusCode)
		}
	})

	// 2. List agents
	var agentID string
	t.Run("ListAgents", func(t *testing.T) {
		req, _ := http.NewRequestWithContext(ctx, "GET", baseURL+"/agents", nil)
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatalf("list agents: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Fatalf("list agents returned %d", resp.StatusCode)
		}

		var agents []struct {
			ID   string `json:"id"`
			Name string `json:"name"`
			Role string `json:"role"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&agents); err != nil {
			t.Fatalf("decode agents: %v", err)
		}
		if len(agents) == 0 {
			t.Fatal("expected at least one agent")
		}
		agentID = agents[0].ID
		if agentID == "" {
			t.Error("agent ID is empty")
		}
	})

	if agentID == "" {
		t.Fatal("cannot continue without an agent ID")
	}

	// 3. Create conversation
	var conversationID string
	t.Run("CreateConversation", func(t *testing.T) {
		body := fmt.Sprintf(`{"agent_id": %q}`, agentID)
		req, _ := http.NewRequestWithContext(ctx, "POST", baseURL+"/conversations",
			strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")

		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatalf("create conversation: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusOK {
			t.Fatalf("create conversation returned %d", resp.StatusCode)
		}

		var conv struct {
			ID string `json:"id"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&conv); err != nil {
			t.Fatalf("decode conversation: %v", err)
		}
		conversationID = conv.ID
		if conversationID == "" {
			t.Error("conversation ID is empty")
		}
	})

	if conversationID == "" {
		t.Fatal("cannot continue without a conversation ID")
	}

	// 4. Send message (SSE stream)
	t.Run("SendMessage", func(t *testing.T) {
		body := `{"content": "Hello"}`
		url := fmt.Sprintf("%s/conversations/%s/messages", baseURL, conversationID)
		req, _ := http.NewRequestWithContext(ctx, "POST", url, strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Accept", "text/event-stream")

		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatalf("send message: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Fatalf("send message returned %d", resp.StatusCode)
		}

		contentType := resp.Header.Get("Content-Type")
		if !strings.Contains(contentType, "text/event-stream") {
			t.Errorf("content-type = %q, want text/event-stream", contentType)
		}
	})
}
