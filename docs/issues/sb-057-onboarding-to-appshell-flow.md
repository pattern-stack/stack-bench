---
id: SB-057
title: Onboarding → AppShell flow — land on main app after onboarding
status: ready
epic: EP-011
depends_on: [SB-053, SB-054, SB-055, SB-056]
branch:
pr:
stack:
stack_index: 5
created: 2026-03-25
---

# Onboarding → AppShell flow

## Summary

Wire the complete post-onboarding flow. After GitHub is connected and the app is installed, the user should land directly on the AppShell in empty mode — sidebar showing connection status, content area showing the empty state, header in placeholder mode. Remove the standalone EmptyState page redirect.

## Scope

What's in:
- Onboarding "Continue to Stack Bench" navigates to `/` which renders AppShell
- App.tsx: when `!data && !loading && !error`, render AppShell in empty mode (not a separate page)
- Clean up the standalone EmptyState.tsx if fully superseded
- Verify the onboarding → main app transition is smooth (no flash, no redirect loop)

What's out:
- CLI auth flow
- Stack creation / import features
- Changes to the onboarding steps themselves

## Implementation

Key files to create or modify:

```
app/frontend/src/App.tsx (AuthenticatedApp — empty mode AppShell)
app/frontend/src/pages/OnboardingPage.tsx (verify navigation target)
app/frontend/src/components/organisms/EmptyState.tsx (inline into AppShell or remove)
```

## Verification

- [ ] Register → onboarding → connect GitHub → install app → land on AppShell
- [ ] AppShell shows empty sidebar, empty header, empty content area
- [ ] GitHub connection status visible in sidebar
- [ ] No redirect loops or flash of error state
- [ ] Refreshing `/` stays on AppShell (not redirected back to onboarding)
