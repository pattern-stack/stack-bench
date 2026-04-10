package tui

import (
	"github.com/dugshub/agentic-tui/internal/cliclient"
	"github.com/dugshub/agentic-tui/internal/execclient"
	"github.com/dugshub/agentic-tui/internal/httpclient"
	"github.com/dugshub/agentic-tui/internal/stdioclient"
	"github.com/dugshub/agentic-tui/internal/types"
)

// NewHTTPClient creates a Client that communicates over HTTP/SSE.
// If endpoints is nil, default paths are used.
func NewHTTPClient(baseURL string, endpoints *EndpointConfig) types.Client {
	return httpclient.NewHTTPClient(baseURL, endpoints)
}

// NewStubClient creates a Client that returns canned responses for testing.
func NewStubClient() types.Client {
	return &httpclient.StubClient{}
}

// NewStdioClient creates a Client that communicates via JSON-RPC over stdin/stdout.
// It spawns the configured command as a subprocess and exchanges JSON-RPC 2.0
// messages over its stdin/stdout pipes.
func NewStdioClient(cfg StdioConfig) (types.Client, error) {
	return stdioclient.New(stdioclient.Config{
		Command: cfg.Command,
		Args:    cfg.Args,
		Dir:     cfg.Dir,
		Env:     cfg.Env,
	})
}

// NewCLIClient creates a Client that spawns a CLI agent per message and parses
// its JSONL streaming output (Claude, Gemini, etc.).
func NewCLIClient(cfg CLIAgentConfig) types.Client {
	return cliclient.New(cliclient.Config{
		Command: cfg.Command,
		Args:    cfg.Args,
		Format:  cliclient.Format(cfg.Format),
		Dir:     cfg.Dir,
		Env:     cfg.Env,
	})
}

// NewExecClient creates a Client that spawns any CLI command per message
// and streams its stdout as plain text.
func NewExecClient(cfg ExecConfig) types.Client {
	return execclient.New(execclient.Config{
		Command:        cfg.Command,
		Args:           cfg.Args,
		Dir:            cfg.Dir,
		Env:            cfg.Env,
		PromptViaStdin: cfg.PromptViaStdin,
	})
}
