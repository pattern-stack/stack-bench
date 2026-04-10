package httpclient

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/dugshub/agentic-tui/internal/sse"
	"github.com/dugshub/agentic-tui/internal/types"
)

// endpointConfig mirrors the public EndpointConfig from config.go
// with accessor methods that supply defaults.
type endpointConfig struct {
	listAgents         string
	createConversation string
	sendMessage        string
	listConversations  string
	getConversation    string
	health             string
}

func newEndpointConfig(pub *types.EndpointConfig) *endpointConfig {
	ec := &endpointConfig{
		listAgents:         "/agents",
		createConversation: "/conversations",
		sendMessage:        "/conversations/{id}/send",
		listConversations:  "/conversations",
		getConversation:    "/conversations/{id}",
		health:             "/health",
	}
	if pub == nil {
		return ec
	}
	if pub.ListAgents != "" {
		ec.listAgents = pub.ListAgents
	}
	if pub.CreateConversation != "" {
		ec.createConversation = pub.CreateConversation
	}
	if pub.SendMessage != "" {
		ec.sendMessage = pub.SendMessage
	}
	if pub.ListConversations != "" {
		ec.listConversations = pub.ListConversations
	}
	if pub.GetConversation != "" {
		ec.getConversation = pub.GetConversation
	}
	if pub.Health != "" {
		ec.health = pub.Health
	}
	return ec
}

func (e *endpointConfig) sendMessagePath(id string) string {
	return strings.Replace(e.sendMessage, "{id}", id, 1)
}

func (e *endpointConfig) getConversationPath(id string) string {
	return strings.Replace(e.getConversation, "{id}", id, 1)
}

// HTTPClient communicates with the backend over HTTP.
type HTTPClient struct {
	BaseURL    string
	endpoints  *endpointConfig
	HTTPClient *http.Client
}

var _ types.Client = (*HTTPClient)(nil)

// NewHTTPClient creates a client pointing at the given backend base URL.
// The default timeout of 30s applies to non-streaming requests.
// For SSE streaming, context cancellation is used instead.
// If endpoints is nil, default paths are used.
func NewHTTPClient(baseURL string, endpoints *types.EndpointConfig) *HTTPClient {
	return &HTTPClient{
		BaseURL:   baseURL,
		endpoints: newEndpointConfig(endpoints),
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *HTTPClient) ListAgents(ctx context.Context) ([]types.AgentSummary, error) {
	url := c.BaseURL + c.endpoints.listAgents

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
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

	// Read body once, try both formats
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read agents response: %w", err)
	}

	// Try decoding as []AgentSummary first (canonical format)
	var agents []types.AgentSummary
	if err := json.Unmarshal(body, &agents); err == nil && len(agents) > 0 && agents[0].ID != "" {
		return agents, nil
	}

	// Fallback: try as []string (legacy format)
	var names []string
	if err := json.Unmarshal(body, &names); err != nil {
		return nil, fmt.Errorf("list agents: unexpected response format")
	}

	// Fetch details for each agent to get role info
	result := make([]types.AgentSummary, 0, len(names))
	for _, name := range names {
		detail, err := c.getAgentDetail(ctx, name)
		if err != nil {
			// Fall back to name-only if detail fetch fails
			result = append(result, types.AgentSummary{ID: name, Name: name})
			continue
		}
		result = append(result, types.AgentSummary{
			ID:   detail.Name,
			Name: detail.RoleName,
			Role: detail.Mission,
		})
	}

	return result, nil
}

func (c *HTTPClient) getAgentDetail(ctx context.Context, name string) (*types.AgentResponse, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.BaseURL+c.endpoints.listAgents+"/"+name, nil)
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

	var detail types.AgentResponse
	if err := json.NewDecoder(resp.Body).Decode(&detail); err != nil {
		return nil, err
	}
	return &detail, nil
}

func (c *HTTPClient) CreateConversation(ctx context.Context, agentID string) (string, error) {
	body, err := json.Marshal(types.CreateConversationRequest{AgentName: agentID})
	if err != nil {
		return "", err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+c.endpoints.createConversation, bytes.NewReader(body))
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

	var conv types.ConversationResponse
	if err := json.NewDecoder(resp.Body).Decode(&conv); err != nil {
		return "", err
	}
	return conv.ID, nil
}

func (c *HTTPClient) SendMessage(ctx context.Context, conversationID string, content string) (<-chan types.StreamChunk, error) {
	body, err := json.Marshal(types.SendMessageRequest{Message: content})
	if err != nil {
		return nil, err
	}

	url := c.BaseURL + c.endpoints.sendMessagePath(conversationID)
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
	sseCh := sse.ParseSSE(resp.Body)
	ch := make(chan types.StreamChunk, 16)
	go func() {
		defer close(ch)
		for evt := range sseCh {
			chunk := sse.ChunkFromSSE(evt)
			if chunk != nil {
				ch <- *chunk
				if chunk.Done {
					return
				}
			}
		}
		// Stream ended without a done event
		ch <- types.StreamChunk{Done: true}
	}()

	return ch, nil
}

func (c *HTTPClient) ListConversations(ctx context.Context, agentName string) ([]types.Conversation, error) {
	url := c.BaseURL + c.endpoints.listConversations

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}

	// Server-side filtering via query parameters
	q := req.URL.Query()
	if agentName != "" {
		q.Set("agent_name", agentName)
	}
	req.URL.RawQuery = q.Encode()

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("list conversations: HTTP %d", resp.StatusCode)
	}

	var conversations []types.Conversation
	if err := json.NewDecoder(resp.Body).Decode(&conversations); err != nil {
		return nil, err
	}
	return conversations, nil
}

func (c *HTTPClient) GetConversation(ctx context.Context, id string) (*types.ConversationDetailResponse, error) {
	url := c.BaseURL + c.endpoints.getConversationPath(id)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("get conversation: HTTP %d", resp.StatusCode)
	}

	var detail types.ConversationDetailResponse
	if err := json.NewDecoder(resp.Body).Decode(&detail); err != nil {
		return nil, err
	}
	return &detail, nil
}

// StubClient is a no-op client that returns empty results.
// It satisfies the Client interface so the TUI compiles and runs
// before the backend is wired in.
type StubClient struct{}

var _ types.Client = (*StubClient)(nil)

func (s *StubClient) ListAgents(_ context.Context) ([]types.AgentSummary, error) {
	return []types.AgentSummary{
		{ID: "architect", Name: "Architect", Role: "Plans and designs"},
		{ID: "builder", Name: "Builder", Role: "Implements code"},
		{ID: "validator", Name: "Validator", Role: "Tests and verifies"},
	}, nil
}

func (s *StubClient) SendMessage(_ context.Context, _ string, _ string) (<-chan types.StreamChunk, error) {
	ch := make(chan types.StreamChunk, 1)
	ch <- types.StreamChunk{Content: "(backend not connected)", Done: true}
	close(ch)
	return ch, nil
}

func (s *StubClient) CreateConversation(_ context.Context, _ string) (string, error) {
	return "stub-conversation-id", nil
}

func (s *StubClient) ListConversations(_ context.Context, _ string) ([]types.Conversation, error) {
	return nil, nil
}

func (s *StubClient) GetConversation(_ context.Context, _ string) (*types.ConversationDetailResponse, error) {
	return &types.ConversationDetailResponse{}, nil
}
