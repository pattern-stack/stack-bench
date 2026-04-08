package tui

import (
	"context"
	"strings"
	"sync"
	"time"

	"github.com/dugshub/agent-tui/internal/sse"
)

// DemoStep is a single step in a demo script. Each step can be a user message
// (Role="user", Content set) or an assistant response with rich streaming parts.
type DemoStep struct {
	Role    string     `json:"role"`
	Content string     `json:"content,omitempty"`
	Parts   []DemoPart `json:"parts,omitempty"`
}

// DemoPart is a typed content block within an assistant response.
type DemoPart struct {
	Type        string `json:"type"`                   // "text", "thinking", "tool_start", "tool_end"
	Content     string `json:"content,omitempty"`       // text/thinking content, or tool result
	ToolCallID  string `json:"tool_call_id,omitempty"`
	ToolName    string `json:"tool_name,omitempty"`
	DisplayType string `json:"display_type,omitempty"`  // "diff", "code", "bash", "generic"
	Input       string `json:"input,omitempty"`         // tool input
	Error       string `json:"error,omitempty"`         // tool error
}

// demoClient replays a scripted conversation for demo/testing purposes.
// It implements the internal sse.Client interface.
type demoClient struct {
	script []DemoStep
	cursor int
	mu     sync.Mutex
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

		// If step has parts, stream them with types
		if len(step.Parts) > 0 {
			for _, p := range step.Parts {
				switch p.Type {
				case "thinking":
					streamWords(ch, p.Content, sse.ChunkThinking, 20*time.Millisecond)
				case "tool_start":
					ch <- sse.StreamChunk{
						Content:     p.ToolName,
						Type:        sse.ChunkToolStart,
						ToolCallID:  p.ToolCallID,
						ToolName:    p.ToolName,
						DisplayType: p.DisplayType,
						ToolInput:   p.Input,
					}
					time.Sleep(300 * time.Millisecond)
				case "tool_end":
					ch <- sse.StreamChunk{
						Content:     p.Content,
						Type:        sse.ChunkToolEnd,
						ToolCallID:  p.ToolCallID,
						ToolName:    p.ToolName,
						DisplayType: p.DisplayType,
						ToolError:   p.Error,
					}
					time.Sleep(100 * time.Millisecond)
				default: // "text"
					streamWords(ch, p.Content, sse.ChunkText, 25*time.Millisecond)
				}
			}
		} else {
			// Simple text-only step
			streamWords(ch, step.Content, sse.ChunkText, 25*time.Millisecond)
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

// streamWords sends content word-by-word with a delay between each.
func streamWords(ch chan<- sse.StreamChunk, content string, chunkType sse.ChunkType, delay time.Duration) {
	words := strings.Fields(content)
	for i, word := range words {
		token := word
		if i < len(words)-1 {
			token += " "
		}
		ch <- sse.StreamChunk{Content: token, Type: chunkType}
		time.Sleep(delay)
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
