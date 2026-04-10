package tui

import (
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
