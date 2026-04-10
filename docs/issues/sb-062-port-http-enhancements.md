---
id: SB-062
title: Port HTTP client enhancements from main
status: draft
epic: EP-017
depends_on: [SB-059]
branch: dug/agentic-tui/5-http-enhancements
pr:
stack: agentic-tui
stack_index: 5
created: 2026-04-09
---

# Port HTTP client enhancements from main

## Summary

Merge main's HTTP client improvements into the PR #198 base: configurable
endpoint paths, backward-compatible SSE event name aliases, and graceful
ListAgents fallback. The SSE parser merge is the critical piece — take PR
#198's parser (richer payloads) and add main's 4 canonical event aliases.

## Scope

What's in:
- Add `EndpointConfig` support to `internal/httpclient/` (configurable API paths)
- Add 4 canonical event aliases to `internal/sse/parse.go`:
  - `message.delta` → `ChunkText`
  - `message.complete` → `ChunkText` (done)
  - `tool.start` → `ChunkToolStart`
  - `tool.end` → `ChunkToolEnd`
- Add `ListAgents` fallback: try `[]AgentSummary`, fall back to `[]string`
- Enhance `StubClient` with main's richer version

What's out:
- Type changes (SB-059)
- New transport implementations (SB-061)

## Implementation

**SSE parser merge** (`internal/sse/parse.go`):

PR #198's `ChunkFromSSE` is the base — it has richer payload parsing:
- `SSEToolStartData.Arguments` (`map[string]any`)
- `SSEToolEndData.Result` (`any`) with fallback to `Output`
- `ChunkToolReject`, `ChunkIteration` types

Add main's aliases to the switch statement (~10 lines):
```go
case "message.delta":     // alias for agent.message.chunk
case "message.complete":  // alias for agent.message.complete
case "tool.start":        // alias for agent.tool.start
case "tool.end":          // alias for agent.tool.end
```

**EndpointConfig** (`internal/httpclient/client.go`):

From `packages/agent-tui/internal/httpclient/client.go`:
```go
type EndpointConfig struct {
    ListAgents         string // default: "/agents"
    CreateConversation string // default: "/conversations"
    SendMessage        string // default: "/conversations/{id}/send"
    ListConversations  string // default: "/conversations"
    GetConversation    string // default: "/conversations/{id}"
    Health             string // default: "/health"
}
```

Replace hardcoded URL construction with config-driven paths.

**ListAgents fallback**: Try unmarshaling as `[]AgentSummary` first. If that
fails, try `[]string` and convert to `AgentSummary{ID: name, Name: name}`.

Source: `packages/agent-tui/internal/httpclient/client.go`

## Verification

- [ ] `go test ./internal/sse/...` passes
- [ ] `go test ./internal/httpclient/...` passes
- [ ] SSE parser handles both `agent.message.chunk` and `message.delta` for the same event
- [ ] SSE parser handles both `agent.tool.start` and `tool.start`
- [ ] `EndpointConfig` with custom paths compiles and is wired through
- [ ] `Arguments map[string]any` is preserved in `StreamChunk` for tool.start events
- [ ] `Result` fallback to `Output` is preserved for tool.end events

## Notes

- The merge strategy is: PR #198 parser is base, main's aliases are additive
- Do NOT replace PR #198's richer payload parsing with main's simplified version
- `StubClient` source: `packages/agent-tui/internal/httpclient/stub.go`
