package api

import (
	"context"
	"strings"
	"sync"
	"time"
)

// DemoMessage is a single message in a demo script.
type DemoMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
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
	var content string
	found := false
	for d.cursor < len(d.script) {
		if d.script[d.cursor].Role == "assistant" {
			content = d.script[d.cursor].Content
			d.cursor++
			found = true
			break
		}
		d.cursor++
	}
	d.mu.Unlock()

	if !found {
		content = "(end of demo script)"
	}

	ch := make(chan StreamChunk, 64)
	go func() {
		defer close(ch)
		// Stream line-by-line, then word-by-word within each line,
		// preserving newlines so markdown structure survives.
		lines := strings.Split(content, "\n")
		for li, line := range lines {
			if li > 0 {
				ch <- StreamChunk{Content: "\n", Type: ChunkText}
				time.Sleep(15 * time.Millisecond)
			}
			// Preserve leading whitespace (indentation), then stream words
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
		ch <- StreamChunk{Done: true}
	}()

	return ch, nil
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
