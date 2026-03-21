---
id: SB-036
title: Shared atoms (Badge, Icon, Button, Collapsible, Tab)
status: draft
epic: EP-006
depends_on: [SB-035]
branch:
pr:
stack: frontend-mvp
stack_index: 2
created: 2026-03-21
---

# Shared atoms (Badge, Icon, Button, Collapsible, Tab)

## Summary

Port the core atom components from dealbrain2's component library into stack-bench. Keep the structure and API surface, completely restyle with the new dark design system. These are generic, reusable primitives — no domain knowledge.

## Scope

What's in:
- `Badge` — pill label with size variants (sm, default) and semantic color variants (default/muted, green, red, purple, yellow, accent)
- `Icon` — SVG icon component with size variants. Subset of icons: chevron-right, chevron-down, check, x, plus, file, folder, git-branch, git-commit, circle, message-square
- `Button` — primary (green) and subtle (ghost/border) variants with sizes
- `Collapsible` — Radix-based expand/collapse with animation
- `Tab` + `CountBadge` — tab label with optional count pill, active/inactive states with bottom border indicator

What's out:
- Domain-specific components (StatusBadge, DiffBadge — those are SB-037/039)
- Form inputs, modals, tooltips
- Dealbrain's monochromatic color scheme — we use semantic colors

## Implementation

Key files to create or modify:

```
app/frontend/src/components/atoms/
  Badge/
    Badge.tsx
    index.ts
  Icon/
    Icon.tsx
    icons/                             # SVG files (subset from dealbrain)
    index.ts
  Button/
    Button.tsx
    index.ts
  Collapsible/
    Collapsible.tsx
    index.ts
  Tab/
    Tab.tsx
    CountBadge.tsx
    index.ts
  index.ts                             # barrel export
```

## Verification

- [ ] Each atom renders correctly in isolation (manual browser check or simple test page)
- [ ] Badge renders all color variants on dark background
- [ ] Collapsible animates open/close
- [ ] Tab shows active state with accent bottom border
- [ ] No dealbrain-specific styling (orange brand, Figtree font, light theme tokens)

## Notes

Source reference: `/Users/dug/Projects/dealbrain2/apps/frontend/src/components/atoms/`
Styling approach: Tailwind 4 utility classes + CVA for variants, referencing CSS custom properties from SB-035 design tokens.
