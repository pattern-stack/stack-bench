package tui

import (
	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/agentic-tui/internal/types"
)

// EndpointConfig allows customizing the API path structure.
// Re-exported from internal/types for use by consumers.
type EndpointConfig = types.EndpointConfig

// Config configures an agentic-tui instance.
type Config struct {
	// AppName is displayed in headers and the agent picker. Required.
	AppName string

	// AssistantLabel is the prefix shown before assistant messages (e.g., "ai:", "claude:").
	// Defaults to lowercase AppName + ":" if empty.
	AssistantLabel string

	// Backend specifies how to connect to the backend.
	// Exactly one of BackendURL, BackendService, BackendStdio, BackendCLI,
	// or BackendExec must be set.
	BackendURL     string         // HTTP/SSE: Direct URL
	BackendService ServiceNode    // HTTP/SSE: Auto-managed local service
	BackendStdio   *StdioConfig   // JSON-RPC: Spawn subprocess
	BackendCLI     *CLIAgentConfig // CLI agent with JSONL streaming (Claude, Gemini, etc.)
	BackendExec    *ExecConfig    // Raw text CLI (any command)

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

// CLIFormat identifies the JSONL output format of a CLI agent.
type CLIFormat string

const (
	FormatClaude CLIFormat = "claude"
	FormatGemini CLIFormat = "gemini"
)

// CLIAgentConfig configures a CLI agent that emits JSONL streaming output.
type CLIAgentConfig struct {
	Command string    // e.g. "claude", "gemini"
	Args    []string  // base args BEFORE the prompt
	Format  CLIFormat // which JSONL parser to use
	Dir     string    // working directory (optional)
	Env     []string  // extra env vars (optional)
}

// ExecConfig configures a raw text CLI command.
type ExecConfig struct {
	Command        string   // e.g. "aider"
	Args           []string // args before the prompt
	Dir            string   // working directory
	Env            []string // extra env vars
	PromptViaStdin bool     // if true, pipe prompt to stdin instead of appending as last arg
}
