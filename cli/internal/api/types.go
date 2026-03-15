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

// SSEEvent is a parsed Server-Sent Event.
type SSEEvent struct {
	Event string
	Data  string
}
