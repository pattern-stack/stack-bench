---
id: SB-053
title: AppShell empty mode — render shell with no stacks
status: ready
epic: EP-011
depends_on: []
branch:
pr:
stack:
stack_index: 1
created: 2026-03-25
---

# AppShell empty mode

## Summary

Make AppShell renderable without any stack data. Currently it requires a full stack detail payload (stackName, trunk, items, activeBranch, etc). Add an empty/no-data mode where the shell renders its layout (sidebar + header + content) with placeholder content in each zone.

## Scope

What's in:
- Make AppShell props optional or provide an empty-state variant
- Render the 3-column layout (sidebar, main, agent panel collapsed) even with no data
- Delegate empty content to child components (SB-054, SB-055, SB-056)

What's out:
- Actual data fetching or stack creation
- CLI integration

## Implementation

Key files to create or modify:

```
app/frontend/src/components/templates/AppShell/AppShell.tsx
app/frontend/src/App.tsx (AuthenticatedApp — render AppShell in empty mode instead of EmptyState page)
```

## Verification

- [ ] AppShell renders without crashing when no stack data provided
- [ ] 3-column layout visible with empty sidebar, header, content
- [ ] No red error text or "No data" message
