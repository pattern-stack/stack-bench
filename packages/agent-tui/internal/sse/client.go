package sse

import "context"

// Client defines the internal interface for communicating with an agent backend.
// HTTPClient, StdioClient, and StubClient all satisfy this interface.
type Client interface {
	ListAgents(ctx context.Context) ([]AgentSummary, error)
	CreateConversation(ctx context.Context, agentID string) (string, error)
	SendMessage(ctx context.Context, conversationID string, content string) (<-chan StreamChunk, error)
	ListConversations(ctx context.Context, agentName string) ([]Conversation, error)
	GetConversation(ctx context.Context, id string) (*ConversationDetail, error)
}
