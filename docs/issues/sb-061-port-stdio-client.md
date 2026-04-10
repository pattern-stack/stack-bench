---
id: SB-061
title: Port JSON-RPC stdio client from main
status: draft
epic: EP-017
depends_on: [SB-059]
branch:
pr:
stack: agentic-tui
stack_index: 4
created: 2026-04-09
---

# Port JSON-RPC stdio client from main

## Summary

Copy the JSON-RPC 2.0 stdio client from main's `packages/agent-tui/internal/stdioclient/`
into the standalone package. This is a self-contained transport that spawns a
subprocess and communicates via JSON-RPC over stdin/stdout. It enables any
language SDK to drive the TUI without HTTP.

## Scope

What's in:
- Copy `internal/stdioclient/client.go` (~424 lines)
- Copy `internal/stdioclient/jsonrpc.go` (~144 lines)
- Port `internal/stdioclient/client_test.go`
- Update imports to use `internal/types` instead of `internal/sse`

What's out:
- StdioConfig public type (SB-060)
- Contract tests for stdio (SB-064)
- Examples (SB-064)

## Implementation

Source: `packages/agent-tui/internal/stdioclient/`

```
packages/agentic-tui/internal/stdioclient/
  client.go     ← StdioClient: spawn subprocess, stdin/stdout pipes, readLoop goroutine
  jsonrpc.go    ← Wire types: Request, Response, Notification
  client_test.go
```

Changes from main's version:
- Replace `internal/sse` imports with `internal/types`
- `convertStreamEvent()` maps JSON-RPC `stream.event` notifications to `types.StreamChunk`
- `Client` struct implements `types.Client` interface directly (no adapter)

JSON-RPC methods supported:
- `listAgents` → `[]types.AgentSummary`
- `createConversation` → `{id: string}`
- `sendMessage` → streaming via `stream.event` notifications
- `listConversations` → `[]types.Conversation` (optional, -32601 if unsupported)
- `getConversation` → `types.ConversationDetail` (optional)

## Verification

- [ ] `go build ./internal/stdioclient/...` passes
- [ ] `go test ./internal/stdioclient/...` passes
- [ ] `StdioClient` implements `types.Client` interface (compile-time check)
- [ ] No imports from `internal/sse` (only `internal/types`)

## Notes

- The stdio client handles graceful shutdown: SIGTERM → 5s grace → SIGKILL
- Pending requests tracked in `map[id]chan *Response` with mutex
- Stream events arrive as `stream.event` notifications (no `id` field — they're JSON-RPC notifications, not responses)
