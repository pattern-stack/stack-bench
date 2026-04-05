package httpclient

import (
	"context"

	"github.com/dugshub/agent-tui/internal/sse"
)

// StubClient returns canned responses. Useful for development without a backend.
type StubClient struct{}

func (s *StubClient) ListAgents(_ context.Context) ([]sse.AgentSummary, error) {
	return []sse.AgentSummary{
		{ID: "architect", Name: "Architect", Role: "Plans and designs"},
		{ID: "builder", Name: "Builder", Role: "Implements code"},
		{ID: "validator", Name: "Validator", Role: "Tests and verifies"},
	}, nil
}

func (s *StubClient) SendMessage(_ context.Context, _ string, _ string) (<-chan sse.StreamChunk, error) {
	ch := make(chan sse.StreamChunk, 1)
	ch <- sse.StreamChunk{Content: "(backend not connected)", Done: true}
	close(ch)
	return ch, nil
}

func (s *StubClient) CreateConversation(_ context.Context, _ string) (string, error) {
	return "stub-conversation-id", nil
}

func (s *StubClient) ListConversations(_ context.Context, _ string) ([]sse.Conversation, error) {
	return nil, nil
}

func (s *StubClient) GetConversation(_ context.Context, _ string) (*sse.ConversationDetail, error) {
	return nil, nil
}
