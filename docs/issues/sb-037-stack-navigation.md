---
id: SB-037
title: Stack Navigation (sidebar + branch list)
status: draft
epic: EP-006
depends_on: [SB-036]
branch:
pr:
stack: frontend-mvp
stack_index: 3
created: 2026-03-21
---

# Stack Navigation (sidebar + branch list)

## Summary

Build the stack sidebar — the left panel that shows all branches in a stack with their status, diff stats, and visual connectors. This is the primary navigation for the app. Powered by `GET /api/v1/stacks/{id}/detail`.

## Scope

What's in:
- `StackDot` atom — colored circle (green=merged, blue=active, gray=default) with vertical connector line segment above/below
- `StatusBadge` molecule — extends Badge with domain-specific presets: draft, local, open, review, merged
- `DiffStat` atom — inline `+N -N` with green/red coloring
- `StackItem` molecule — StackDot + title + StatusBadge + DiffStat. Click handler, active/hover states.
- `StackConnector` molecule — vertical connected list of StackItems with continuous line through dots. First/last item line truncation.
- `StackSidebar` organism — header (stack name + repo label), StackConnector list. Fixed-width (320px) left panel.
- Wire to `store.stacks` from generated hooks (or direct API call to `/api/v1/stacks/{id}/detail`)

What's out:
- Sidebar file tree / commits sub-tabs (v2 feature, future)
- Collapsible sidebar sections
- Stack switching (single stack view for MVP)

## Implementation

Key files to create or modify:

```
app/frontend/src/components/
  atoms/
    StackDot/
      StackDot.tsx
      index.ts
    DiffStat/
      DiffStat.tsx
      index.ts
  molecules/
    StatusBadge/
      StatusBadge.tsx
      index.ts
    StackItem/
      StackItem.tsx
      index.ts
    StackConnector/
      StackConnector.tsx
      index.ts
  organisms/
    StackSidebar/
      StackSidebar.tsx
      index.ts
```

## Verification

- [ ] Sidebar renders with stack name and repo in header
- [ ] Branches display in correct stack order with connected dots
- [ ] Active branch highlighted with accent color
- [ ] Merged branches show green dot, draft/local show appropriate badges
- [ ] Clicking a branch triggers selection callback
- [ ] Diff stats show when PR data is available

## Notes

State machine values for StatusBadge mapping:
- Branch states: created, pushed, reviewing, ready, submitted, merged
- PR states: draft, open, approved, merged, closed
