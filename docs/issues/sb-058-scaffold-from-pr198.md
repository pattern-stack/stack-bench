---
id: SB-058
title: Scaffold standalone package from PR #198
status: draft
epic: EP-017
depends_on: []
branch: dug/agentic-tui/1-scaffold
pr:
stack: agentic-tui
stack_index: 1
pr198_source: origin/dugshub/message-parts/2-part-aware-chat
created: 2026-04-09
---

# Scaffold standalone package from PR #198

## Summary

Copy all TUI code from PR #198's `app/cli/` into `packages/agentic-tui/`
with restructured imports. This is a pure file-move + import-path rewrite
with zero logic changes. The rendering code is frozen — only import paths
change.

## Scope

What's in:
- Copy `app/cli/internal/` files from `origin/dugshub/message-parts/2-part-aware-chat`
- Copy `app/cli/fixtures/` → `packages/agentic-tui/demo/fixtures/`
- Copy `app/cli/themes/` → `packages/agentic-tui/themes/` (YAML-loaded themes)
- Create `packages/agentic-tui/go.mod` with module `github.com/dugshub/agentic-tui`
- Rewrite all imports from `github.com/dugshub/stack-bench/app/cli/internal/` → `github.com/dugshub/agentic-tui/internal/`
- Split `internal/api/` → `internal/httpclient/` (client code) + `internal/sse/` (parser + event types)
- Drop `BranchConversation` from client interface (stack-bench-specific)

What's out:
- `app/cli/main.go` — this becomes an example later, not part of the library
- Type unification (SB-059)
- Any rendering logic changes

## Implementation

Source (read via `git show origin/dugshub/message-parts/2-part-aware-chat:<path>`):
```
app/cli/internal/api/client.go     → internal/httpclient/client.go
app/cli/internal/api/types.go      → internal/sse/types.go (temporary, unified in SB-059)
app/cli/internal/api/sse.go        → internal/sse/parse.go
app/cli/internal/api/demo.go       → internal/demo/client.go
app/cli/internal/app/model.go      → internal/app/model.go
app/cli/internal/app/demo.go       → internal/app/demo.go
app/cli/internal/app/gallery.go    → internal/app/gallery.go
app/cli/internal/app/spinners.go   → internal/app/spinners.go
app/cli/internal/chat/model.go     → internal/chat/model.go
app/cli/internal/chat/view.go      → internal/chat/view.go
app/cli/internal/command/          → internal/command/
app/cli/internal/service/          → internal/service/
app/cli/internal/ui/               → internal/ui/
app/cli/fixtures/                  → demo/fixtures/
app/cli/themes/                    → themes/
```

New `go.mod`:
```
module github.com/dugshub/agentic-tui

go 1.25.0

require (
    charm.land/bubbles/v2 v2.0.0
    charm.land/bubbletea/v2 v2.0.2
    charm.land/lipgloss/v2 v2.0.2
    github.com/alecthomas/chroma/v2 v2.23.1
    github.com/yuin/goldmark v1.7.17
    gopkg.in/yaml.v3 v3.0.1
)
```

Copy `go.sum` from PR #198's `app/cli/go.sum` and update module paths.

## Verification

- [ ] `cd packages/agentic-tui && go build ./...` passes
- [ ] `cd packages/agentic-tui && go vet ./...` passes
- [ ] All existing tests pass: `go test ./...`
- [ ] No files import `github.com/dugshub/stack-bench` (grep confirms zero hits)
- [ ] `BranchConversation` does not appear in any client interface

## Notes

- Read PR #198 files via: `git show origin/dugshub/message-parts/2-part-aware-chat:<path>`
- The `themes/` directory contains `dark.yml`, `light.yml`, and `embed.go` for YAML-loaded themes — this is the PR #198 theme system, preserve it exactly
- PR #198 uses `PartType string` constants and struct-based `ToolCallPart` — keep this model
