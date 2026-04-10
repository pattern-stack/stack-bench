---
id: SB-064
title: Contract tests, examples, PROTOCOL.md
status: draft
epic: EP-017
depends_on: [SB-061, SB-062]
branch: dug/agentic-tui/7-contract-tests-examples
pr:
stack: agentic-tui
stack_index: 7
created: 2026-04-09
---

# Contract tests, examples, PROTOCOL.md

## Summary

Add contract tests (validating HTTP and stdio backends), reference examples
(showing all integration patterns), and PROTOCOL.md (the universal backend
contract document). This is the capstone issue — everything should compile
and all tests pass after this.

## Scope

What's in:
- Copy `packages/agent-tui/contracttest/` → `packages/agentic-tui/contracttest/`
- Copy `packages/agent-tui/_examples/` → `packages/agentic-tui/_examples/`
- Update all import paths to `github.com/dugshub/agentic-tui`
- Write `PROTOCOL.md` at package root
- Final verification: `go build ./...` and `go test ./...` across entire package

What's out:
- CI/CD pipelines (post-epic ship task)
- GitHub Release workflow (post-epic)
- README.md (post-epic)
- Stack Bench integration (post-epic)

## Implementation

**Contract tests** (`contracttest/`):

Source: `packages/agent-tui/contracttest/`
```
packages/agentic-tui/contracttest/
  validate.go         ← ValidateBackend() for HTTP/SSE
  validate_stdio.go   ← ValidateStdioBackend() for JSON-RPC
  validate_test.go    ← Test helpers
```

Update imports from `github.com/dugshub/agent-tui` → `github.com/dugshub/agentic-tui`.

**Examples** (`_examples/`):

Source: `packages/agent-tui/_examples/`
```
packages/agentic-tui/_examples/
  minimal/main.go           ← 24-line HTTP integration
  stdio-python/             ← Python JSON-RPC backend
  stdio-typescript/         ← TypeScript JSON-RPC backend
  custom-commands/main.go   ← Registering custom slash commands
  custom-theme/main.go      ← Custom theme
  demo/main.go              ← Demo mode
  gallery/main.go           ← Component gallery
```

Update imports. Verify each example compiles: `go build ./_examples/minimal/`

**PROTOCOL.md**:

Contents (from spec):
1. SSE event vocabulary with full JSON payload schemas
2. JSON-RPC 2.0 method definitions (params, results, error codes)
3. HTTP endpoint conventions (paths, methods, headers, SSE wire format)
4. Display type registry (`generic`, `diff`, `code`, `bash`)
5. Streaming lifecycle (connect → stream events → done/error)
6. Backward compatibility guarantees (event name aliases, optional fields)
7. "Implementing a backend in 30 minutes" quick-start

Event table for PROTOCOL.md:

| Event | Legacy Aliases | Data | Purpose |
|-------|---------------|------|---------|
| `message.delta` | `agent.message.chunk` | `{"delta": "..."}` | Streaming text |
| `message.complete` | `agent.message.complete` | `{"content", "input_tokens", "output_tokens"}` | Message done |
| `thinking` | `agent.reasoning` | `{"content": "..."}` | Reasoning |
| `tool.start` | `agent.tool.start`, `tool_start` | `{"tool_call_id", "tool_name", "display_type", "arguments"}` | Tool begins |
| `tool.end` | `agent.tool.end`, `tool_end` | `{"tool_call_id", "result", "error", "duration_ms", "display_type"}` | Tool ends |
| `tool.rejected` | `agent.tool.rejected` | `{"tool_name", "reason"}` | Safety gate |
| `error` | `agent.error` | `{"error_type", "message"}` | Fatal error |
| `done` | -- | `{}` | Stream complete |

## Verification

- [ ] `go build ./...` passes (entire package including examples)
- [ ] `go test ./...` passes (all tests)
- [ ] `go vet ./...` passes
- [ ] Each example compiles independently
- [ ] `PROTOCOL.md` exists and covers all event types
- [ ] Contract test for HTTP validates: listAgents, createConversation, sendMessage streaming
- [ ] Contract test for stdio validates: listAgents, createConversation, sendMessage streaming
- [ ] No imports reference `github.com/dugshub/agent-tui` (old module) or `github.com/dugshub/stack-bench`

## Notes

- This issue is the final gate — if all verification passes here, EP-017 is complete
- The contract tests are helpers for backend implementors, not integration tests against a live backend
- PROTOCOL.md is the document external developers will read first
