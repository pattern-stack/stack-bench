package api

import (
	"bufio"
	"encoding/json"
	"io"
	"strings"
)

// ParseSSE reads an SSE stream and sends parsed events to the returned channel.
// The channel is closed when the stream ends or an error occurs.
// Unknown event types are silently forwarded — the consumer decides what to handle.
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
	}()
	return ch
}

// SSEChunkData is the JSON payload for agent.message.chunk events.
type SSEChunkData struct {
	Delta string `json:"delta"`
}

// SSEMessageCompleteData is the JSON payload for agent.message.complete events.
type SSEMessageCompleteData struct {
	Content      string `json:"content"`
	InputTokens  int    `json:"input_tokens"`
	OutputTokens int    `json:"output_tokens"`
}

// SSEErrorData is the JSON payload for error / agent.error events.
type SSEErrorData struct {
	ErrorType string `json:"error_type"`
	Message   string `json:"message"`
}

// ChunkFromSSE converts an SSE event into a StreamChunk.
// Returns nil for events we don't need to surface to the chat UI.
func ChunkFromSSE(evt SSEEvent) *StreamChunk {
	switch evt.Event {
	case "agent.message.chunk":
		var d SSEChunkData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return nil
		}
		return &StreamChunk{Content: d.Delta}

	case "agent.message.complete":
		var d SSEMessageCompleteData
		if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
			return &StreamChunk{Done: true}
		}
		return &StreamChunk{Content: d.Content, Done: true}

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
