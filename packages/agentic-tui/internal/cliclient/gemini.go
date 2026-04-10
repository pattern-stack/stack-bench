package cliclient

import (
	"encoding/json"

	"github.com/dugshub/agentic-tui/internal/types"
)

// GeminiParser parses Gemini CLI's --output-format stream-json output.
// Gemini's streaming format follows a similar structure to Claude's
// (both inspired by Anthropic's streaming API).
//
// TODO: Verify exact Gemini CLI stream-json format against real output.
// Current implementation is modeled after known Gemini CLI behavior.
type GeminiParser struct{}

// geminiEvent is the top-level event from Gemini's stream-json output.
type geminiEvent struct {
	Type    string          `json:"type"`
	Subtype string          `json:"subtype,omitempty"`
	Event   json.RawMessage `json:"event,omitempty"`
	Message json.RawMessage `json:"message,omitempty"`
	Result  json.RawMessage `json:"result,omitempty"`
}

// geminiInnerEvent is the "event" field inside a stream_event.
type geminiInnerEvent struct {
	Type         string          `json:"type"`
	ContentBlock json.RawMessage `json:"content_block,omitempty"`
	Delta        json.RawMessage `json:"delta,omitempty"`
}

type geminiContentBlock struct {
	Type string `json:"type"`
	ID   string `json:"id,omitempty"`
	Name string `json:"name,omitempty"`
}

type geminiDelta struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
}

// geminiToolResult represents a tool result in the assistant message.
type geminiToolResult struct {
	Type      string      `json:"type"`
	ToolUseID string      `json:"tool_use_id,omitempty"`
	Content   interface{} `json:"content,omitempty"`
	IsError   bool        `json:"is_error,omitempty"`
}

// ParseLine parses a single JSONL line from Gemini CLI output.
func (p *GeminiParser) ParseLine(line []byte) []types.StreamChunk {
	var event geminiEvent
	if err := json.Unmarshal(line, &event); err != nil {
		return nil
	}

	switch event.Type {
	case "system":
		return nil

	case "stream_event":
		return p.parseStreamEvent(event.Event)

	case "assistant":
		return p.parseAssistantMessage(event.Message)

	case "result":
		return nil

	default:
		return nil
	}
}

func (p *GeminiParser) parseStreamEvent(raw json.RawMessage) []types.StreamChunk {
	if raw == nil {
		return nil
	}

	var inner geminiInnerEvent
	if err := json.Unmarshal(raw, &inner); err != nil {
		return nil
	}

	switch inner.Type {
	case "content_block_delta":
		return p.parseDelta(inner.Delta)
	case "content_block_start":
		return p.parseContentBlockStart(inner.ContentBlock)
	default:
		return nil
	}
}

func (p *GeminiParser) parseDelta(raw json.RawMessage) []types.StreamChunk {
	if raw == nil {
		return nil
	}

	var delta geminiDelta
	if err := json.Unmarshal(raw, &delta); err != nil {
		return nil
	}

	if delta.Type == "text_delta" {
		return []types.StreamChunk{{Content: delta.Text, Type: types.ChunkText}}
	}

	return nil
}

func (p *GeminiParser) parseContentBlockStart(raw json.RawMessage) []types.StreamChunk {
	if raw == nil {
		return nil
	}

	var block geminiContentBlock
	if err := json.Unmarshal(raw, &block); err != nil {
		return nil
	}

	if block.Type == "tool_use" {
		return []types.StreamChunk{{
			Type:        types.ChunkToolStart,
			ToolCallID:  block.ID,
			ToolName:    block.Name,
			DisplayType: "generic",
		}}
	}

	return nil
}

func (p *GeminiParser) parseAssistantMessage(raw json.RawMessage) []types.StreamChunk {
	if raw == nil {
		return nil
	}

	var msg struct {
		Content []geminiToolResult `json:"content"`
	}
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
