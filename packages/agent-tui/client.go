package tui

import "context"

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
	return newHTTPClient(baseURL, endpoints)
}

// NewStubClient creates a Client that returns canned responses.
func NewStubClient() Client {
	return newStubClient()
}
