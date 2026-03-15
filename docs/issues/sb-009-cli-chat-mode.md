---
id: SB-009
title: CLI chat mode (restructure + clean UI)
status: in-progress
epic: EP-002
depends_on: []
branch: dugshub/sb-cli-chat/1-cli-chat-mode
pr: 17
stack: sb-cli-chat
stack_index: 1
created: 2026-03-14
---

# CLI Chat Mode

## Summary

Restructure the 1,950-line `main.go` into Go packages. Strip fake data, build a clean chat UI ready for backend wiring.

## Scope

What's in:
- Split into packages: `internal/app/`, `internal/chat/`, `internal/ui/`, `internal/api/`
- Clean chat view — messages, input bar, streaming rendering
- Agent selection on startup
- Strip fake data

What's out:
- Backend API calls (SB-010)
- Stacks/Streams tabs (future)

## Implementation

```
cli/internal/app/model.go
cli/internal/chat/model.go
cli/internal/chat/view.go
cli/internal/ui/styles.go
cli/internal/api/client.go
cli/main.go
```

## Verification

- [ ] `just dev` launches chat UI
- [ ] Chat renders messages with streaming text
- [ ] No fake data
- [ ] `just build` works

## Notes

GH: #11
