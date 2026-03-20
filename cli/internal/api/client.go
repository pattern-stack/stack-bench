package api

import "context"

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

// StreamChunk is a piece of a streaming response from the backend.
type StreamChunk struct {
	Content string
	Done    bool
	Error   error
}

// Client defines the interface for communicating with the stack-bench backend.
// SB-010 will provide a real HTTP implementation; this package provides a stub.
type Client interface {
	// ListAgents returns all available agents.
	ListAgents(ctx context.Context) ([]Agent, error)

	// SendMessage sends a user message and returns a channel of streamed response chunks.
	SendMessage(ctx context.Context, conversationID string, content string) (<-chan StreamChunk, error)

	// CreateConversation starts a new conversation with the given agent.
	CreateConversation(ctx context.Context, agentID string) (string, error)
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
