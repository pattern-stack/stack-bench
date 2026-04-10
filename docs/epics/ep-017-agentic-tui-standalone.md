---
id: EP-017
title: agentic-tui standalone package
status: planning
created: 2026-04-09
target:
---

# agentic-tui Standalone Package

## Objective

Extract the TUI from PR #198 into a standalone, language-agnostic Go package
at `packages/agentic-tui/` (module `github.com/dugshub/agentic-tui`). The
package must preserve PR #198's exact visual output while adding main's
infrastructure (public API, JSON-RPC stdio, contract tests, examples). Any
agent framework in any language can drive it via HTTP/SSE or JSON-RPC.

## Issues

| ID | Title | Status | Branch | Depends On |
|----|-------|--------|--------|------------|
| SB-058 | Scaffold standalone package from PR #198 | draft | | -- |
| SB-059 | Unify types into single source | draft | | SB-058 |
| SB-060 | Port public API layer from main | draft | | SB-059 |
| SB-061 | Port JSON-RPC stdio client from main | draft | | SB-059 |
| SB-062 | Port HTTP client enhancements from main | draft | | SB-059 |
| SB-063 | Port service lifecycle from main | draft | | SB-059 |
| SB-064 | Contract tests, examples, PROTOCOL.md | draft | | SB-061, SB-062 |

## Dependency Graph

```
SB-058 (scaffold)
  └── SB-059 (unify types)
        ├── SB-060 (public API)
        ├── SB-061 (stdio client)    ──┐
        ├── SB-062 (HTTP enhancements) ├── SB-064 (tests + examples + protocol)
        └── SB-063 (service lifecycle) │
                                       ┘
```

After SB-059, issues SB-060 through SB-063 can run in parallel.
SB-064 depends on SB-061 + SB-062 (contract tests validate both transports).

## Critical Constraint

PR #198 (`origin/dugshub/message-parts/2-part-aware-chat`) is the frozen
visual truth. Rendering code (chat/view.go, ui/components/, ui/theme/,
ui/markdown.go) must be copied verbatim from that branch — only import path
rewrites are acceptable changes. See spec for full rationale.

## Acceptance Criteria

- [ ] `packages/agentic-tui/` exists as standalone Go module
- [ ] `go build ./...` passes from `packages/agentic-tui/`
- [ ] `go test ./...` passes from `packages/agentic-tui/`
- [ ] Demo mode renders identically to PR #198
- [ ] Public `tui.Client` interface works with HTTP, Stdio, Stub, and custom backends
- [ ] PROTOCOL.md documents SSE events, JSON-RPC methods, HTTP endpoints
- [ ] Contract tests validate both HTTP and stdio transports
- [ ] Examples exist for minimal, stdio-python, stdio-typescript, custom-commands, custom-theme

## Notes

- Spec: `.claude/specs/2026-04-09-agentic-tui-standalone.md`
- PR #198: pattern-stack/stack-bench#198
- Repo extraction (to separate GitHub repo) and CI/release are post-epic ship tasks
