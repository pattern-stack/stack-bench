package cliclient

import (
	"encoding/json"
	"strings"

	"github.com/dugshub/agentic-tui/internal/types"
)

// ClaudeParser parses Claude CLI's --output-format stream-json output.
type ClaudeParser struct{}

// claudeEvent is the top-level event from Claude's stream-json output.
type claudeEvent struct {
	Type    string          `json:"type"`
	Subtype string          `json:"subtype,omitempty"`
	Event   json.RawMessage `json:"event,omitempty"`
	Message json.RawMessage `json:"message,omitempty"`
	// For result events
	Result json.RawMessage `json:"result,omitempty"`
	// For system.init
	SessionID string `json:"session_id,omitempty"`
}

// claudeInnerEvent is the "event" field inside a stream_event.
type claudeInnerEvent struct {
	Type         string          `json:"type"`
	ContentBlock json.RawMessage `json:"content_block,omitempty"`
	Delta        json.RawMessage `json:"delta,omitempty"`
	Index        int             `json:"index,omitempty"`
}

type claudeContentBlock struct {
	Type string `json:"type"`
	ID   string `json:"id,omitempty"`
	Name string `json:"name,omitempty"`
}

type claudeDelta struct {
	Type     string `json:"type"`
	Text     string `json:"text,omitempty"`
	Thinking string `json:"thinking,omitempty"`
}

// claudeAssistantMessage represents the assistant message with tool results.
type claudeAssistantMessage struct {
	Content []claudeContentPart `json:"content"`
}

type claudeContentPart struct {
	Type      string      `json:"type"`
	ToolUseID string      `json:"tool_use_id,omitempty"`
	Content   interface{} `json:"content,omitempty"`
	IsError   bool        `json:"is_error,omitempty"`
}

type claudeTextContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

// ParseLine parses a single JSONL line from Claude CLI output.
func (p *ClaudeParser) ParseLine(line []byte) []types.StreamChunk {
	var event claudeEvent
	if err := json.Unmarshal(line, &event); err != nil {
		return nil
	}

	switch event.Type {
	case "system":
		// system.init — ignore (session management not needed)
		return nil

	case "stream_event":
		return p.parseStreamEvent(event.Event)

	case "assistant":
		return p.parseAssistantMessage(event.Message)

	case "result":
		// Final result — we emit Done after process exits, so ignore
		return nil

	default:
		return nil
	}
}

func (p *ClaudeParser) parseStreamEvent(raw json.RawMessage) []types.StreamChunk {
	if raw == nil {
		return nil
	}

	var inner claudeInnerEvent
	if err := json.Unmarshal(raw, &inner); err != nil {
		return nil
	}

	switch inner.Type {
	case "content_block_delta":
		return p.parseDelta(inner.Delta)

	case "content_block_start":
		return p.parseContentBlockStart(inner.ContentBlock)

	case "content_block_stop", "message_start", "message_delta", "message_stop":
		// Ignored — we handle completion via process exit
		return nil

	default:
		return nil
	}
}

func (p *ClaudeParser) parseDelta(raw json.RawMessage) []types.StreamChunk {
	if raw == nil {
		return nil
	}

	var delta claudeDelta
	if err := json.Unmarshal(raw, &delta); err != nil {
		return nil
	}

	switch delta.Type {
	case "text_delta":
		return []types.StreamChunk{{Content: delta.Text, Type: types.ChunkText}}
	case "thinking_delta":
		return []types.StreamChunk{{Content: delta.Thinking, Type: types.ChunkThinking}}
	case "input_json_delta":
		// Tool input accumulation — ignored for display purposes
		return nil
	default:
		return nil
	}
}

func (p *ClaudeParser) parseContentBlockStart(raw json.RawMessage) []types.StreamChunk {
	if raw == nil {
		return nil
	}

	var block claudeContentBlock
	if err := json.Unmarshal(raw, &block); err != nil {
		return nil
	}

	switch block.Type {
	case "tool_use":
		return []types.StreamChunk{{
			Type:        types.ChunkToolStart,
			ToolCallID:  block.ID,
			ToolName:    block.Name,
			DisplayType: displayTypeFor(block.Name),
		}}
	case "thinking":
		return []types.StreamChunk{{Content: "", Type: types.ChunkThinking}}
	default:
		return nil
	}
}

func (p *ClaudeParser) parseAssistantMessage(raw json.RawMessage) []types.StreamChunk {
	if raw == nil {
		return nil
	}

	var msg claudeAssistantMessage
	if err := json.Unmarshal(raw, &msg); err != nil {
		return nil
	}

	var chunks []types.StreamChunk
	for _, part := range msg.Content {
		if part.Type != "tool_result" {
			continue
		}

		resultText := extractToolResultText(part.Content)
		chunk := types.StreamChunk{
			Type:       types.ChunkToolEnd,
			ToolCallID: part.ToolUseID,
		}
		if part.IsError {
			chunk.ToolError = resultText
		} else {
			chunk.Result = resultText
		}
		chunks = append(chunks, chunk)
	}

	return chunks
}

// extractToolResultText extracts text from a tool result content field,
// which can be a string, an array of content blocks, or nil.
func extractToolResultText(content interface{}) string {
	if content == nil {
		return ""
	}

	// String content
	if s, ok := content.(string); ok {
		return s
	}

	// Array of content blocks
	if arr, ok := content.([]interface{}); ok {
		var parts []string
		for _, item := range arr {
			if m, ok := item.(map[string]interface{}); ok {
				if m["type"] == "text" {
					if text, ok := m["text"].(string); ok {
						parts = append(parts, text)
					}
				}
			}
		}
		return strings.Join(parts, "")
	}

	return ""
}

// displayTypeFor maps Claude tool names to display types.
func displayTypeFor(toolName string) string {
	switch toolName {
	case "Bash":
		return "bash"
	case "Edit", "Write":
		return "diff"
	case "Read", "Glob", "Grep":
		return "code"
	default:
		return "generic"
	}
}
