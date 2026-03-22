---
id: SB-021
title: Spinner + StatusBlock components
status: ready
epic: EP-006
depends_on: [SB-014]
branch:
pr:
stack: cli-components
stack_index: 8
created: 2026-03-22
---

# Spinner + StatusBlock Components

## Summary

Build the Spinner atom (animated braille indicator wrapping tea.Model) and the StatusBlock molecule (Spinner + verb text + optional elapsed/count badges). These replace the current inline `...` streaming indicator with a proper animated component.

## Scope

What's in:
- `atoms/spinner.go` — braille animation, tea.Model with Update/Init/View
- `molecules/statusblock.go` — composes Spinner + TextBlock(verb) + Badge(elapsed) + Badge(count)
- Wire Spinner's tick into the parent Bubble Tea message loop
- Tests for both

What's out:
- Replacing the current `...` indicator in the chat view (separate integration task)

## Implementation

```
app/cli/internal/ui/components/atoms/spinner.go
app/cli/internal/ui/components/atoms/spinner_test.go
app/cli/internal/ui/components/molecules/statusblock.go
app/cli/internal/ui/components/molecules/statusblock_test.go
```

## Verification

- [ ] Spinner cycles through braille frames on tick
- [ ] StatusBlock renders verb + optional badges
- [ ] Tests pass with `go test ./internal/ui/components/...`
