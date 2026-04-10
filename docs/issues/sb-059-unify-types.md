---
id: SB-059
title: Unify types into single source
status: draft
epic: EP-017
depends_on: [SB-058]
branch: dug/agentic-tui/2-unify-types
pr:
stack: agentic-tui
stack_index: 2
created: 2026-04-09
---

# Unify types into single source

## Summary

Create `internal/types/` as the single source of truth for all shared types
(`StreamChunk`, `ChunkType`, `AgentSummary`, `Conversation`, etc.) and the
`Client` interface. All internal packages import from `internal/types/`.
Root package re-exports via type aliases for the public API. This eliminates
the duplicate type definitions and adapter boilerplate from the rushed
PR #196 extraction.

## Scope

What's in:
- Create `internal/types/types.go` — all DTOs (`AgentSummary`, `StreamChunk`, `ChunkType`, `Conversation`, `ConversationDetail`, `ConversationMessage`, `MessagePart`)
- Create `internal/types/client.go` — `Client` interface (5 methods: `ListAgents`, `CreateConversation`, `SendMessage`, `ListConversations`, `GetConversation`)
- Update `internal/httpclient/` to import `internal/types`
- Update `internal/sse/` to import `internal/types` (keep parse logic, remove type defs)
- Update `internal/chat/` to import `internal/types`
- Update `internal/app/` to import `internal/types`
- Prepare root-level `types.go` with `type StreamChunk = types.StreamChunk` aliases

What's out:
- Public API wiring (SB-060)
- Transport implementations (SB-061, SB-062)

## Implementation

```
packages/agentic-tui/
  internal/types/
    types.go      ← canonical: AgentSummary, StreamChunk, ChunkType, Conversation, etc.
    client.go     ← canonical: Client interface
```

Type definitions come from PR #198's `api/types.go` (richer than main's):
- `ChunkType` as `string` constants (not `int` iota)
- `StreamChunk` with `Arguments map[string]any`, `Result string`, `ToolError string`, `DurationMs int`
- `ChunkToolReject` and `ChunkIteration` types included

Root re-exports:
```go
// packages/agentic-tui/types.go
package tui
import "github.com/dugshub/agentic-tui/internal/types"
type StreamChunk = types.StreamChunk
type ChunkType = types.ChunkType
type AgentSummary = types.AgentSummary
type Conversation = types.Conversation
type ConversationDetail = types.ConversationDetail
type Client = types.Client
// etc.
```

## Verification

- [ ] `go build ./...` passes
- [ ] `go vet ./...` passes
- [ ] `grep -r "type StreamChunk struct" packages/agentic-tui/` returns exactly 1 hit (in `internal/types/`)
- [ ] `grep -r "type AgentSummary struct" packages/agentic-tui/` returns exactly 1 hit
- [ ] No `publicClientAdapter` or `internalClientAdapter` exists
- [ ] All tests pass: `go test ./...`

## Notes

- The `Client` interface must NOT include `BranchConversation` (dropped in SB-058)
- `ListConversations` and `GetConversation` are optional — return `(nil, nil)` to skip
- `SendMessage` returns `<-chan StreamChunk` — the channel type must be `types.StreamChunk`
