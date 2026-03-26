---
id: SB-056
title: Header empty state — minimal header with no branch selected
status: ready
epic: EP-011
depends_on: [SB-053]
branch:
pr:
stack:
stack_index: 4
created: 2026-03-25
---

# Header empty state

## Summary

PRHeader currently requires a title, baseBranch, headBranch, and status. When no branch is selected (empty workspace), show a minimal header that maintains the layout but displays placeholder content — app name or "Select a branch", no diff stats toolbar.

## Scope

What's in:
- PRHeader empty/placeholder variant
- Maintains header height and border for layout consistency
- Hides diff toolbar (file count, collapse/expand, comment toggle)
- Shows app branding or neutral placeholder text

What's out:
- New header component — extend existing PRHeader

## Implementation

Key files to create or modify:

```
app/frontend/src/components/molecules/PRHeader/PRHeader.tsx (add empty variant)
app/frontend/src/components/templates/AppShell/AppShell.tsx (render empty header when no activeBranch)
```

## Verification

- [ ] Header renders without branch data
- [ ] Consistent height with populated header
- [ ] No diff toolbar shown when empty
