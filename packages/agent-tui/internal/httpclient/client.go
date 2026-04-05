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

	"github.com/dugshub/agent-tui/internal/sse"
)

// EndpointConfig allows customizing the API path structure.
type EndpointConfig struct {
	ListAgents         string
	CreateConversation string
	SendMessage        string
	ListConversations  string
	GetConversation    string
	Health             string
}

func (e *EndpointConfig) listAgents() string {
	if e != nil && e.ListAgents != "" {
		return e.ListAgents
	}
	return "/agents"
}

func (e *EndpointConfig) createConversation() string {
	if e != nil && e.CreateConversation != "" {
		return e.CreateConversation
	}
	return "/conversations"
}

func (e *EndpointConfig) sendMessage(id string) string {
	tmpl := "/conversations/{id}/messages"
	if e != nil && e.SendMessage != "" {
		tmpl = e.SendMessage
	}
	return strings.Replace(tmpl, "{id}", id, 1)
}

func (e *EndpointConfig) listConversations() string {
	if e != nil && e.ListConversations != "" {
		return e.ListConversations
	}
	return "/conversations"
}

func (e *EndpointConfig) getConversation(id string) string {
	tmpl := "/conversations/{id}"
	if e != nil && e.GetConversation != "" {
		tmpl = e.GetConversation
	}
	return strings.Replace(tmpl, "{id}", id, 1)
}

// Wire format types for the Stack Bench backend.
type wireAgentResponse struct {
	Name     string  `json:"name"`
	RoleName string  `json:"role_name"`
	Model    string  `json:"model"`
	Mission  string  `json:"mission"`
}

type wireCreateConversationReq struct {
	AgentName string  `json:"agent_name"`
	Model     *string `json:"model,omitempty"`
}

type wireConversationResp struct {
	ID        string    `json:"id"`
	AgentName string    `json:"agent_name"`
	CreatedAt time.Time `json:"created_at"`
}

type wireSendMessageReq struct {
	Message string `json:"message"`
}

type wireConversation struct {
	ID            string    `json:"id"`
	AgentName     string    `json:"agent_name"`
	State         string    `json:"state"`
	ExchangeCount int       `json:"exchange_count"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}

type wireConversationDetail struct {
	ID            string                   `json:"id"`
	AgentName     string                   `json:"agent_name"`
	State         string                   `json:"state"`
	ExchangeCount int                      `json:"exchange_count"`
	Messages      []sse.ConversationMessage `json:"messages"`
	CreatedAt     time.Time                `json:"created_at"`
	UpdatedAt     time.Time                `json:"updated_at"`
}

// HTTPClient communicates with an agent backend over HTTP.
type HTTPClient struct {
	BaseURL    string
	Endpoints  *EndpointConfig
	HTTPClient *http.Client
}

// New creates an HTTPClient.
func New(baseURL string, endpoints *EndpointConfig) *HTTPClient {
	return &HTTPClient{
		BaseURL:   baseURL,
		Endpoints: endpoints,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *HTTPClient) ListAgents(ctx context.Context) ([]sse.AgentSummary, error) {
	url := c.BaseURL + c.Endpoints.listAgents()

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
	var agents []sse.AgentSummary
	if err := json.Unmarshal(body, &agents); err == nil && len(agents) > 0 && agents[0].ID != "" {
		return agents, nil
	}

	// Fallback: try as []string (Stack Bench legacy format)
	var names []string
	if err := json.Unmarshal(body, &names); err != nil {
		return nil, fmt.Errorf("list agents: unexpected response format")
	}

	result := make([]sse.AgentSummary, 0, len(names))
	for _, name := range names {
		detail, err := c.getAgentDetail(ctx, name)
		if err != nil {
			result = append(result, sse.AgentSummary{ID: name, Name: name})
			continue
		}
		result = append(result, sse.AgentSummary{
			ID:   detail.Name,
			Name: detail.RoleName,
			Role: detail.Mission,
		})
	}
	return result, nil
}

func (c *HTTPClient) getAgentDetail(ctx context.Context, name string) (*wireAgentResponse, error) {
	url := c.BaseURL + c.Endpoints.listAgents() + "/" + name
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
		return nil, fmt.Errorf("get agent %s: HTTP %d", name, resp.StatusCode)
	}

	var detail wireAgentResponse
	if err := json.NewDecoder(resp.Body).Decode(&detail); err != nil {
		return nil, err
	}
	return &detail, nil
}

func (c *HTTPClient) CreateConversation(ctx context.Context, agentID string) (string, error) {
	body, err := json.Marshal(wireCreateConversationReq{AgentName: agentID})
	if err != nil {
		return "", err
	}

	url := c.BaseURL + c.Endpoints.createConversation()
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("create conversation: HTTP %d", resp.StatusCode)
	}

	var result struct {
		ID string `json:"id"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}
	return result.ID, nil
}

func (c *HTTPClient) SendMessage(ctx context.Context, conversationID string, content string) (<-chan sse.StreamChunk, error) {
	body, err := json.Marshal(wireSendMessageReq{Message: content})
	if err != nil {
		return nil, err
	}

	url := c.BaseURL + c.Endpoints.sendMessage(conversationID)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")

	streamClient := &http.Client{Transport: c.HTTPClient.Transport}
	resp, err := streamClient.Do(req)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		return nil, fmt.Errorf("send message: HTTP %d", resp.StatusCode)
	}

	sseCh := sse.ParseSSE(resp.Body)
	ch := make(chan sse.StreamChunk, 16)
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
		ch <- sse.StreamChunk{Done: true}
	}()

	return ch, nil
}

func (c *HTTPClient) ListConversations(ctx context.Context, agentName string) ([]sse.Conversation, error) {
	url := c.BaseURL + c.Endpoints.listConversations()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	if agentName != "" {
		q := req.URL.Query()
		q.Set("agent_name", agentName)
		req.URL.RawQuery = q.Encode()
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil, nil
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("list conversations: HTTP %d", resp.StatusCode)
	}

	var conversations []sse.Conversation
	if err := json.NewDecoder(resp.Body).Decode(&conversations); err != nil {
		return nil, err
	}
	return conversations, nil
}

func (c *HTTPClient) GetConversation(ctx context.Context, id string) (*sse.ConversationDetail, error) {
	url := c.BaseURL + c.Endpoints.getConversation(id)
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

	var detail sse.ConversationDetail
	if err := json.NewDecoder(resp.Body).Decode(&detail); err != nil {
		return nil, err
	}
	return &detail, nil
}
