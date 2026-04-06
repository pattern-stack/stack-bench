package chat

import (
	"errors"
	"testing"

	"github.com/dugshub/agent-tui/internal/sse"
)

func TestAccumulateText(t *testing.T) {
	m := New(nil, "test", nil, "ai:")
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkText, Content: "hello "}})
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkText, Content: "world"}})

	if len(m.messages) != 1 {
		t.Fatalf("expected 1 message, got %d", len(m.messages))
	}
	msg := m.messages[0]
	if msg.Role != RoleAssistant {
		t.Fatalf("expected RoleAssistant, got %d", msg.Role)
	}
	if len(msg.Parts) != 1 {
		t.Fatalf("expected 1 part, got %d", len(msg.Parts))
	}
	tp, ok := msg.Parts[0].(TextPart)
	if !ok {
		t.Fatalf("expected TextPart, got %T", msg.Parts[0])
	}
	if tp.Content != "hello world" {
		t.Errorf("Content = %q, want %q", tp.Content, "hello world")
	}
}

func TestAccumulateTextAfterToolCall(t *testing.T) {
	m := New(nil, "test", nil, "ai:")
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkText, Content: "before"}})
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkToolStart, ToolCallID: "tc1", ToolName: "search"}})
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkText, Content: "after"}})

	msg := m.messages[0]
	if len(msg.Parts) != 3 {
		t.Fatalf("expected 3 parts, got %d", len(msg.Parts))
	}
	if _, ok := msg.Parts[0].(TextPart); !ok {
		t.Errorf("part[0] expected TextPart, got %T", msg.Parts[0])
	}
	if _, ok := msg.Parts[1].(ToolCallPart); !ok {
		t.Errorf("part[1] expected ToolCallPart, got %T", msg.Parts[1])
	}
	if _, ok := msg.Parts[2].(TextPart); !ok {
		t.Errorf("part[2] expected TextPart, got %T", msg.Parts[2])
	}
}

func TestAccumulateThinking(t *testing.T) {
	m := New(nil, "test", nil, "ai:")
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkThinking, Content: "let me "}})
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkThinking, Content: "think..."}})

	msg := m.messages[0]
	if len(msg.Parts) != 1 {
		t.Fatalf("expected 1 part, got %d", len(msg.Parts))
	}
	tp, ok := msg.Parts[0].(ThinkingPart)
	if !ok {
		t.Fatalf("expected ThinkingPart, got %T", msg.Parts[0])
	}
	if tp.Content != "let me think..." {
		t.Errorf("Content = %q, want %q", tp.Content, "let me think...")
	}
}

func TestToolCallLifecycle(t *testing.T) {
	m := New(nil, "test", nil, "ai:")
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{
		Type:        sse.ChunkToolStart,
		ToolCallID:  "tc1",
		ToolName:    "search",
		DisplayType: "generic",
		ToolInput:   "query=foo",
	}})

	// Verify running state
	msg := m.messages[0]
	tc, ok := msg.Parts[0].(ToolCallPart)
	if !ok {
		t.Fatalf("expected ToolCallPart, got %T", msg.Parts[0])
	}
	if tc.State != ToolCallRunning {
		t.Errorf("State = %d, want ToolCallRunning", tc.State)
	}
	if tc.Input != "query=foo" {
		t.Errorf("Input = %q, want %q", tc.Input, "query=foo")
	}

	// Complete the tool call
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{
		Type:       sse.ChunkToolEnd,
		ToolCallID: "tc1",
		ToolName:   "search",
		Content:    "found 3 results",
	}})

	msg = m.messages[0]
	tc, ok = msg.Parts[0].(ToolCallPart)
	if !ok {
		t.Fatalf("expected ToolCallPart, got %T", msg.Parts[0])
	}
	if tc.State != ToolCallComplete {
		t.Errorf("State = %d, want ToolCallComplete", tc.State)
	}
	if tc.Result != "found 3 results" {
		t.Errorf("Result = %q, want %q", tc.Result, "found 3 results")
	}
}

func TestToolCallFailed(t *testing.T) {
	m := New(nil, "test", nil, "ai:")
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{
		Type:       sse.ChunkToolStart,
		ToolCallID: "tc1",
		ToolName:   "search",
	}})
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{
		Type:       sse.ChunkToolEnd,
		ToolCallID: "tc1",
		ToolName:   "search",
		ToolError:  "permission denied",
	}})

	msg := m.messages[0]
	tc, ok := msg.Parts[0].(ToolCallPart)
	if !ok {
		t.Fatalf("expected ToolCallPart, got %T", msg.Parts[0])
	}
	if tc.State != ToolCallFailed {
		t.Errorf("State = %d, want ToolCallFailed", tc.State)
	}
	if tc.Error != "permission denied" {
		t.Errorf("Error = %q, want %q", tc.Error, "permission denied")
	}
}

func TestToolCallUnmatchedEnd(t *testing.T) {
	m := New(nil, "test", nil, "ai:")
	// First create an assistant message with a tool call
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{
		Type:       sse.ChunkToolStart,
		ToolCallID: "tc1",
		ToolName:   "search",
	}})
	// Send tool end with a non-matching ID -- should not panic, should not modify anything
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{
		Type:       sse.ChunkToolEnd,
		ToolCallID: "nonexistent",
		ToolName:   "search",
		Content:    "result",
	}})

	msg := m.messages[0]
	// The original tool call should still be in Running state
	tc, ok := msg.Parts[0].(ToolCallPart)
	if !ok {
		t.Fatalf("expected ToolCallPart, got %T", msg.Parts[0])
	}
	if tc.State != ToolCallRunning {
		t.Errorf("State = %d, want ToolCallRunning (unmatched end should not modify)", tc.State)
	}
}

func TestErrorChunk(t *testing.T) {
	m := New(nil, "test", nil, "ai:")
	m.streaming = true
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{
		Error: errors.New("connection failed"),
	}})

	if m.streaming {
		t.Error("expected streaming=false after error")
	}
	if len(m.messages) != 1 {
		t.Fatalf("expected 1 message, got %d", len(m.messages))
	}
	msg := m.messages[0]
	if len(msg.Parts) != 1 {
		t.Fatalf("expected 1 part, got %d", len(msg.Parts))
	}
	ep, ok := msg.Parts[0].(ErrorPart)
	if !ok {
		t.Fatalf("expected ErrorPart, got %T", msg.Parts[0])
	}
	if ep.Message != "connection failed" {
		t.Errorf("Message = %q, want %q", ep.Message, "connection failed")
	}
}

func TestFinalizeRaw(t *testing.T) {
	m := New(nil, "test", nil, "ai:")
	m.streaming = true
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkThinking, Content: "hmm"}})
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkText, Content: "hello "}})
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkToolStart, ToolCallID: "tc1", ToolName: "x"}})
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkToolEnd, ToolCallID: "tc1", Content: "result"}})
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkText, Content: "world"}})
	m.handleResponse(ResponseMsg{Chunk: sse.StreamChunk{Type: sse.ChunkText, Done: true}})

	msg := m.messages[0]
	// Raw should contain only text parts, not thinking or tool results
	if msg.Raw != "hello world" {
		t.Errorf("Raw = %q, want %q", msg.Raw, "hello world")
	}
	if m.streaming {
		t.Error("expected streaming=false after Done")
	}
}

func TestContentMethod(t *testing.T) {
	// With Raw set
	msg := Message{Role: RoleAssistant, Raw: "from raw"}
	if msg.Content() != "from raw" {
		t.Errorf("Content() = %q, want %q", msg.Content(), "from raw")
	}

	// Without Raw, falls back to TextParts
	msg2 := Message{
		Role: RoleAssistant,
		Parts: []MessagePart{
			TextPart{Content: "hello "},
			ErrorPart{Message: "oops"},
			TextPart{Content: "world"},
		},
	}
	want := "hello Error: oopsworld"
	if msg2.Content() != want {
		t.Errorf("Content() = %q, want %q", msg2.Content(), want)
	}
}

func TestBackwardCompatUserMessage(t *testing.T) {
	msg := Message{Role: RoleUser, Raw: "user input"}
	if msg.Content() != "user input" {
		t.Errorf("Content() = %q, want %q", msg.Content(), "user input")
	}
}
