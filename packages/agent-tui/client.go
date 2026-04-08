package tui

import (
	"context"

	"github.com/dugshub/agent-tui/internal/httpclient"
	"github.com/dugshub/agent-tui/internal/sse"
	"github.com/dugshub/agent-tui/internal/stdioclient"
)

// Client defines the interface for communicating with an agent backend.
// The package provides HTTPClient (HTTP/SSE), StdioClient (JSON-RPC over stdin/stdout),
// and StubClient (testing). Consumers can implement this for custom transports.
//
// ListConversations and GetConversation are optional — return (nil, nil) to skip.
type Client interface {
	ListAgents(ctx context.Context) ([]AgentSummary, error)
	CreateConversation(ctx context.Context, agentID string) (string, error)
	SendMessage(ctx context.Context, conversationID string, content string) (<-chan StreamChunk, error)
	ListConversations(ctx context.Context, agentName string) ([]Conversation, error)
	GetConversation(ctx context.Context, id string) (*ConversationDetail, error)
}

// NewHTTPClient creates a Client that communicates over HTTP/SSE.
func NewHTTPClient(baseURL string, endpoints *EndpointConfig) Client {
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
	return &publicClientAdapter{internal: httpclient.New(baseURL, epCfg)}
}

// NewStubClient creates a Client that returns canned responses.
func NewStubClient() Client {
	return &publicClientAdapter{internal: &httpclient.StubClient{}}
}

// NewStdioClient creates a Client that communicates via JSON-RPC over stdin/stdout.
func NewStdioClient(cfg StdioConfig) (Client, error) {
	c, err := stdioclient.New(stdioclient.Config{
		Command: cfg.Command,
		Args:    cfg.Args,
		Dir:     cfg.Dir,
		Env:     cfg.Env,
	})
	if err != nil {
		return nil, err
	}
	return &publicClientAdapter{internal: c}, nil
}

// publicClientAdapter wraps an sse.Client to satisfy the public Client interface.
// Used only by the NewHTTPClient/NewStubClient/NewStdioClient constructors
// for consumers who need a tui.Client instance.
type publicClientAdapter struct {
	internal sse.Client
}

func (a *publicClientAdapter) ListAgents(ctx context.Context) ([]AgentSummary, error) {
	agents, err := a.internal.ListAgents(ctx)
	if err != nil {
		return nil, err
	}
	result := make([]AgentSummary, len(agents))
	for i, ag := range agents {
		result[i] = AgentSummary{ID: ag.ID, Name: ag.Name, Role: ag.Role, Model: ag.Model}
	}
	return result, nil
}

func (a *publicClientAdapter) CreateConversation(ctx context.Context, agentID string) (string, error) {
	return a.internal.CreateConversation(ctx, agentID)
}

func (a *publicClientAdapter) SendMessage(ctx context.Context, conversationID string, content string) (<-chan StreamChunk, error) {
	sseCh, err := a.internal.SendMessage(ctx, conversationID, content)
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
				Arguments:   sc.Arguments,
				Result:      sc.Result,
				ToolError:   sc.ToolError,
				DurationMs:  sc.DurationMs,
			}
		}
	}()
	return ch, nil
}

func (a *publicClientAdapter) ListConversations(ctx context.Context, agentName string) ([]Conversation, error) {
	convs, err := a.internal.ListConversations(ctx, agentName)
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
			ExchangeCount:      c.ExchangeCount,
			BranchedFromID:     c.BranchedFromID,
			BranchedAtSequence: c.BranchedAtSequence,
			CreatedAt:          c.CreatedAt, UpdatedAt: c.UpdatedAt,
		}
	}
	return result, nil
}

func (a *publicClientAdapter) GetConversation(ctx context.Context, id string) (*ConversationDetail, error) {
	detail, err := a.internal.GetConversation(ctx, id)
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
