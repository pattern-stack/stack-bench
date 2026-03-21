package api

import (
	"io"
	"strings"
	"testing"
)

func TestParseSSE_ValidEvents(t *testing.T) {
	input := "event: agent.message.chunk\ndata: {\"delta\":\"hello\"}\n\nevent: agent.message.complete\ndata: {\"content\":\"hello\",\"input_tokens\":10,\"output_tokens\":5}\n\n"

	body := io.NopCloser(strings.NewReader(input))
	ch := ParseSSE(body)

	events := collect(ch)
	if len(events) != 2 {
		t.Fatalf("expected 2 events, got %d", len(events))
	}

	if events[0].Event != "agent.message.chunk" {
		t.Errorf("event[0].Event = %q, want %q", events[0].Event, "agent.message.chunk")
	}
	if events[0].Data != `{"delta":"hello"}` {
		t.Errorf("event[0].Data = %q, want %q", events[0].Data, `{"delta":"hello"}`)
	}

	if events[1].Event != "agent.message.complete" {
		t.Errorf("event[1].Event = %q, want %q", events[1].Event, "agent.message.complete")
	}
}

func TestParseSSE_MultiLineData(t *testing.T) {
	input := "event: test\ndata: line1\ndata: line2\n\n"

	body := io.NopCloser(strings.NewReader(input))
	ch := ParseSSE(body)

	events := collect(ch)
	if len(events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(events))
	}
	if events[0].Data != "line1\nline2" {
		t.Errorf("Data = %q, want %q", events[0].Data, "line1\nline2")
	}
}

func TestParseSSE_IgnoresComments(t *testing.T) {
	input := ": this is a comment\nevent: test\ndata: {}\n\n"

	body := io.NopCloser(strings.NewReader(input))
	ch := ParseSSE(body)

	events := collect(ch)
	if len(events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(events))
	}
	if events[0].Event != "test" {
		t.Errorf("Event = %q, want %q", events[0].Event, "test")
	}
}

func TestChunkFromSSE_MessageChunk(t *testing.T) {
	evt := SSEEvent{
		Event: "agent.message.chunk",
		Data:  `{"delta":"world"}`,
	}
	chunk := ChunkFromSSE(evt)
	if chunk == nil {
		t.Fatal("expected non-nil chunk")
	}
	if chunk.Content != "world" {
		t.Errorf("Content = %q, want %q", chunk.Content, "world")
	}
	if chunk.Type != ChunkText {
		t.Errorf("Type = %q, want %q", chunk.Type, ChunkText)
	}
	if chunk.Done {
		t.Error("expected Done=false")
	}
}

func TestChunkFromSSE_MessageComplete_NoDuplication(t *testing.T) {
	evt := SSEEvent{
		Event: "agent.message.complete",
		Data:  `{"content":"full response","input_tokens":10,"output_tokens":5}`,
	}
	chunk := ChunkFromSSE(evt)
	if chunk == nil {
		t.Fatal("expected non-nil chunk")
	}
	if chunk.Content != "" {
		t.Errorf("Content = %q, want empty (content already streamed via chunks)", chunk.Content)
	}
	if !chunk.Done {
		t.Error("expected Done=true")
	}
}

func TestChunkFromSSE_Error(t *testing.T) {
	evt := SSEEvent{
		Event: "agent.error",
		Data:  `{"error_type":"rate_limit","message":"too many requests"}`,
	}
	chunk := ChunkFromSSE(evt)
	if chunk == nil {
		t.Fatal("expected non-nil chunk")
	}
	if !chunk.Done {
		t.Error("expected Done=true")
	}
	if chunk.Error == nil {
		t.Fatal("expected non-nil Error")
	}
	apiErr, ok := chunk.Error.(*APIError)
	if !ok {
		t.Fatalf("expected *APIError, got %T", chunk.Error)
	}
	if apiErr.Type != "rate_limit" {
		t.Errorf("error Type = %q, want %q", apiErr.Type, "rate_limit")
	}
}

func TestChunkFromSSE_Reasoning(t *testing.T) {
	for _, eventName := range []string{"agent.reasoning", "thinking"} {
		evt := SSEEvent{
			Event: eventName,
			Data:  `{"content":"let me think..."}`,
		}
		chunk := ChunkFromSSE(evt)
		if chunk == nil {
			t.Fatalf("[%s] expected non-nil chunk", eventName)
		}
		if chunk.Type != ChunkThinking {
			t.Errorf("[%s] Type = %q, want %q", eventName, chunk.Type, ChunkThinking)
		}
		if chunk.Content != "let me think..." {
			t.Errorf("[%s] Content = %q, want %q", eventName, chunk.Content, "let me think...")
		}
	}
}

func TestChunkFromSSE_ToolStart(t *testing.T) {
	for _, eventName := range []string{"agent.tool.start", "tool_start"} {
		evt := SSEEvent{
			Event: eventName,
			Data:  `{"tool_name":"search","input":"query"}`,
		}
		chunk := ChunkFromSSE(evt)
		if chunk == nil {
			t.Fatalf("[%s] expected non-nil chunk", eventName)
		}
		if chunk.Type != ChunkToolStart {
			t.Errorf("[%s] Type = %q, want %q", eventName, chunk.Type, ChunkToolStart)
		}
		if chunk.Content != "search" {
			t.Errorf("[%s] Content = %q, want %q", eventName, chunk.Content, "search")
		}
	}
}

func TestChunkFromSSE_ToolEnd(t *testing.T) {
	for _, eventName := range []string{"agent.tool.end", "tool_end"} {
		evt := SSEEvent{
			Event: eventName,
			Data:  `{"tool_name":"search","output":"found 3 results"}`,
		}
		chunk := ChunkFromSSE(evt)
		if chunk == nil {
			t.Fatalf("[%s] expected non-nil chunk", eventName)
		}
		if chunk.Type != ChunkToolEnd {
			t.Errorf("[%s] Type = %q, want %q", eventName, chunk.Type, ChunkToolEnd)
		}
		if chunk.Content != "found 3 results" {
			t.Errorf("[%s] Content = %q, want %q", eventName, chunk.Content, "found 3 results")
		}
	}
}

func TestChunkFromSSE_Done(t *testing.T) {
	evt := SSEEvent{Event: "done", Data: "{}"}
	chunk := ChunkFromSSE(evt)
	if chunk == nil {
		t.Fatal("expected non-nil chunk")
	}
	if !chunk.Done {
		t.Error("expected Done=true")
	}
}

func TestChunkFromSSE_UnknownEvent_ReturnsNil(t *testing.T) {
	evt := SSEEvent{Event: "unknown.event.type", Data: `{"foo":"bar"}`}
	chunk := ChunkFromSSE(evt)
	if chunk != nil {
		t.Errorf("expected nil for unknown event, got %+v", chunk)
	}
}

func TestChunkFromSSE_InvalidJSON_ReturnsNil(t *testing.T) {
	evt := SSEEvent{Event: "agent.message.chunk", Data: "not json"}
	chunk := ChunkFromSSE(evt)
	if chunk != nil {
		t.Errorf("expected nil for invalid JSON chunk, got %+v", chunk)
	}
}

func collect(ch <-chan SSEEvent) []SSEEvent {
	var events []SSEEvent
	for evt := range ch {
		events = append(events, evt)
	}
	return events
}
