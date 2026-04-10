package types

import "context"

// Client defines the interface for communicating with the backend.
type Client interface {
	// ListAgents returns all available agents.
	ListAgents(ctx context.Context) ([]AgentSummary, error)

	// SendMessage sends a user message and returns a channel of streamed response chunks.
	SendMessage(ctx context.Context, conversationID string, content string) (<-chan StreamChunk, error)

	// CreateConversation starts a new conversation with the given agent.
	CreateConversation(ctx context.Context, agentID string) (string, error)

	// ListConversations returns past conversations, optionally filtered by agent name.
	ListConversations(ctx context.Context, agentName string) ([]Conversation, error)

	// GetConversation returns full conversation details with messages.
	GetConversation(ctx context.Context, id string) (*ConversationDetailResponse, error)
}
