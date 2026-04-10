package tui

import tea "charm.land/bubbletea/v2"

// Config configures an agentic-tui instance.
type Config struct {
	// AppName is displayed in headers and the agent picker. Required.
	AppName string

	// AssistantLabel is the prefix shown before assistant messages (e.g., "ai:", "claude:").
	// Defaults to lowercase AppName + ":" if empty.
	AssistantLabel string

	// Backend specifies how to connect to the backend.
	// Exactly one of BackendURL, BackendService, or BackendStdio must be set.
	BackendURL     string       // HTTP/SSE: Direct URL
	BackendService ServiceNode  // HTTP/SSE: Auto-managed local service
	BackendStdio   *StdioConfig // JSON-RPC: Spawn subprocess

	// EnvOverride is the environment variable name that overrides BackendURL.
	EnvOverride string

	// Theme is the initial theme. Defaults to DarkTheme() if nil.
	Theme *Theme

	// Commands are additional slash commands to register.
	Commands []CommandDef

	// Endpoints allows overriding the default API path structure.
	Endpoints *EndpointConfig

	// OnReady is called after the backend is connected and agents are loaded.
	OnReady func(agents []AgentSummary)
}

// EndpointConfig allows customizing the API path structure.
type EndpointConfig struct {
	ListAgents         string // default: "/agents"
	CreateConversation string // default: "/conversations"
	SendMessage        string // default: "/conversations/{id}/messages"
	ListConversations  string // default: "/conversations"
	GetConversation    string // default: "/conversations/{id}"
	Health             string // default: "/health"
}

// CommandDef defines a slash command.
type CommandDef struct {
	Name        string
	Aliases     []string
	Description string
	Category    string
	Hidden      bool
	Handler     CommandHandler
}

// CommandHandler is called when a slash command is executed.
type CommandHandler func(result CommandParseResult) tea.Cmd

// CommandParseResult holds the parsed output of a slash command.
type CommandParseResult struct {
	Command string
	Args    []string
	Flags   map[string]bool
	Options map[string]string
	Raw     string
}
