---
id: SB-055
title: Content area empty state — centered welcome in main zone
status: ready
epic: EP-011
depends_on: [SB-053]
branch:
pr:
stack:
stack_index: 3
created: 2026-03-25
---

# Content area empty state

## Summary

The main content area (where diffs normally render) should show a centered, minimal empty state when no branch is selected or no stacks exist. Use the stacked-layers icon and a brief message guiding the user toward `stack push` or browsing repos.

## Scope

What's in:
- Centered empty state within the main content zone of AppShell
- Stacked-layers SVG icon (matches the product concept)
- Brief copy: "No stacks yet" + hint about `stack push`
- Reuse/adapt the EmptyState component (organisms) for in-shell use

What's out:
- Full-page standalone empty state (remove the current EmptyState.tsx page-level component)
- Interactive elements (create stack button, import flow)

## Implementation

Key files to create or modify:

```
app/frontend/src/components/organisms/EmptyState.tsx (refactor to content-area variant)
app/frontend/src/App.tsx (pass empty state as children to AppShell)
```

## Verification

- [ ] Empty state renders inside AppShell content area
- [ ] Vertically and horizontally centered
- [ ] Matches design tokens (dark theme, IBM Plex, muted text)
