---
id: SB-054
title: Sidebar empty state — placeholder stack connector and file tree
status: ready
epic: EP-011
depends_on: [SB-053]
branch:
pr:
stack:
stack_index: 2
created: 2026-03-25
---

# Sidebar empty state

## Summary

When no stacks exist, the sidebar should show a meaningful empty state rather than being blank. Show the stack header area with "No stacks" or a connection status indicator, an empty stack connector zone, and the file tree area with a placeholder message.

## Scope

What's in:
- StackSidebar empty variant (no items, no stack name)
- Stack connector area: subtle placeholder ("No branches")
- File tree area: empty state message
- GitHub connection status indicator (green dot + username if connected)

What's out:
- Stack creation UI
- Import from GitHub flow

## Implementation

Key files to create or modify:

```
app/frontend/src/components/organisms/StackSidebar/StackSidebar.tsx
app/frontend/src/components/molecules/StackConnector/ (empty state)
```

Reference: `pattern-stack/frontend-patterns` EmptyState atom for pattern guidance.

## Verification

- [ ] Sidebar renders with no stack data
- [ ] Shows GitHub connection status
- [ ] No blank/broken areas
