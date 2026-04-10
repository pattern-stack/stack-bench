package contracttest

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

// ValidateStdioBackend runs a standard test suite against a JSON-RPC stdio backend.
// It spawns the given command and communicates via stdin/stdout.
func ValidateStdioBackend(t *testing.T, command string, args ...string) {
	t.Helper()

	cmd := exec.Command(command, args...)
	stdin, err := cmd.StdinPipe()
	if err != nil {
		t.Fatalf("stdin pipe: %v", err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatalf("stdout pipe: %v", err)
	}
	cmd.Stderr = nil // discard stderr

	if err := cmd.Start(); err != nil {
		t.Fatalf("start subprocess: %v", err)
	}
	defer func() {
		stdin.Close()
		done := make(chan error, 1)
		go func() { done <- cmd.Wait() }()
		select {
		case <-done:
		case <-time.After(5 * time.Second):
			_ = cmd.Process.Kill()
			<-done
		}
	}()

	scanner := bufio.NewScanner(stdout)
	scanner.Buffer(make([]byte, 0, 1024*1024), 1024*1024)

	var idSeq atomic.Int64

	send := func(method string, params interface{}) int64 {
		t.Helper()
		id := idSeq.Add(1)
		req := map[string]interface{}{
			"jsonrpc": "2.0",
			"method":  method,
			"id":      id,
		}
		if params != nil {
			req["params"] = params
		}
		data, err := json.Marshal(req)
		if err != nil {
			t.Fatalf("marshal request: %v", err)
		}
		if _, err := fmt.Fprintf(stdin, "%s\n", data); err != nil {
			t.Fatalf("write request: %v", err)
		}
		return id
	}

	readLine := func() map[string]interface{} {
		t.Helper()
		if !scanner.Scan() {
			if err := scanner.Err(); err != nil {
				t.Fatalf("read stdout: %v", err)
			}
			t.Fatal("unexpected EOF from subprocess")
		}
		var msg map[string]interface{}
		if err := json.Unmarshal(scanner.Bytes(), &msg); err != nil {
			t.Fatalf("unmarshal message: %v (line: %s)", err, scanner.Text())
		}
		return msg
	}

	readResponse := func(expectedID int64) map[string]interface{} {
		t.Helper()
		for {
			msg := readLine()
			// Skip notifications (no id)
			if _, hasID := msg["id"]; hasID {
				gotID, ok := msg["id"].(float64)
				if !ok {
					t.Fatalf("response id is not a number: %v", msg["id"])
				}
				if int64(gotID) != expectedID {
					t.Fatalf("response id = %v, want %d", gotID, expectedID)
				}
				return msg
			}
		}
	}

	// 1. listAgents
	var agentID string
	t.Run("listAgents", func(t *testing.T) {
		id := send("listAgents", nil)
		resp := readResponse(id)
		result, ok := resp["result"].([]interface{})
		if !ok || len(result) == 0 {
			t.Fatalf("expected non-empty agent list, got %v", resp["result"])
		}
		agent, ok := result[0].(map[string]interface{})
		if !ok {
			t.Fatalf("expected agent object, got %T", result[0])
		}
		agentID, _ = agent["id"].(string)
		if agentID == "" {
			t.Error("agent id is empty")
		}
	})

	if agentID == "" {
		t.Fatal("cannot continue without agent ID")
	}

	// 2. createConversation
	var convID string
	t.Run("createConversation", func(t *testing.T) {
		id := send("createConversation", map[string]string{"agent_id": agentID})
		resp := readResponse(id)
		result, ok := resp["result"].(map[string]interface{})
		if !ok {
			t.Fatalf("expected result object, got %v", resp["result"])
		}
		convID, _ = result["id"].(string)
		if convID == "" {
			t.Error("conversation id is empty")
		}
	})

	if convID == "" {
		t.Fatal("cannot continue without conversation ID")
	}

	// 3. sendMessage — collect notifications then final response
	t.Run("sendMessage", func(t *testing.T) {
		id := send("sendMessage", map[string]string{
			"conversation_id": convID,
			"content":         "Hello",
		})

		var gotDelta bool
		var gotDone bool
		var gotResponse bool

		deadline := time.After(10 * time.Second)
		for !gotResponse {
			// Check deadline in a non-blocking way
			select {
			case <-deadline:
				t.Fatal("timeout waiting for sendMessage response")
			default:
			}

			if !scanner.Scan() {
				if err := scanner.Err(); err != nil && err != io.EOF {
					t.Fatalf("read error: %v", err)
				}
				break
			}

			var msg map[string]interface{}
			if err := json.Unmarshal(scanner.Bytes(), &msg); err != nil {
				t.Fatalf("unmarshal: %v", err)
			}

			if _, hasID := msg["id"]; hasID {
				// This is the final response
				gotID := int64(msg["id"].(float64))
				if gotID != id {
					t.Errorf("response id = %d, want %d", gotID, id)
				}
				gotResponse = true
				continue
			}

			// It's a notification
			if method, _ := msg["method"].(string); method == "stream.event" {
				params, _ := msg["params"].(map[string]interface{})
				if params == nil {
					continue
				}
				evtType, _ := params["type"].(string)
				switch evtType {
				case "message.delta":
					gotDelta = true
				case "done":
					gotDone = true
				}
			}
		}

		if !gotDelta {
			t.Error("expected at least one message.delta notification")
		}
		if !gotDone {
			t.Error("expected a done notification")
		}
		if !gotResponse {
			t.Error("expected a final JSON-RPC response")
		}
	})
}

// readResponseSkipNotifications reads until a response with the given ID arrives.
// Used internally by ValidateStdioBackend.
func readResponseSkipNotifications(scanner *bufio.Scanner, expectedID int64) (map[string]interface{}, []map[string]interface{}, error) {
	var notifications []map[string]interface{}
	for scanner.Scan() {
		var msg map[string]interface{}
		if err := json.Unmarshal(scanner.Bytes(), &msg); err != nil {
			return nil, nil, err
		}
		if _, hasID := msg["id"]; hasID {
			return msg, notifications, nil
		}
		notifications = append(notifications, msg)
	}
	return nil, notifications, fmt.Errorf("EOF without response for id %d", expectedID)
}

// isNotification checks if a JSON-RPC message is a notification (no id field).
func isNotification(msg map[string]interface{}) bool {
	_, hasID := msg["id"]
	return !hasID && strings.Contains(fmt.Sprint(msg["method"]), "stream")
}
