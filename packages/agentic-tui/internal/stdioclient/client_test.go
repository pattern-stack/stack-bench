package stdioclient

import (
	"encoding/json"
	"testing"

	"github.com/dugshub/agentic-tui/internal/types"
)

func TestConvertStreamEvent_MessageDelta(t *testing.T) {
	params := StreamEventParams{
		Type: "message.delta",
		Data: json.RawMessage(`{"delta": "Hello "}`),
	}
	chunk := convertStreamEvent(params)
	if chunk == nil {
		t.Fatal("expected chunk, got nil")
	}
	if chunk.Content != "Hello " {
		t.Errorf("content = %q, want %q", chunk.Content, "Hello ")
	}
	if chunk.Type != types.ChunkText {
		t.Errorf("type = %q, want %q", chunk.Type, types.ChunkText)
	}
	if chunk.Done {
		t.Error("expected Done = false")
	}
}

func TestConvertStreamEvent_Thinking(t *testing.T) {
	params := StreamEventParams{
		Type: "thinking",
		Data: json.RawMessage(`{"content": "Let me consider..."}`),
	}
	chunk := convertStreamEvent(params)
	if chunk == nil {
		t.Fatal("expected chunk, got nil")
	}
	if chunk.Content != "Let me consider..." {
		t.Errorf("content = %q, want %q", chunk.Content, "Let me consider...")
	}
	if chunk.Type != types.ChunkThinking {
		t.Errorf("type = %q, want %q", chunk.Type, types.ChunkThinking)
	}
}

func TestConvertStreamEvent_ToolStart(t *testing.T) {
	params := StreamEventParams{
		Type: "tool.start",
		Data: json.RawMessage(`{"id": "tc-1", "name": "read_file", "input": "path=main.go", "display_type": "code"}`),
	}
	chunk := convertStreamEvent(params)
	if chunk == nil {
		t.Fatal("expected chunk, got nil")
	}
	if chunk.Type != types.ChunkToolStart {
		t.Errorf("type = %q, want %q", chunk.Type, types.ChunkToolStart)
	}
	if chunk.ToolCallID != "tc-1" {
		t.Errorf("ToolCallID = %q, want %q", chunk.ToolCallID, "tc-1")
	}
	if chunk.ToolName != "read_file" {
		t.Errorf("ToolName = %q, want %q", chunk.ToolName, "read_file")
	}
	if chunk.DisplayType != "code" {
		t.Errorf("DisplayType = %q, want %q", chunk.DisplayType, "code")
	}
}

func TestConvertStreamEvent_ToolEnd(t *testing.T) {
	params := StreamEventParams{
		Type: "tool.end",
		Data: json.RawMessage(`{"id": "tc-1", "name": "read_file", "output": "package main", "display_type": "code"}`),
	}
	chunk := convertStreamEvent(params)
	if chunk == nil {
		t.Fatal("expected chunk, got nil")
	}
	if chunk.Type != types.ChunkToolEnd {
		t.Errorf("type = %q, want %q", chunk.Type, types.ChunkToolEnd)
	}
	if chunk.Content != "package main" {
		t.Errorf("content = %q, want %q", chunk.Content, "package main")
	}
}

func TestConvertStreamEvent_Error(t *testing.T) {
	params := StreamEventParams{
		Type: "error",
		Data: json.RawMessage(`{"type": "rate_limit", "message": "Too many requests"}`),
	}
	chunk := convertStreamEvent(params)
	if chunk == nil {
		t.Fatal("expected chunk, got nil")
	}
	if !chunk.Done {
		t.Error("expected Done = true")
	}
	if chunk.Error == nil {
		t.Error("expected non-nil Error")
	}
}

func TestConvertStreamEvent_Done(t *testing.T) {
	params := StreamEventParams{
		Type: "done",
		Data: json.RawMessage(`{}`),
	}
	chunk := convertStreamEvent(params)
	if chunk == nil {
		t.Fatal("expected chunk, got nil")
	}
	if !chunk.Done {
		t.Error("expected Done = true")
	}
}

func TestConvertStreamEvent_Unknown(t *testing.T) {
	params := StreamEventParams{
		Type: "unknown_event",
		Data: json.RawMessage(`{}`),
	}
	chunk := convertStreamEvent(params)
	if chunk != nil {
		t.Error("expected nil for unknown event type")
	}
}

func TestRPCError(t *testing.T) {
	err := &RPCError{Code: -32601, Message: "Method not found"}
	if err.Error() != "JSON-RPC error -32601: Method not found" {
		t.Errorf("error string = %q", err.Error())
	}
}
