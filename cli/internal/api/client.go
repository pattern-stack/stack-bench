package api

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// Agent represents an available agent from the backend.
type Agent struct {
	ID   string
	Name string
	Role string
}

// Message represents a chat message exchanged with the backend.
type Message struct {
	Role    string // "user" or "assistant"
	Content string
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
	Content string
	Type    ChunkType // "text", "thinking", "tool_start", "tool_end"
	Done    bool
	Error   error
}

// Client defines the interface for communicating with the stack-bench backend.
type Client interface {
	// ListAgents returns all available agents.
	ListAgents(ctx context.Context) ([]Agent, error)

	// SendMessage sends a user message and returns a channel of streamed response chunks.
	SendMessage(ctx context.Context, conversationID string, content string) (<-chan StreamChunk, error)

	// CreateConversation starts a new conversation with the given agent.
	CreateConversation(ctx context.Context, agentID string) (string, error)
}

// HTTPClient communicates with the stack-bench backend over HTTP.
type HTTPClient struct {
	BaseURL    string
	HTTPClient *http.Client
}

var _ Client = (*HTTPClient)(nil)

// NewHTTPClient creates a client pointing at the given backend base URL.
// The default timeout of 30s applies to non-streaming requests.
// For SSE streaming, context cancellation is used instead.
func NewHTTPClient(baseURL string) *HTTPClient {
	return &HTTPClient{
		BaseURL: baseURL,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *HTTPClient) ListAgents(ctx context.Context) ([]Agent, error) {
	// GET /agents/ returns list[str] (agent names)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.BaseURL+"/agents/", nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("list agents: HTTP %d", resp.StatusCode)
	}

	var names []string
	if err := json.NewDecoder(resp.Body).Decode(&names); err != nil {
		return nil, err
	}

	// Fetch details for each agent to get role info
	agents := make([]Agent, 0, len(names))
	for _, name := range names {
		detail, err := c.getAgentDetail(ctx, name)
		if err != nil {
			// Fall back to name-only if detail fetch fails
			agents = append(agents, Agent{ID: name, Name: name, Role: ""})
			continue
		}
		agents = append(agents, Agent{
			ID:   detail.Name,
			Name: detail.RoleName,
			Role: detail.Mission,
		})
	}

	return agents, nil
}

func (c *HTTPClient) getAgentDetail(ctx context.Context, name string) (*AgentResponse, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.BaseURL+"/agents/"+name, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("get agent %s: HTTP %d", name, resp.StatusCode)
	}

	var detail AgentResponse
	if err := json.NewDecoder(resp.Body).Decode(&detail); err != nil {
		return nil, err
	}
	return &detail, nil
}

func (c *HTTPClient) CreateConversation(ctx context.Context, agentID string) (string, error) {
	body, err := json.Marshal(CreateConversationRequest{AgentName: agentID})
	if err != nil {
		return "", err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+"/conversations/", bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		return "", fmt.Errorf("create conversation: HTTP %d", resp.StatusCode)
	}

	var conv ConversationResponse
	if err := json.NewDecoder(resp.Body).Decode(&conv); err != nil {
		return "", err
	}
	return conv.ID, nil
}

func (c *HTTPClient) SendMessage(ctx context.Context, conversationID string, content string) (<-chan StreamChunk, error) {
	body, err := json.Marshal(SendMessageRequest{Message: content})
	if err != nil {
		return nil, err
	}

	url := fmt.Sprintf("%s/conversations/%s/send", c.BaseURL, conversationID)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")

	// Use a client without timeout for SSE streaming — the stream is
	// long-lived and cancellation is handled via ctx.
	streamClient := &http.Client{Transport: c.HTTPClient.Transport}
	resp, err := streamClient.Do(req)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		return nil, fmt.Errorf("send message: HTTP %d", resp.StatusCode)
	}

	// Parse SSE stream into StreamChunks
	sseCh := ParseSSE(resp.Body)
	ch := make(chan StreamChunk, 16)
	go func() {
		defer close(ch)
		for evt := range sseCh {
			chunk := ChunkFromSSE(evt)
			if chunk != nil {
				ch <- *chunk
				if chunk.Done {
					return
				}
			}
		}
		// Stream ended without a done event
		ch <- StreamChunk{Done: true}
	}()

	return ch, nil
}

// StubClient is a no-op client that returns empty results.
// It satisfies the Client interface so the CLI compiles and runs
// before the backend is wired in.
type StubClient struct{}

var _ Client = (*StubClient)(nil)

func (s *StubClient) ListAgents(_ context.Context) ([]Agent, error) {
	return []Agent{
		{ID: "architect", Name: "Architect", Role: "Plans and designs"},
		{ID: "builder", Name: "Builder", Role: "Implements code"},
		{ID: "validator", Name: "Validator", Role: "Tests and verifies"},
	}, nil
}

func (s *StubClient) SendMessage(_ context.Context, _ string, _ string) (<-chan StreamChunk, error) {
	ch := make(chan StreamChunk, 1)
	ch <- StreamChunk{Content: "(backend not connected)", Done: true}
	close(ch)
	return ch, nil
}

func (s *StubClient) CreateConversation(_ context.Context, _ string) (string, error) {
	return "stub-conversation-id", nil
}
