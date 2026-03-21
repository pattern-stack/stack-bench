---
id: SB-038
title: App Shell + Chrome (layout, tabs, PR header)
status: draft
epic: EP-006
depends_on: [SB-037]
branch:
pr:
stack: frontend-mvp
stack_index: 4
created: 2026-03-21
---

# App Shell + Chrome (layout, tabs, PR header)

## Summary

Build the app layout that composes StackSidebar with the main content area. The main area shows the selected branch's PR header, a tab bar, and a content panel. This wires the sidebar selection to the detail view.

## Scope

What's in:
- `TabBar` molecule — horizontal row of Tab atoms with active state management, renders in main area below PR header
- `PRHeader` molecule — PR title (h2), branch-to-branch info (mono, with arrow), PR description text
- `BranchMeta` atom — base branch name + arrow + head branch name, monospace, accent-colored
- `ActionBar` molecule — status indicator on left (draft/local/open icon + label), action buttons on right. Pinned to bottom of main area.
- `AppShell` organism — full page flexbox layout: StackSidebar (fixed left) + main area (flex column: PRHeader → TabBar → content slot → ActionBar)
- Route setup: single route for now, stack ID from URL or hardcoded for MVP
- Selection state: clicking branch in sidebar updates PRHeader, tab content

What's out:
- Multiple routes / page navigation
- "Ask Claude to revise" button functionality
- "Mark ready & push" button functionality (visible but inert)

## Implementation

Key files to create or modify:

```
app/frontend/src/
  App.tsx                              # Mount AppShell, manage selection state
  components/
    atoms/
      BranchMeta/
        BranchMeta.tsx
        index.ts
    molecules/
      TabBar/
        TabBar.tsx
        index.ts
      PRHeader/
        PRHeader.tsx
        index.ts
      ActionBar/
        ActionBar.tsx
        index.ts
    organisms/
      AppShell/
        AppShell.tsx
        index.ts
```

## Verification

- [ ] Full page renders: sidebar left, main area right, no scroll on body
- [ ] Selecting a branch in sidebar updates PR header with title and branch info
- [ ] Tab bar shows "Files changed" tab with count (active by default)
- [ ] Action bar pinned to bottom with status text and placeholder buttons
- [ ] Layout is full viewport height, main area scrolls independently

## Notes

Tab bar will initially show only "Files changed" with a count. Conversation tab will be added later when CLI conversation work is ported (EP-002).
