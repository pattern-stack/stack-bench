package chat

import (
	"testing"

	"github.com/dugshub/agentic-tui/internal/sse"
)

func TestPartAccumulation_TextChunks(t *testing.T) {
	m := newTestModel()

	// Stream text in 3 chunks
	m.handleResponse(resp(sse.StreamChunk{Content: "Hello ", Type: sse.ChunkText}))
	m.handleResponse(resp(sse.StreamChunk{Content: "world", Type: sse.ChunkText}))
	m.handleResponse(resp(sse.StreamChunk{Done: true, Type: sse.ChunkText}))

	if len(m.messages) != 1 {
		t.Fatalf("expected 1 message, got %d", len(m.messages))
	}
	msg := m.messages[0]
	if msg.Role != RoleAssistant {
		t.Errorf("expected assistant role, got %v", msg.Role)
	}
	if len(msg.Parts) != 1 {
		t.Fatalf("expected 1 part, got %d", len(msg.Parts))
	}
	if msg.Parts[0].Type != PartText {
		t.Errorf("expected text part, got %s", msg.Parts[0].Type)
	}
	if msg.Parts[0].Content != "Hello world" {
		t.Errorf("expected 'Hello world', got %q", msg.Parts[0].Content)
	}
	if msg.Content() != "Hello world" {
		t.Errorf("Content() = %q, want 'Hello world'", msg.Content())
	}
}

func TestPartAccumulation_ThinkingThenText(t *testing.T) {
	m := newTestModel()

	m.handleResponse(resp(sse.StreamChunk{Content: "Let me think...", Type: sse.ChunkThinking}))
	m.handleResponse(resp(sse.StreamChunk{Content: "The answer is 42", Type: sse.ChunkText}))
	m.handleResponse(resp(sse.StreamChunk{Done: true, Type: sse.ChunkText}))

	msg := m.messages[0]
	if len(msg.Parts) != 2 {
		t.Fatalf("expected 2 parts, got %d", len(msg.Parts))
	}
	if msg.Parts[0].Type != PartThinking {
		t.Errorf("part 0: expected thinking, got %s", msg.Parts[0].Type)
	}
	if msg.Parts[1].Type != PartText {
		t.Errorf("part 1: expected text, got %s", msg.Parts[1].Type)
	}
}

func TestPartAccumulation_ToolCallStartEnd(t *testing.T) {
	m := newTestModel()

	// Text, then tool call, then more text
	m.handleResponse(resp(sse.StreamChunk{Content: "Let me read that file.", Type: sse.ChunkText}))
	m.handleResponse(resp(sse.StreamChunk{
		Type:        sse.ChunkToolStart,
		ToolCallID:  "tc-1",
		ToolName:    "read_file",
		DisplayType: "code",
		Arguments:   map[string]any{"path": "/tmp/foo.go"},
	}))
	m.handleResponse(resp(sse.StreamChunk{
		Type:       sse.ChunkToolEnd,
		ToolCallID: "tc-1",
		ToolName:   "read_file",
		Result:     "package main\nfunc main() {}",
		DurationMs: 42,
	}))
	m.handleResponse(resp(sse.StreamChunk{Content: "Here's the file.", Type: sse.ChunkText}))
	m.handleResponse(resp(sse.StreamChunk{Done: true, Type: sse.ChunkText}))

	msg := m.messages[0]
	if len(msg.Parts) != 3 {
		t.Fatalf("expected 3 parts (text, tool_call, text), got %d", len(msg.Parts))
	}

	// Part 0: text
	if msg.Parts[0].Type != PartText || msg.Parts[0].Content != "Let me read that file." {
		t.Errorf("part 0: got type=%s content=%q", msg.Parts[0].Type, msg.Parts[0].Content)
	}

	// Part 1: tool call
	tc := msg.Parts[1]
	if tc.Type != PartToolCall {
		t.Fatalf("part 1: expected tool_call, got %s", tc.Type)
	}
	if tc.ToolCall == nil {
		t.Fatal("part 1: ToolCall is nil")
	}
	if tc.ToolCall.ID != "tc-1" {
		t.Errorf("ToolCall.ID = %q, want 'tc-1'", tc.ToolCall.ID)
	}
	if tc.ToolCall.Name != "read_file" {
		t.Errorf("ToolCall.Name = %q, want 'read_file'", tc.ToolCall.Name)
	}
	if tc.ToolCall.DisplayType != "code" {
		t.Errorf("ToolCall.DisplayType = %q, want 'code'", tc.ToolCall.DisplayType)
	}
	if tc.ToolCall.State != ToolCallStateComplete {
		t.Errorf("ToolCall.State = %q, want 'complete'", tc.ToolCall.State)
	}
	if tc.ToolCall.Result != "package main\nfunc main() {}" {
		t.Errorf("ToolCall.Result = %q", tc.ToolCall.Result)
	}
	if tc.ToolCall.DurationMs != 42 {
		t.Errorf("ToolCall.DurationMs = %d, want 42", tc.ToolCall.DurationMs)
	}
	if !tc.Complete {
		t.Error("tool call part should be Complete after ChunkToolEnd")
	}

	// Part 2: text
	if msg.Parts[2].Type != PartText || msg.Parts[2].Content != "Here's the file." {
		t.Errorf("part 2: got type=%s content=%q", msg.Parts[2].Type, msg.Parts[2].Content)
	}
}

func TestPartAccumulation_ToolCallError(t *testing.T) {
	m := newTestModel()

	m.handleResponse(resp(sse.StreamChunk{
		Type:       sse.ChunkToolStart,
		ToolCallID: "tc-err",
		ToolName:   "bash",
		DisplayType: "bash",
	}))
	m.handleResponse(resp(sse.StreamChunk{
		Type:       sse.ChunkToolEnd,
		ToolCallID: "tc-err",
		ToolName:   "bash",
		ToolError:  "command not found",
		Result:     "",
	}))
	m.handleResponse(resp(sse.StreamChunk{Done: true, Type: sse.ChunkText}))

	tc := m.messages[0].Parts[0].ToolCall
	if tc.State != ToolCallStateError {
		t.Errorf("expected error state, got %s", tc.State)
	}
	if tc.Error != "command not found" {
		t.Errorf("expected error message, got %q", tc.Error)
	}
}

func TestPartAccumulation_ToolReject(t *testing.T) {
	m := newTestModel()

	m.handleResponse(resp(sse.StreamChunk{
		Type:     sse.ChunkToolReject,
		ToolName: "rm_rf",
		Content:  "tool not allowed",
	}))
	m.handleResponse(resp(sse.StreamChunk{Done: true, Type: sse.ChunkText}))

	msg := m.messages[0]
	if len(msg.Parts) != 1 {
		t.Fatalf("expected 1 part, got %d", len(msg.Parts))
	}
	if msg.Parts[0].Type != PartError {
		t.Errorf("expected error part, got %s", msg.Parts[0].Type)
	}
	if msg.Parts[0].Content != "Tool rejected: rm_rf: tool not allowed" {
		t.Errorf("content = %q", msg.Parts[0].Content)
	}
}

func TestPartAccumulation_MultipleToolCalls(t *testing.T) {
	m := newTestModel()

	// Two tool calls in sequence
	m.handleResponse(resp(sse.StreamChunk{
		Type: sse.ChunkToolStart, ToolCallID: "tc-1", ToolName: "read_file", DisplayType: "code",
	}))
	m.handleResponse(resp(sse.StreamChunk{
		Type: sse.ChunkToolEnd, ToolCallID: "tc-1", Result: "file contents",
	}))
	m.handleResponse(resp(sse.StreamChunk{
		Type: sse.ChunkToolStart, ToolCallID: "tc-2", ToolName: "edit_file", DisplayType: "diff",
	}))
	m.handleResponse(resp(sse.StreamChunk{
		Type: sse.ChunkToolEnd, ToolCallID: "tc-2", Result: "edit applied",
	}))
	m.handleResponse(resp(sse.StreamChunk{Done: true, Type: sse.ChunkText}))

	msg := m.messages[0]
	if len(msg.Parts) != 2 {
		t.Fatalf("expected 2 tool call parts, got %d", len(msg.Parts))
	}
	if msg.Parts[0].ToolCall.Name != "read_file" {
		t.Errorf("part 0: name = %q", msg.Parts[0].ToolCall.Name)
	}
	if msg.Parts[1].ToolCall.Name != "edit_file" {
		t.Errorf("part 1: name = %q", msg.Parts[1].ToolCall.Name)
	}
}

func TestRawMessage_BackwardCompat(t *testing.T) {
	msg := Message{Role: RoleAssistant, Raw: true, RawContent: "<pre>rendered</pre>"}
	if msg.Content() != "<pre>rendered</pre>" {
		t.Errorf("Content() = %q, want raw content", msg.Content())
	}
}

func TestTextMessage_Helper(t *testing.T) {
	msg := TextMessage(RoleUser, "hello")
	if msg.Role != RoleUser {
		t.Errorf("role = %v", msg.Role)
	}
	if msg.Content() != "hello" {
		t.Errorf("Content() = %q", msg.Content())
	}
	if len(msg.Parts) != 1 || msg.Parts[0].Type != PartText {
		t.Error("expected single text part")
	}
}

func TestRenderMessage_AllPartTypes(t *testing.T) {
	msg := Message{
		Role: RoleAssistant,
		Parts: []MessagePart{
			{Type: PartThinking, Content: "Hmm let me consider this carefully"},
			{Type: PartText, Content: "Here's what I found."},
			{Type: PartToolCall, ToolCall: &ToolCallPart{
				Name: "read_file", State: ToolCallStateComplete,
				DisplayType: "code", Result: "package main",
			}, Complete: true},
			{Type: PartError, Content: "something went wrong"},
		},
	}

	rendered := renderMessage(msg, 80, spinnerSet{}, true)
	if rendered == "" {
		t.Fatal("renderMessage returned empty string")
	}
	// Just verify it doesn't panic and produces output
	t.Logf("Rendered message:\n%s", rendered)
}

// --- helpers ---

func newTestModel() Model {
	return Model{}
}

func resp(chunk sse.StreamChunk) ResponseMsg {
	return ResponseMsg{Chunk: chunk}
}
