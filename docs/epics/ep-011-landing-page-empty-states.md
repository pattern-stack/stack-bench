---
id: EP-011
title: Landing Page & Empty States
status: planning
created: 2026-03-25
target: 2026-04-01
---

# Landing Page & Empty States

## Objective

After onboarding (GitHub connected, app installed), users should land on the main AppShell — not a separate empty state page. The AppShell, sidebar, header, and content area all need graceful loading and empty states so the app feels complete even with zero stacks.

## Context

Currently, completing onboarding drops users into `AuthenticatedApp` which immediately tries to load a stack. With no stacks, it shows a red error. The fix is to make every zone of the AppShell handle the empty case with purpose — showing connection status, guiding toward first stack creation, and feeling like a real workspace rather than a broken page.

## Design Direction

- Dark theme, IBM Plex Sans/Mono, existing design tokens
- Borrow patterns from `pattern-stack/frontend-patterns` where useful (Skeleton, EmptyState atoms)
- Empty states should feel like the app is ready and waiting, not broken
- Loading states use skeleton shimmer consistent with existing `HeaderSkeleton`, `DiffSkeleton`, `TreeSkeleton`

## Issues

- SB-053: AppShell empty mode — render AppShell with empty sidebar + content when no stacks
- SB-054: Sidebar empty state — stack connector placeholder, empty file tree
- SB-055: Content area empty state — centered message in main content zone
- SB-056: Header empty state — minimal header when no branch is selected
- SB-057: Onboarding → AppShell flow — skip separate empty state page, land on AppShell after onboarding
