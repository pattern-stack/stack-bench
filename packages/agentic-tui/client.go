package tui

import (
	"github.com/dugshub/agentic-tui/internal/httpclient"
	"github.com/dugshub/agentic-tui/internal/types"
)

// NewHTTPClient creates a Client that communicates over HTTP/SSE.
func NewHTTPClient(baseURL string) types.Client {
	return httpclient.NewHTTPClient(baseURL)
}

// NewStubClient creates a Client that returns canned responses for testing.
func NewStubClient() types.Client {
	return &httpclient.StubClient{}
}

// NewStdioClient creates a Client that communicates via JSON-RPC over stdin/stdout.
// This is a placeholder — the actual stdio transport is implemented in SB-061.
func NewStdioClient(_ StdioConfig) (types.Client, error) {
	// TODO(SB-061): implement actual stdio client
	return &httpclient.StubClient{}, nil
}
