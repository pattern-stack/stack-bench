---
id: SB-023
title: ConfirmPrompt + RadioSelect components
status: ready
epic: EP-006
depends_on: [SB-014]
branch:
pr:
stack: cli-components
stack_index: 10
created: 2026-03-22
---

# ConfirmPrompt + RadioSelect Components

## Summary

Build the ConfirmPrompt molecule (binary yes/no choice for agent approvals) and the RadioSelect molecule (list selection with cursor for agent/conversation picking). These are the core interaction components for human-in-the-loop agent workflows.

## Scope

What's in:
- `molecules/confirmprompt.go` — TextBlock(question) + Badge(options) with selected highlight
- `molecules/radioselect.go` — TextBlock(label) + list with Icon(cursor) + TextBlock(description)
- Both are pure render functions — state (selected index) managed by caller
- Tests for both

What's out:
- Keyboard handling for selection (caller's responsibility)
- Wiring to agent approval flow (separate integration)

## Implementation

```
app/cli/internal/ui/components/molecules/confirmprompt.go
app/cli/internal/ui/components/molecules/confirmprompt_test.go
app/cli/internal/ui/components/molecules/radioselect.go
app/cli/internal/ui/components/molecules/radioselect_test.go
```

## Verification

- [ ] ConfirmPrompt renders question with highlighted selected option
- [ ] RadioSelect renders items with cursor on selected item
- [ ] Both render through atoms (Badge, Icon, TextBlock)
- [ ] Tests pass with `go test ./internal/ui/components/...`
