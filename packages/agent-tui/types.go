package tui

import "time"

// AgentSummary is a display DTO for an available agent.
type AgentSummary struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Role  string `json:"role"`
	Model string `json:"model,omitempty"`
}

// Conversation is a summary of a past conversation for the picker.
type Conversation struct {
	ID            string    `json:"id"`
	AgentID       string    `json:"agent_id"`
	State         string    `json:"state"`
	ExchangeCount int       `json:"exchange_count"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}

// ConversationDetail is the full conversation with message history.
type ConversationDetail struct {
	ID            string                `json:"id"`
	AgentID       string                `json:"agent_id"`
	State         string                `json:"state"`
	ExchangeCount int                   `json:"exchange_count"`
	Messages      []ConversationMessage `json:"messages"`
	CreatedAt     time.Time             `json:"created_at"`
	UpdatedAt     time.Time             `json:"updated_at"`
}

// ConversationMessage is a message within a conversation detail response.
type ConversationMessage struct {
	ID       string        `json:"id"`
	Kind     string        `json:"kind"`
	Sequence int           `json:"sequence"`
	Parts    []MessagePart `json:"parts"`
}

// MessagePart is a part of a message (text, tool_call, etc).
type MessagePart struct {
	Type    string  `json:"type"`
	Content *string `json:"content,omitempty"`
}

// ChunkType identifies the kind of streaming event.
type ChunkType string

const (
	ChunkText      ChunkType = "text"
	ChunkThinking  ChunkType = "thinking"
	ChunkToolStart ChunkType = "tool_start"
	ChunkToolEnd   ChunkType = "tool_end"
)

// StreamChunk is a piece of a streaming response from the backend.
type StreamChunk struct {
	Content     string
	Type        ChunkType
	Done        bool
	Error       error
	ToolCallID  string
	ToolName    string
	DisplayType string
	ToolInput   string
	ToolError   string
}
