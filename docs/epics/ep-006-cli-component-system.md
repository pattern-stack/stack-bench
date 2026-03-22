---
id: EP-006
title: CLI Component System
status: active
created: 2026-03-21
target: 2026-04-04
---

# CLI Component System

## Objective

Build an atoms-and-molecules component layer for the Go/Bubble Tea CLI so that every piece of rendered UI is a composable, token-driven, theme-aware building block. Replace inline styling with structured components that route through `theme.Resolve()`. Stand up all components needed for agent interaction (tool calls, approvals, diffs).

## Issues

| ID | Title | Status | Branch/PR |
|----|-------|--------|-----------|
| SB-014 | Core atoms | done | #55 |
| SB-015 | Chat molecules | done | #56 |
| SB-016 | Chat view migration + viewport | done | #57 |
| SB-017 | Goldmark markdown renderer | done | #58 |
| SB-018 | Syntax highlighting (chroma) | done | #59 |
| SB-019 | Table rendering | done | #60 |
| SB-020 | CodeBlock polish + demo improvements | done | #61 |
| SB-021 | Spinner + StatusBlock | ready | — |
| SB-022 | ToolCallBlock + DiffBlock | ready | — |
| SB-023 | ConfirmPrompt + RadioSelect | ready | — |
| SB-024 | Deprecate ui/styles.go | ready | — |

## Acceptance Criteria

- [ ] All atoms render through theme tokens — no direct lipgloss.Style construction in views
- [ ] Markdown renders through goldmark with syntax highlighting and table support
- [ ] Tool calls render with name, status, collapsible I/O
- [ ] Confirmation prompts support y/n agent approval flow
- [ ] Spinner animates for async operations
- [ ] ui/styles.go removed, all callers migrated
- [ ] Demo mode exercises all component types

## Notes

- Stack: `cli-components` (7 branches submitted as PRs #55-#61)
- Spec: `docs/specs/2026-03-21-cli-component-system.md`
- Proposal for agent integration: `docs/proposals/cli-agentic-patterns-integration.md`
