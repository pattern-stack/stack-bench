package sse

// SSE-specific parsing data structures used only by parse.go.
// Shared types (StreamChunk, AgentSummary, etc.) live in internal/types.

// SSEChunkData is the JSON payload for agent.message.chunk events.
type SSEChunkData struct {
	Delta string `json:"delta"`
}

// SSEMessageCompleteData is the JSON payload for agent.message.complete events.
type SSEMessageCompleteData struct {
	Content      string `json:"content"`
	InputTokens  int    `json:"input_tokens"`
	OutputTokens int    `json:"output_tokens"`
}

// SSEReasoningData is the JSON payload for reasoning/thinking events.
type SSEReasoningData struct {
	Content string `json:"content"`
}

// SSEToolStartData is the JSON payload for tool start events.
type SSEToolStartData struct {
	ToolCallID  string         `json:"tool_call_id"`
	ToolName    string         `json:"tool_name"`
	DisplayType string         `json:"display_type"`
	Arguments   map[string]any `json:"arguments"`
	Input       string         `json:"input"`
}

// SSEToolEndData is the JSON payload for tool end events.
type SSEToolEndData struct {
	ToolCallID  string `json:"tool_call_id"`
	ToolName    string `json:"tool_name"`
	DisplayType string `json:"display_type"`
	Result      any    `json:"result"`
	Output      string `json:"output"`
	Error       string `json:"error"`
	DurationMs  int    `json:"duration_ms"`
}

// SSEErrorData is the JSON payload for error / agent.error events.
type SSEErrorData struct {
	ErrorType string `json:"error_type"`
	Message   string `json:"message"`
}
