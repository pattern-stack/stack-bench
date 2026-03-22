---
id: SB-022
title: ToolCallBlock + DiffBlock components
status: ready
epic: EP-006
depends_on: [SB-014, SB-021]
branch:
pr:
stack: cli-components
stack_index: 9
created: 2026-03-22
---

# ToolCallBlock + DiffBlock Components

## Summary

Build the ToolCallBlock molecule (tool invocation display with status and collapsible I/O) and the DiffBlock molecule (colored diff with +/- lines). These are the core rendering components for agent tool execution output.

## Scope

What's in:
- `molecules/toolcallblock.go` — Badge(tool name) + Badge(status) + collapsible CodeBlock for input/output
- `molecules/diffblock.go` — Badge(filename) + colored diff lines (green for added, red for removed, dim for context)
- ToolStatus enum: Running, Success, Error
- DiffLineType enum: Added, Removed, Context
- Tests for both

What's out:
- Wiring to actual backend tool call events (separate integration)
- Collapse/expand interaction (render both states, caller manages which)

## Implementation

```
app/cli/internal/ui/components/molecules/toolcallblock.go
app/cli/internal/ui/components/molecules/toolcallblock_test.go
app/cli/internal/ui/components/molecules/diffblock.go
app/cli/internal/ui/components/molecules/diffblock_test.go
```

## Verification

- [ ] ToolCallBlock renders tool name, status badge, input/output
- [ ] ToolCallBlock renders differently for Running/Success/Error
- [ ] DiffBlock colors added lines green, removed lines red
- [ ] Tests pass with `go test ./internal/ui/components/...`
