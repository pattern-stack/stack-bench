package tui

import (
	"context"

	"github.com/dugshub/agent-tui/internal/httpclient"
	"github.com/dugshub/agent-tui/internal/sse"
	"github.com/dugshub/agent-tui/internal/stdioclient"
)

// clientAdapter wraps an internal client (using sse.* types) to satisfy
// the public Client interface (using tui.* types).
type clientAdapter struct {
	http  *httpclient.HTTPClient
	stub  *httpclient.StubClient
	stdio *stdioclient.Client
}

func (a *clientAdapter) ListAgents(ctx context.Context) ([]AgentSummary, error) {
	var agents []sse.AgentSummary
	var err error
	switch {
	case a.http != nil:
		agents, err = a.http.ListAgents(ctx)
	case a.stub != nil:
		agents, err = a.stub.ListAgents(ctx)
	case a.stdio != nil:
		agents, err = a.stdio.ListAgents(ctx)
	}
	if err != nil {
		return nil, err
	}
	result := make([]AgentSummary, len(agents))
	for i, ag := range agents {
		result[i] = AgentSummary{ID: ag.ID, Name: ag.Name, Role: ag.Role, Model: ag.Model}
	}
	return result, nil
}

func (a *clientAdapter) CreateConversation(ctx context.Context, agentID string) (string, error) {
	switch {
	case a.http != nil:
		return a.http.CreateConversation(ctx, agentID)
	case a.stub != nil:
		return a.stub.CreateConversation(ctx, agentID)
	case a.stdio != nil:
		return a.stdio.CreateConversation(ctx, agentID)
	}
	return "", nil
}

func (a *clientAdapter) SendMessage(ctx context.Context, conversationID string, content string) (<-chan StreamChunk, error) {
	var sseCh <-chan sse.StreamChunk
	var err error
	switch {
	case a.http != nil:
		sseCh, err = a.http.SendMessage(ctx, conversationID, content)
	case a.stub != nil:
		sseCh, err = a.stub.SendMessage(ctx, conversationID, content)
	case a.stdio != nil:
		sseCh, err = a.stdio.SendMessage(ctx, conversationID, content)
	}
	if err != nil {
		return nil, err
	}

	ch := make(chan StreamChunk, 16)
	go func() {
		defer close(ch)
		for sc := range sseCh {
			ch <- StreamChunk{
				Content:     sc.Content,
				Type:        ChunkType(sc.Type),
				Done:        sc.Done,
				Error:       sc.Error,
				ToolCallID:  sc.ToolCallID,
				ToolName:    sc.ToolName,
				DisplayType: sc.DisplayType,
				ToolInput:   sc.ToolInput,
				ToolError:   sc.ToolError,
			}
		}
	}()
	return ch, nil
}

func (a *clientAdapter) ListConversations(ctx context.Context, agentName string) ([]Conversation, error) {
	var convs []sse.Conversation
	var err error
	switch {
	case a.http != nil:
		convs, err = a.http.ListConversations(ctx, agentName)
	case a.stub != nil:
		convs, err = a.stub.ListConversations(ctx, agentName)
	case a.stdio != nil:
		convs, err = a.stdio.ListConversations(ctx, agentName)
	}
	if err != nil {
		return nil, err
	}
	if convs == nil {
		return nil, nil
	}
	result := make([]Conversation, len(convs))
	for i, c := range convs {
		result[i] = Conversation{
			ID: c.ID, AgentID: c.AgentID, State: c.State,
			ExchangeCount: c.ExchangeCount,
			CreatedAt: c.CreatedAt, UpdatedAt: c.UpdatedAt,
		}
	}
	return result, nil
}

func (a *clientAdapter) GetConversation(ctx context.Context, id string) (*ConversationDetail, error) {
	var detail *sse.ConversationDetail
	var err error
	switch {
	case a.http != nil:
		detail, err = a.http.GetConversation(ctx, id)
	case a.stub != nil:
		detail, err = a.stub.GetConversation(ctx, id)
	case a.stdio != nil:
		detail, err = a.stdio.GetConversation(ctx, id)
	}
	if err != nil || detail == nil {
		return nil, err
	}
	msgs := make([]ConversationMessage, len(detail.Messages))
	for i, m := range detail.Messages {
		parts := make([]MessagePart, len(m.Parts))
		for j, p := range m.Parts {
			parts[j] = MessagePart{Type: p.Type, Content: p.Content}
		}
		msgs[i] = ConversationMessage{ID: m.ID, Kind: m.Kind, Sequence: m.Sequence, Parts: parts}
	}
	return &ConversationDetail{
		ID: detail.ID, AgentID: detail.AgentID, State: detail.State,
		ExchangeCount: detail.ExchangeCount, Messages: msgs,
		CreatedAt: detail.CreatedAt, UpdatedAt: detail.UpdatedAt,
	}, nil
}

func newHTTPClient(baseURL string, endpoints *EndpointConfig) Client {
	var epCfg *httpclient.EndpointConfig
	if endpoints != nil {
		epCfg = &httpclient.EndpointConfig{
			ListAgents:         endpoints.ListAgents,
			CreateConversation: endpoints.CreateConversation,
			SendMessage:        endpoints.SendMessage,
			ListConversations:  endpoints.ListConversations,
			GetConversation:    endpoints.GetConversation,
			Health:             endpoints.Health,
		}
	}
	return &clientAdapter{http: httpclient.New(baseURL, epCfg)}
}

func newStubClient() Client {
	return &clientAdapter{stub: &httpclient.StubClient{}}
}

func newStdioClient(cfg StdioConfig) (Client, error) {
	c, err := stdioclient.New(stdioclient.Config{
		Command: cfg.Command,
		Args:    cfg.Args,
		Dir:     cfg.Dir,
		Env:     cfg.Env,
	})
	if err != nil {
		return nil, err
	}
	return &clientAdapter{stdio: c}, nil
}

// ExecServiceConfig and ServiceNode are now type aliases, so NewExecService
// delegates directly to service.NewExecService in service.go.
