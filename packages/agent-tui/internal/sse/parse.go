package sse

import (
	"bufio"
	"encoding/json"
	"io"
	"strings"
	"time"
)

// AgentSummary is a display DTO for an available agent.
type AgentSummary struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Role  string `json:"role"`
	Model string `json:"model,omitempty"`
}

// Conversation is a summary of a past conversation.
type Conversation struct {
	ID            string    `json:"id"`
	AgentID       string    `json:"agent_id"`
	State         string    `json:"state"`
	ExchangeCount int       `json:"exchange_count"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}

// ConversationDetail is the full conversation with message history.
type ConversationDetail struct {
	ID            string                `json:"id"`
	AgentID       string                `json:"agent_id"`
	State         string                `json:"state"`
	ExchangeCount int                   `json:"exchange_count"`
	Messages      []ConversationMessage `json:"messages"`
	CreatedAt     time.Time             `json:"created_at"`
	UpdatedAt     time.Time             `json:"updated_at"`
}

// ConversationMessage is a message within a conversation detail.
type ConversationMessage struct {
	ID       string        `json:"id"`
	Kind     string        `json:"kind"`
	Sequence int           `json:"sequence"`
	Parts    []MessagePart `json:"parts"`
}

// MessagePart is a part of a message.
type MessagePart struct {
	Type    string  `json:"type"`
	Content *string `json:"content,omitempty"`
}

// ChunkType identifies the kind of streaming event.
type ChunkType string

const (
	ChunkText      ChunkType = "text"
	ChunkThinking  ChunkType = "thinking"
	ChunkToolStart ChunkType = "tool_start"
	ChunkToolEnd   ChunkType = "tool_end"
)

// StreamChunk is a piece of a streaming response from the backend.
type StreamChunk struct {
	Content     string
	Type        ChunkType
	Done        bool
	Error       error
	ToolCallID  string
	ToolName    string
	DisplayType string
	ToolInput   string
	ToolError   string
}

// APIError represents an error returned by the backend API.
type APIError struct {
	Type string
	Msg  string
}

func (e *APIError) Error() string {
	return e.Type + ": " + e.Msg
}

// SSEEvent is a parsed Server-Sent Event.
type SSEEvent struct {
	Event string
	Data  string
}

// ParseSSE reads an SSE stream and sends parsed events to the returned channel.
// The channel is closed when the stream ends or an error occurs.
// Unknown event types are silently forwarded -- the consumer decides what to handle.
func ParseSSE(body io.ReadCloser) <-chan SSEEvent {
	ch := make(chan SSEEvent, 16)
	go func() {
		defer close(ch)
		defer body.Close()

		scanner := bufio.NewScanner(body)
		var event, data strings.Builder

		for scanner.Scan() {
			line := scanner.Text()

			if line == "" {
				// Empty line = event boundary
				if data.Len() > 0 {
					ch <- SSEEvent{
						Event: strings.TrimSpace(event.String()),
						Data:  strings.TrimSpace(data.String()),
					}
				}
				event.Reset()
				data.Reset()
				continue
			}

			if strings.HasPrefix(line, "event: ") {
				event.WriteString(strings.TrimPrefix(line, "event: "))
			} else if strings.HasPrefix(line, "data: ") {
				if data.Len() > 0 {
					data.WriteByte('\n')
				}
				data.WriteString(strings.TrimPrefix(line, "data: "))
			}
			// Ignore comments (lines starting with ':') and unknown prefixes
		}

		if err := scanner.Err(); err != nil {
			ch <- SSEEvent{Event: "error", Data: `{"error_type":"scan_error","message":"` + err.Error() + `"}`}
		}
	}()
	return ch
}

// SSEChunkData is the JSON payload for message delta events.
type SSEChunkData struct {
	Delta string `json:"delta"`
}

// SSEMessageCompleteData is the JSON payload for message complete events.
type SSEMessageCompleteData struct {
	Content      string `json:"content"`
	InputTokens  int    `json:"input_tokens"`
	OutputTokens int    `json:"output_tokens"`
}

// SSEReasoningData is the JSON payload for reasoning/thinking events.
type SSEReasoningData struct {
	Content string `json:"content"`
}

// SSEToolStartData is the JSON payload for tool start events.
type SSEToolStartData struct {
	ToolCallID  string `json:"tool_call_id"`
	ToolName    string `json:"tool_name"`
	Input       string `json:"input"`
	DisplayType string `json:"display_type"`
}

// SSEToolEndData is the JSON payload for tool end events.
type SSEToolEndData struct {
	ToolCallID  string `json:"tool_call_id"`
	ToolName    string `json:"tool_name"`
	Output      string `json:"output"`
	Error       string `json:"error"`
	DisplayType string `json:"display_type"`
	DurationMs  int    `json:"duration_ms"`
}

// SSEErrorData is the JSON payload for error events.
type SSEErrorData struct {
	ErrorType string `json:"error_type"`
	Message   string `json:"message"`
}

// ChunkFromSSE converts an SSE event into a StreamChunk.
// Returns nil for events we don't need to surface to the chat UI.
func ChunkFromSSE(evt SSEEvent) *StreamChunk {
	switch evt.Event {
	// Text delta: legacy "agent.message.chunk" and canonical "message.delta"
	case "agent.message.chunk", "message.delta":
		var d SSEChunkData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return nil
		}
		return &StreamChunk{Content: d.Delta, Type: ChunkText}

	// Message complete: legacy "agent.message.complete" and canonical "message.complete"
	case "agent.message.complete", "message.complete":
		// Content was already streamed incrementally via chunks.
		// Only signal completion -- do not repeat the full content.
		return &StreamChunk{Done: true, Type: ChunkText}

	// Thinking/reasoning: legacy "agent.reasoning" and canonical "thinking"
	case "agent.reasoning", "thinking":
		var d SSEReasoningData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return nil
		}
		return &StreamChunk{Content: d.Content, Type: ChunkThinking}

	// Tool start: legacy "agent.tool.start", alt "tool_start", and canonical "tool.start"
	case "agent.tool.start", "tool_start", "tool.start":
		var d SSEToolStartData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return nil
		}
		return &StreamChunk{
			Content:     d.ToolName,
			Type:        ChunkToolStart,
			ToolCallID:  d.ToolCallID,
			ToolName:    d.ToolName,
			DisplayType: d.DisplayType,
			ToolInput:   d.Input,
		}

	// Tool end: legacy "agent.tool.end", alt "tool_end", and canonical "tool.end"
	case "agent.tool.end", "tool_end", "tool.end":
		var d SSEToolEndData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return nil
		}
		return &StreamChunk{
			Content:     d.Output,
			Type:        ChunkToolEnd,
			ToolCallID:  d.ToolCallID,
			ToolName:    d.ToolName,
			DisplayType: d.DisplayType,
			ToolError:   d.Error,
		}

	case "done":
		return &StreamChunk{Done: true, Type: ChunkText}

	// Error: legacy "agent.error" and canonical "error"
	case "agent.error", "error":
		var d SSEErrorData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return &StreamChunk{Content: "Error: unknown", Done: true, Error: io.ErrUnexpectedEOF}
		}
		return &StreamChunk{
			Content: "Error: " + d.Message,
			Done:    true,
			Error:   &APIError{Type: d.ErrorType, Msg: d.Message},
		}

	default:
		// Unknown events are silently ignored per spec
		return nil
	}
}
