package sse

import (
	"bufio"
	"encoding/json"
	"io"
	"strings"

	"github.com/dugshub/agentic-tui/internal/types"
)

// ParseSSE reads an SSE stream and sends parsed events to the returned channel.
// The channel is closed when the stream ends or an error occurs.
// Unknown event types are silently forwarded — the consumer decides what to handle.
func ParseSSE(body io.ReadCloser) <-chan types.SSEEvent {
	ch := make(chan types.SSEEvent, 16)
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
					ch <- types.SSEEvent{
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
			ch <- types.SSEEvent{Event: "error", Data: `{"error_type":"scan_error","message":"` + err.Error() + `"}`}
		}
	}()
	return ch
}

// ChunkFromSSE converts an SSE event into a StreamChunk.
// Returns nil for events we don't need to surface to the chat UI.
func ChunkFromSSE(evt types.SSEEvent) *types.StreamChunk {
	switch evt.Event {
	case "agent.message.chunk":
		var d SSEChunkData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return nil
		}
		return &types.StreamChunk{Content: d.Delta, Type: types.ChunkText}

	case "agent.message.complete":
		// Content was already streamed incrementally via chunks.
		// Only signal completion — do not repeat the full content.
		return &types.StreamChunk{Done: true, Type: types.ChunkText}

	case "agent.reasoning", "thinking":
		var d SSEReasoningData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return nil
		}
		return &types.StreamChunk{Content: d.Content, Type: types.ChunkThinking}

	case "agent.tool.start", "tool_start":
		var d SSEToolStartData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return nil
		}
		name := d.ToolName
		if name == "" {
			name = d.Input
		}
		return &types.StreamChunk{
			Content:     name,
			Type:        types.ChunkToolStart,
			ToolCallID:  d.ToolCallID,
			ToolName:    d.ToolName,
			DisplayType: d.DisplayType,
			Arguments:   d.Arguments,
		}

	case "agent.tool.end", "tool_end":
		var d SSEToolEndData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return nil
		}
		result := d.Output
		if r, ok := d.Result.(string); ok && result == "" {
			result = r
		}
		return &types.StreamChunk{
			Content:     result,
			Type:        types.ChunkToolEnd,
			ToolCallID:  d.ToolCallID,
			ToolName:    d.ToolName,
			DisplayType: d.DisplayType,
			Result:      result,
			ToolError:   d.Error,
			DurationMs:  d.DurationMs,
		}

	case "agent.tool.rejected":
		var d struct {
			ToolName string `json:"tool_name"`
			Reason   string `json:"reason"`
		}
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return nil
		}
		return &types.StreamChunk{
			Content:  d.Reason,
			Type:     types.ChunkToolReject,
			ToolName: d.ToolName,
		}

	case "agent.iteration.start", "agent.iteration.end":
		return &types.StreamChunk{Type: types.ChunkIteration}

	case "done":
		return &types.StreamChunk{Done: true, Type: types.ChunkText}

	case "agent.error", "error":
		var d SSEErrorData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return &types.StreamChunk{Content: "Error: unknown", Done: true, Error: io.ErrUnexpectedEOF}
		}
		return &types.StreamChunk{
			Content: "Error: " + d.Message,
			Done:    true,
			Error:   &types.APIError{Type: d.ErrorType, Msg: d.Message},
		}

	default:
		// Unknown events are silently ignored per spec
		return nil
	}
}
