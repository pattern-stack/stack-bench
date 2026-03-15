package api

import "time"

// AgentResponse matches the backend GET /agents/{name} response.
type AgentResponse struct {
	Name       string  `json:"name"`
	RoleName   string  `json:"role_name"`
	Model      string  `json:"model"`
	Mission    string  `json:"mission"`
	Background *string `json:"background,omitempty"`
}

// ConversationResponse matches the backend POST /conversations/ response.
type ConversationResponse struct {
	ID              string    `json:"id"`
	ReferenceNumber *string   `json:"reference_number,omitempty"`
	AgentName       string    `json:"agent_name"`
	Model           string    `json:"model"`
	State           string    `json:"state"`
	ErrorMessage    *string   `json:"error_message,omitempty"`
	ExchangeCount   int       `json:"exchange_count"`
	TotalInputToks  int       `json:"total_input_tokens"`
	TotalOutputToks int       `json:"total_output_tokens"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
}

// CreateConversationRequest is the POST body for /conversations/.
type CreateConversationRequest struct {
	AgentName string  `json:"agent_name"`
	Model     *string `json:"model,omitempty"`
}

// SendMessageRequest is the POST body for /conversations/{id}/send.
type SendMessageRequest struct {
	Message string `json:"message"`
}

// APIError represents an error returned by the backend API.
type APIError struct {
	Type string
	Msg  string
}

func (e *APIError) Error() string {
	return e.Type + ": " + e.Msg
}

// Conversation is a summary of a past conversation for the picker.
type Conversation struct {
	ID                string    `json:"id"`
	AgentName         string    `json:"agent_name"`
	State             string    `json:"state"`
	ExchangeCount     int       `json:"exchange_count"`
	TotalInputTokens  int       `json:"total_input_tokens"`
	TotalOutputTokens int       `json:"total_output_tokens"`
	BranchedFromID     *string   `json:"branched_from_id,omitempty"`
	BranchedAtSequence *int     `json:"branched_at_sequence,omitempty"`
	CreatedAt          time.Time `json:"created_at"`
	UpdatedAt         time.Time `json:"updated_at"`
}

// ConversationDetailResponse is the full conversation with messages.
type ConversationDetailResponse struct {
	ID            string                 `json:"id"`
	AgentName     string                 `json:"agent_name"`
	Model         string                 `json:"model"`
	State         string                 `json:"state"`
	ExchangeCount int                    `json:"exchange_count"`
	Messages      []ConversationMessage  `json:"messages"`
	CreatedAt     time.Time              `json:"created_at"`
	UpdatedAt     time.Time              `json:"updated_at"`
}

// ConversationMessage is a message within a conversation detail response.
type ConversationMessage struct {
	ID       string            `json:"id"`
	Kind     string            `json:"kind"`
	Sequence int               `json:"sequence"`
	Parts    []MessagePart     `json:"parts"`
}

// MessagePart is a part of a message (text, tool_call, etc).
type MessagePart struct {
	Type    string  `json:"type"`
	Content *string `json:"content,omitempty"`
}

// BranchConversationRequest is the POST body for branching.
type BranchConversationRequest struct {
	AtSequence int `json:"at_sequence"`
}

// SSEEvent is a parsed Server-Sent Event.
type SSEEvent struct {
	Event string
	Data  string
}
