package tui

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/dugshub/agent-tui/internal/sse"
)

// DemoStep is a single step in a demo script. Each step is either a user
// message (Role="user", Content set) or an assistant response (Role="assistant",
// Parts set with structured content blocks).
type DemoStep struct {
	Role    string     `json:"role"`
	Content string     `json:"content,omitempty"`
	Parts   []DemoPart `json:"parts,omitempty"`
}

// DemoPart is a typed content block within an assistant response.
//
// For tool_call parts, Arguments and Result mirror the SSE wire format —
// the demo client emits ChunkToolStart with the structured Arguments map and
// ChunkToolEnd with Result, so the chat model's display-type dispatch sees
// the same data shape it would from a real backend.
type DemoPart struct {
	Type        string         `json:"type"`                   // "text" | "thinking" | "tool_call" | "error"
	Content     string         `json:"content,omitempty"`      // text/thinking/error content
	ToolName    string         `json:"tool_name,omitempty"`    // for tool_call
	DisplayType string         `json:"display_type,omitempty"` // "generic", "diff", "code", "bash"
	Arguments   map[string]any `json:"arguments,omitempty"`    // structured tool arguments
	Result      string         `json:"result,omitempty"`       // tool result
	Error       string         `json:"error,omitempty"`        // tool error
	DurationMs  int            `json:"duration_ms,omitempty"`  // tool execution time
}

// demoClient replays a scripted conversation for demo/testing purposes.
// Implements the internal sse.Client interface so it slots into the same
// TUI plumbing as the real HTTP backend.
type demoClient struct {
	script    []DemoStep
	cursor    int
	toolCount int
	mu        sync.Mutex
}

var _ sse.Client = (*demoClient)(nil)

func newDemoClient(script []DemoStep) *demoClient {
	return &demoClient{script: script}
}

func (d *demoClient) ListAgents(_ context.Context) ([]sse.AgentSummary, error) {
	return []sse.AgentSummary{
		{ID: "demo", Name: "Demo Agent", Role: "Scripted replay"},
	}, nil
}

func (d *demoClient) CreateConversation(_ context.Context, _ string) (string, error) {
	return "demo-conversation", nil
}

func (d *demoClient) SendMessage(_ context.Context, _ string, _ string) (<-chan sse.StreamChunk, error) {
	d.mu.Lock()
	var step *DemoStep
	for d.cursor < len(d.script) {
		if d.script[d.cursor].Role == "assistant" {
			step = &d.script[d.cursor]
			d.cursor++
			break
		}
		d.cursor++
	}
	d.mu.Unlock()

	ch := make(chan sse.StreamChunk, 64)
	go func() {
		defer close(ch)
		if step == nil {
			ch <- sse.StreamChunk{Content: "(end of demo script)", Type: sse.ChunkText}
			ch <- sse.StreamChunk{Done: true}
			return
		}

		if len(step.Parts) > 0 {
			d.streamParts(ch, step.Parts)
		} else {
			d.streamText(ch, step.Content)
		}

		ch <- sse.StreamChunk{Done: true}
	}()

	return ch, nil
}

func (d *demoClient) ListConversations(_ context.Context, _ string) ([]sse.Conversation, error) {
	return nil, nil
}

func (d *demoClient) GetConversation(_ context.Context, _ string) (*sse.ConversationDetail, error) {
	return nil, nil
}

// streamText streams plain text word-by-word, preserving leading indent per line.
func (d *demoClient) streamText(ch chan<- sse.StreamChunk, content string) {
	lines := strings.Split(content, "\n")
	for li, line := range lines {
		if li > 0 {
			ch <- sse.StreamChunk{Content: "\n", Type: sse.ChunkText}
			time.Sleep(15 * time.Millisecond)
		}
		trimmed := strings.TrimLeft(line, " \t")
		indent := line[:len(line)-len(trimmed)]
		if indent != "" {
			ch <- sse.StreamChunk{Content: indent, Type: sse.ChunkText}
		}
		words := strings.Fields(trimmed)
		for wi, word := range words {
			token := word
			if wi < len(words)-1 {
				token += " "
			}
			ch <- sse.StreamChunk{Content: token, Type: sse.ChunkText}
			time.Sleep(50 * time.Millisecond)
		}
	}
}

// streamParts streams structured parts with realistic timing and tool call IDs.
func (d *demoClient) streamParts(ch chan<- sse.StreamChunk, parts []DemoPart) {
	for _, part := range parts {
		switch part.Type {
		case "text":
			d.streamText(ch, part.Content)

		case "thinking":
			ch <- sse.StreamChunk{Content: part.Content, Type: sse.ChunkThinking}
			time.Sleep(3 * time.Second)

		case "tool_call":
			d.toolCount++
			tcID := fmt.Sprintf("demo-tc-%d", d.toolCount)
			ch <- sse.StreamChunk{
				Type:        sse.ChunkToolStart,
				ToolCallID:  tcID,
				ToolName:    part.ToolName,
				DisplayType: part.DisplayType,
				Arguments:   part.Arguments,
			}
			// Simulate tool execution time, scaled up for visual effect.
			dur := part.DurationMs * 3
			if dur < 2000 {
				dur = 2000
			}
			if dur > 5000 {
				dur = 5000
			}
			time.Sleep(time.Duration(dur) * time.Millisecond)
			chunk := sse.StreamChunk{
				Type:       sse.ChunkToolEnd,
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

		case "error":
			ch <- sse.StreamChunk{Content: part.Content, Type: sse.ChunkError}
			time.Sleep(100 * time.Millisecond)
		}
	}
}

// NewDemoApp creates a TUI app that replays a scripted demo conversation.
// The script exercises all rendering paths: markdown, code blocks, thinking,
// tool calls (diff, code, bash, generic), and errors.
func NewDemoApp(script []DemoStep, cfg Config) (*App, error) {
	if cfg.AppName == "" {
		cfg.AppName = "Demo"
	}
	if cfg.AssistantLabel == "" {
		cfg.AssistantLabel = "demo:"
	}

	a := &App{
		cfg:            cfg,
		internalClient: newDemoClient(script),
	}
	return a, nil
}
