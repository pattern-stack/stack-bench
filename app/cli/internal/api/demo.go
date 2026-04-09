package api

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"
)

// DemoMessage is a single message in a demo script.
type DemoMessage struct {
	Role    string     `json:"role"`
	Content string     `json:"content"`
	Parts   []DemoPart `json:"parts,omitempty"` // structured parts (optional, overrides Content)
}

// DemoPart is a structured part within a demo message.
type DemoPart struct {
	Type        string         `json:"type"`                   // "text", "thinking", "tool_call", "error"
	Content     string         `json:"content,omitempty"`      // text/thinking/error content
	ToolName    string         `json:"tool_name,omitempty"`    // for tool_call
	DisplayType string         `json:"display_type,omitempty"` // "generic", "diff", "code", "bash"
	Arguments   map[string]any `json:"arguments,omitempty"`    // tool arguments
	Result      string         `json:"result,omitempty"`       // tool result
	Error       string         `json:"error,omitempty"`        // tool error
	DurationMs  int            `json:"duration_ms,omitempty"`  // tool duration
}

// DemoClient replays a scripted conversation for demo/testing purposes.
// It implements the Client interface.
type DemoClient struct {
	script []DemoMessage
	cursor int
	mu     sync.Mutex
}

var _ Client = (*DemoClient)(nil)

// NewDemoClient creates a Client that replays the given script.
func NewDemoClient(script []DemoMessage) *DemoClient {
	return &DemoClient{script: script}
}

func (d *DemoClient) ListAgents(_ context.Context) ([]AgentSummary, error) {
	return []AgentSummary{
		{ID: "demo", Name: "Demo Agent", Role: "Scripted replay"},
	}, nil
}

func (d *DemoClient) CreateConversation(_ context.Context, _ string) (string, error) {
	return "demo-conversation", nil
}

func (d *DemoClient) SendMessage(_ context.Context, _ string, _ string) (<-chan StreamChunk, error) {
	d.mu.Lock()
	var msg *DemoMessage
	for d.cursor < len(d.script) {
		if d.script[d.cursor].Role == "assistant" {
			msg = &d.script[d.cursor]
			d.cursor++
			break
		}
		d.cursor++
	}
	d.mu.Unlock()

	if msg == nil {
		msg = &DemoMessage{Role: "assistant", Content: "(end of demo script)"}
	}

	ch := make(chan StreamChunk, 64)
	go func() {
		defer close(ch)
		if len(msg.Parts) > 0 {
			d.streamParts(ch, msg.Parts)
		} else {
			d.streamText(ch, msg.Content)
		}
		ch <- StreamChunk{Done: true}
	}()

	return ch, nil
}

// streamText streams plain text word-by-word (original behavior).
func (d *DemoClient) streamText(ch chan<- StreamChunk, content string) {
	lines := strings.Split(content, "\n")
	for li, line := range lines {
		if li > 0 {
			ch <- StreamChunk{Content: "\n", Type: ChunkText}
			time.Sleep(15 * time.Millisecond)
		}
		trimmed := strings.TrimLeft(line, " \t")
		indent := line[:len(line)-len(trimmed)]
		if indent != "" {
			ch <- StreamChunk{Content: indent, Type: ChunkText}
		}
		words := strings.Fields(trimmed)
		for wi, word := range words {
			token := word
			if wi < len(words)-1 {
				token += " "
			}
			ch <- StreamChunk{Content: token, Type: ChunkText}
			time.Sleep(50 * time.Millisecond)
		}
	}
}

var demoToolCallCounter int

// streamParts streams structured parts with realistic timing.
func (d *DemoClient) streamParts(ch chan<- StreamChunk, parts []DemoPart) {
	for _, part := range parts {
		switch part.Type {
		case "text":
			d.streamText(ch, part.Content)

		case "thinking":
			ch <- StreamChunk{Content: part.Content, Type: ChunkThinking}
			time.Sleep(3 * time.Second)

		case "tool_call":
			demoToolCallCounter++
			tcID := fmt.Sprintf("demo-tc-%d", demoToolCallCounter)
			ch <- StreamChunk{
				Type:        ChunkToolStart,
				ToolCallID:  tcID,
				ToolName:    part.ToolName,
				DisplayType: part.DisplayType,
				Arguments:   part.Arguments,
			}
			// Sleep for the fixture-specified duration so the spinner stays
			// visible for the right amount of time. Floor at 1500ms so very
			// fast tools still produce a visible animation frame.
			dur := part.DurationMs
			if dur < 1500 {
				dur = 1500
			}
			time.Sleep(time.Duration(dur) * time.Millisecond)
			chunk := StreamChunk{
				Type:       ChunkToolEnd,
				ToolCallID: tcID,
				ToolName:   part.ToolName,
				Result:     part.Result,
				DurationMs: part.DurationMs,
			}
			if part.Error != "" {
				chunk.ToolError = part.Error
			}
			ch <- chunk
			time.Sleep(100 * time.Millisecond)

		case "tool_reject":
			// A tool that was blocked by a safety gate before execution.
			// Renders as a PartError under the assistant message.
			ch <- StreamChunk{
				Type:     ChunkToolReject,
				ToolName: part.ToolName,
				Content:  part.Content,
			}
			time.Sleep(400 * time.Millisecond)

		case "error":
			ch <- StreamChunk{Content: part.Content, Type: ChunkError}
			time.Sleep(100 * time.Millisecond)
		}
	}
}

func (d *DemoClient) ListConversations(_ context.Context, _ string) ([]Conversation, error) {
	return nil, nil
}

func (d *DemoClient) GetConversation(_ context.Context, _ string) (*ConversationDetailResponse, error) {
	return &ConversationDetailResponse{}, nil
}

func (d *DemoClient) BranchConversation(_ context.Context, _ string, _ int) (*Conversation, error) {
	return nil, nil
}
