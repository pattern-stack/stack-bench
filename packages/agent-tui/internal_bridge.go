package tui

import (
	"context"

	"github.com/dugshub/agent-tui/internal/sse"
)

// internalClientAdapter wraps a public Client to satisfy sse.Client.
// This bridges the public types back to internal sse types for the app model.
type internalClientAdapter struct {
	client Client
}

func (a *internalClientAdapter) ListAgents(ctx context.Context) ([]sse.AgentSummary, error) {
	agents, err := a.client.ListAgents(ctx)
	if err != nil {
		return nil, err
	}
	result := make([]sse.AgentSummary, len(agents))
	for i, ag := range agents {
		result[i] = sse.AgentSummary{ID: ag.ID, Name: ag.Name, Role: ag.Role, Model: ag.Model}
	}
	return result, nil
}

func (a *internalClientAdapter) CreateConversation(ctx context.Context, agentID string) (string, error) {
	return a.client.CreateConversation(ctx, agentID)
}

func (a *internalClientAdapter) SendMessage(ctx context.Context, conversationID string, content string) (<-chan sse.StreamChunk, error) {
	pubCh, err := a.client.SendMessage(ctx, conversationID, content)
	if err != nil {
		return nil, err
	}
	ch := make(chan sse.StreamChunk, 16)
	go func() {
		defer close(ch)
		for sc := range pubCh {
			ch <- sse.StreamChunk{
				Content:     sc.Content,
				Type:        sse.ChunkType(sc.Type),
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

func (a *internalClientAdapter) ListConversations(ctx context.Context, agentName string) ([]sse.Conversation, error) {
	convs, err := a.client.ListConversations(ctx, agentName)
	if err != nil {
		return nil, err
	}
	if convs == nil {
		return nil, nil
	}
	result := make([]sse.Conversation, len(convs))
	for i, c := range convs {
		result[i] = sse.Conversation{
			ID: c.ID, AgentID: c.AgentID, State: c.State,
			ExchangeCount:      c.ExchangeCount,
			BranchedFromID:     c.BranchedFromID,
			BranchedAtSequence: c.BranchedAtSequence,
			CreatedAt:          c.CreatedAt, UpdatedAt: c.UpdatedAt,
		}
	}
	return result, nil
}

func (a *internalClientAdapter) GetConversation(ctx context.Context, id string) (*sse.ConversationDetail, error) {
	detail, err := a.client.GetConversation(ctx, id)
	if err != nil || detail == nil {
		return nil, err
	}
	msgs := make([]sse.ConversationMessage, len(detail.Messages))
	for i, m := range detail.Messages {
		parts := make([]sse.MessagePart, len(m.Parts))
		for j, p := range m.Parts {
			parts[j] = sse.MessagePart{Type: p.Type, Content: p.Content}
		}
		msgs[i] = sse.ConversationMessage{ID: m.ID, Kind: m.Kind, Sequence: m.Sequence, Parts: parts}
	}
	return &sse.ConversationDetail{
		ID: detail.ID, AgentID: detail.AgentID, State: detail.State,
		ExchangeCount: detail.ExchangeCount, Messages: msgs,
		CreatedAt: detail.CreatedAt, UpdatedAt: detail.UpdatedAt,
	}, nil
}
