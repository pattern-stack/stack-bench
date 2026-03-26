---
title: "EP-011: Landing Page & Empty States"
date: 2026-03-25
status: draft
branch:
depends_on: []
adrs: []
---

# EP-011: Landing Page & Empty States

## Goal

Make every zone of the AppShell (sidebar, header, content area) handle the zero-data case gracefully, so users land on a real workspace after onboarding -- not a standalone empty page or a red error. The AppShell should render its full 3-column layout with purposeful empty states in each zone, showing connection status and guiding toward first stack creation.

## Current State Analysis

Today, `AuthenticatedApp` in `App.tsx` follows this flow:

1. Calls `useStackDetail(selectedStackId)` -- but `selectedStackId` starts as `undefined`, so the query is **disabled** (`enabled: !!stackId`)
2. Since the query never fires, `data` stays `null`, `loading` is `false`, `error` is `null`
3. The `!data` guard at line 181 renders `<EmptyState />` -- a standalone full-page component
4. `EmptyState` is a centered card with a stacked-layers icon, GitHub status, and a `stack push` hint

**Problems:**
- The `EmptyState` component is a full-page takeover, not inside the AppShell layout
- No sidebar, no header, no familiar workspace chrome
- Users who just completed onboarding see a completely different UI from the app they'll eventually use
- The `loading` state (line 165) shows a bare "Loading..." text, not the AppShell skeleton
- The `error` state (line 173) shows raw red error text

**Key components that need empty variants:**
- `AppShell` (`components/templates/AppShell/AppShell.tsx`) -- all props are required, no empty mode
- `StackSidebar` (`components/organisms/StackSidebar/StackSidebar.tsx`) -- requires `stackName`, `items`, `summary`, etc.
- `PRHeader` (`components/molecules/PRHeader/PRHeader.tsx`) -- requires `title`, `baseBranch`, `headBranch`
- `StackHeader` (`components/molecules/StackHeader/StackHeader.tsx`) -- requires `stackName`, `trunk`, `summary`

## Domain Model

No new backend models or services. This is entirely frontend work.

**Existing components affected:**

| Component | Layer | Current Role |
|-----------|-------|--------------|
| `AppShell` | Template | 3-column layout orchestrator |
| `StackSidebar` | Organism | Sidebar with stack list + file tree |
| `StackHeader` | Molecule | Stack name, trunk badge, toolbar |
| `StackConnector` | Molecule | Branch list visualization |
| `PRHeader` | Molecule | Branch header with diff toolbar |
| `EmptyState` | Organism | Standalone full-page empty state |
| `App` / `AuthenticatedApp` | Page | Root data-fetching + routing |

## Implementation Phases

| Phase | What | Issue | Depends On |
|-------|------|-------|------------|
| 1 | AppShell empty mode -- render shell with no data | SB-053 | -- |
| 2a | Sidebar empty state -- placeholder stack connector + file tree | SB-054 | Phase 1 |
| 2b | Content area empty state -- centered message in main zone | SB-055 | Phase 1 |
| 2c | Header empty state -- minimal header with no branch | SB-056 | Phase 1 |
| 3 | Onboarding to AppShell flow -- wire the full transition | SB-057 | Phases 2a-2c |

Phases 2a/2b/2c are independent and can be built in parallel.

## Phase Details

### Phase 1: AppShell empty mode (SB-053)

The core change: make `AppShell` renderable when there is no stack data. Instead of requiring all props, support an "empty" configuration where the shell renders its 3-column layout with empty-state children in each zone.

#### Strategy: Separate empty props type via union

Rather than making every prop optional (which creates a mess of `?? fallback` everywhere), use a discriminated approach: `AuthenticatedApp` renders `AppShell` in empty mode by passing empty-state-specific props, while the data-loaded path stays unchanged.

#### File: `app/frontend/src/components/templates/AppShell/AppShell.tsx`

**Changes:**
- Add a new `AppShellEmptyProps` interface with minimal required props (just `children` for content area, `agentOpen`/`onAgentToggle` for the agent panel toggle)
- Create a new `AppShellEmpty` internal component that renders the same 3-column `<div className="flex h-screen ...">` layout but with:
  - `<StackSidebarEmpty />` in the sidebar slot (from SB-054)
  - Empty header slot (from SB-056)
  - `{children}` in the content area (from SB-055)
  - `<AgentPanel>` in its usual position (collapsed)
- Export both `AppShell` and `AppShellEmpty`

Alternatively (and simpler for this codebase): just make `AppShell` props optional and have the component handle empty state internally. The template already imports `StackSidebar` and `PRHeader` directly, so it can conditionally render empty variants.

**Recommended approach -- make props partially optional:**

```
interface AppShellProps {
  // These become optional for empty mode
  stackName?: string;
  trunk?: string;
  items?: StackConnectorItem[];
  activeIndex?: number;
  onSelect?: (index: number) => void;
  activeBranch?: BranchWithPR | null;
  summary?: StackSummary;
  activityEntries?: ActivityLogEntry[];
  // ... (all data-dependent props become optional)

  // These stay required (layout/interaction)
  agentOpen: boolean;
  onAgentToggle: () => void;
  children?: ReactNode;
}
```

Then in the render:
- If `stackName` is undefined, render `<StackSidebarEmpty />` instead of `<StackSidebar />`
- If `activeBranch` is undefined, render `<PRHeaderEmpty />` instead of `<PRHeader />`
- The content area already renders `{children}`, which `AuthenticatedApp` controls

**Detect empty mode** via a derived boolean:

```ts
const isEmpty = !stackName;
```

#### File: `app/frontend/src/App.tsx`

**Changes to `AuthenticatedApp`:**
- Remove the `<EmptyState />` full-page fallback at line 181-183
- When `!data` (no stack loaded), render `<AppShell>` with only layout props set + empty-state content as children:

```tsx
if (!data) {
  return (
    <AppShell
      agentOpen={agentOpen}
      onAgentToggle={() => setAgentOpen((prev) => !prev)}
    >
      <ContentEmptyState />
    </AppShell>
  );
}
```

This gives the AppShell the signal to render empty variants for sidebar and header internally.

#### Files to create/modify

| File | Action | Description |
|------|--------|-------------|
| `app/frontend/src/components/templates/AppShell/AppShell.tsx` | Modify | Make data props optional, add empty-mode rendering |
| `app/frontend/src/App.tsx` | Modify | Replace `<EmptyState />` with empty-mode `<AppShell>` |

---

### Phase 2a: Sidebar empty state (SB-054)

When no stack data exists, the sidebar should show: a GitHub connection status indicator, a placeholder stack connector area, and an empty file tree message.

#### File: `app/frontend/src/components/organisms/StackSidebar/StackSidebarEmpty.tsx` (new)

A lightweight empty variant of `StackSidebar` that renders:

1. **Header zone** -- app name "Stack Bench" with a git-branch icon, replacing the `StackHeader` which requires stack data. Below it, a GitHub connection status row (green dot + username or "Not connected").

2. **Stack connector zone** -- a muted placeholder area:
   ```
   [git-branch icon]  No branches
   ```
   Styled as a subtle box with `text-[var(--fg-subtle)]`, same height as a single `StackItem` to maintain layout consistency.

3. **File tree zone** -- centered muted text:
   ```
   No files to show
   ```

4. No mode toggle (SidebarModeToggle), no activity log -- these are data-dependent and irrelevant in empty mode.

**Props:** None. `StackSidebarEmpty` calls `useGitHubConnection()` directly (same pattern as the current `EmptyState.tsx`), avoiding prop drilling through `AppShell`.

```ts
function StackSidebarEmpty() {
  const { connected, githubLogin } = useGitHubConnection();
  // ...
}
```

#### File: `app/frontend/src/components/organisms/StackSidebar/index.ts`

**Changes:** Re-export `StackSidebarEmpty`.

#### File: `app/frontend/src/components/templates/AppShell/AppShell.tsx`

**Changes:** Import and render `StackSidebarEmpty` when in empty mode.

#### Files to create/modify

| File | Action | Description |
|------|--------|-------------|
| `app/frontend/src/components/organisms/StackSidebar/StackSidebarEmpty.tsx` | Create | Empty sidebar variant with GitHub status |
| `app/frontend/src/components/organisms/StackSidebar/index.ts` | Modify | Export StackSidebarEmpty |
| `app/frontend/src/components/templates/AppShell/AppShell.tsx` | Modify | Use StackSidebarEmpty in empty mode |
| `app/frontend/src/App.tsx` | Modify | Minor: no GitHub prop changes needed (sidebar handles its own hook) |

---

### Phase 2b: Content area empty state (SB-055)

The main content area should show a centered, minimal empty state when no stacks exist. This replaces the standalone `EmptyState` organism.

#### Reference: `@pattern-stack/frontend-patterns` EmptyState atom

The `EmptyState` atom from `@pattern-stack/frontend-patterns` defines the canonical pattern for empty states in pattern-stack projects. Its interface:

```ts
interface EmptyStateProps {
  variant?: "no-data" | "no-results" | "error" | "loading";
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: { label: string; onClick: () => void };
  secondaryAction?: { label: string; onClick: () => void };
  className?: string;
}
```

Our `ContentEmptyState` should follow this pattern — using `variant="no-data"`, with `title`, `description`, `icon`, and optionally an `action` for future "Import PRs" or "Create stack" CTAs. Even if we don't use the package component directly (our content is more specialized), the prop shape and variant semantics should align.

The same atom pattern should inform `StackSidebarEmpty` (SB-054, `variant="no-data"`) and `PRHeaderEmpty` (SB-056), keeping empty state UX consistent across zones.

#### File: `app/frontend/src/components/organisms/ContentEmptyState/ContentEmptyState.tsx` (new)

A content-area-only empty state component (not full-page). Renders:

1. **Stacked-layers SVG icon** -- reuse the existing SVG from `EmptyState.tsx` (three stacked rectangles)
2. **Heading**: "No stacks yet"
3. **Subtext**: "Stacks will appear here once you push branches or import existing pull requests."
4. **CLI hint**: `stack push` in a styled code block

Layout: `flex items-center justify-center h-full` so it centers within the AppShell content area (not `min-h-screen` like the old standalone version).

**This is essentially the existing `EmptyState` content, extracted from its full-page wrapper and adapted to render inside the content slot of AppShell.**

The status card (GitHub connected, Workspace empty) moves to the sidebar (SB-054), so it does not appear here.

#### File: `app/frontend/src/components/organisms/ContentEmptyState/index.ts` (new)

Standard barrel export.

#### File: `app/frontend/src/components/organisms/EmptyState.tsx`

**Changes:** Delete or mark as deprecated. Its content is split between `ContentEmptyState` (icon + text) and `StackSidebarEmpty` (GitHub status). This file can be removed once SB-057 wires everything together.

#### Files to create/modify

| File | Action | Description |
|------|--------|-------------|
| `app/frontend/src/components/organisms/ContentEmptyState/ContentEmptyState.tsx` | Create | In-shell centered empty state |
| `app/frontend/src/components/organisms/ContentEmptyState/index.ts` | Create | Barrel export |
| `app/frontend/src/components/organisms/index.ts` | Modify | Export ContentEmptyState |
| `app/frontend/src/components/organisms/EmptyState.tsx` | Delete (in SB-057) | Superseded |

---

### Phase 2c: Header empty state (SB-056)

The `PRHeader` currently requires `title`, `baseBranch`, and `headBranch`. When no branch is selected, show a minimal placeholder header that maintains the layout.

#### File: `app/frontend/src/components/molecules/PRHeader/PRHeaderEmpty.tsx` (new)

A placeholder header that:

1. Maintains the same height and border as the populated `PRHeader` (`px-6 py-3 bg-[var(--bg-surface)] border-b border-[var(--border)]`)
2. Shows the app name or neutral text: "Stack Bench" in the title position, with `text-[var(--fg-muted)]` (not semibold)
3. No `BranchMeta`, no `StatusBadge`, no description
4. No diff toolbar row (file count, expand/collapse, comment toggle)
5. No action buttons (restack, mark ready)

```tsx
function PRHeaderEmpty() {
  return (
    <div className="px-6 py-3 bg-[var(--bg-surface)] border-b border-[var(--border)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-lg text-[var(--fg-muted)] leading-tight">
            Stack Bench
          </h2>
          <p className="mt-1 text-sm text-[var(--fg-subtle)]">
            Select a branch to view changes
          </p>
        </div>
      </div>
    </div>
  );
}
```

#### File: `app/frontend/src/components/molecules/PRHeader/index.ts`

**Changes:** Re-export `PRHeaderEmpty`.

#### File: `app/frontend/src/components/templates/AppShell/AppShell.tsx`

**Changes:** When in empty mode, render `<PRHeaderEmpty />` instead of `<PRHeader />` or `<HeaderSkeleton />`.

#### Files to create/modify

| File | Action | Description |
|------|--------|-------------|
| `app/frontend/src/components/molecules/PRHeader/PRHeaderEmpty.tsx` | Create | Minimal placeholder header |
| `app/frontend/src/components/molecules/PRHeader/index.ts` | Modify | Export PRHeaderEmpty |
| `app/frontend/src/components/templates/AppShell/AppShell.tsx` | Modify | Use PRHeaderEmpty in empty mode |

---

### Phase 3: Onboarding to AppShell flow (SB-057)

Wire everything together so the post-onboarding flow is seamless.

#### File: `app/frontend/src/App.tsx`

**Changes to `AuthenticatedApp`:**

1. **Remove the standalone `<EmptyState />` import and fallback.** Replace with:

```tsx
if (!data) {
  return (
    <AppShell
      agentOpen={agentOpen}
      onAgentToggle={() => setAgentOpen((prev) => !prev)}
    >
      <ContentEmptyState />
    </AppShell>
  );
}
```

2. **No GitHub prop drilling needed.** `StackSidebarEmpty` calls `useGitHubConnection()` directly, so `AuthenticatedApp` does not need to fetch or pass GitHub state for the empty case.

3. **Clean up error handling.** The current error state (red text on blank page) should also render inside AppShell for layout consistency. This is a stretch goal for this issue.

4. **Remove the loading full-page fallback** (lines 165-171). Instead, render AppShell with skeleton states. However, this is optional for SB-057 scope -- the primary goal is the empty-data case.

#### File: `app/frontend/src/pages/OnboardingPage.tsx`

**Changes:** Verify `handleFinish` navigates to `/` with `{ replace: true }` -- it already does (line 51). No changes needed.

#### File: `app/frontend/src/components/organisms/EmptyState.tsx`

**Changes:** Delete this file. It is fully superseded by `ContentEmptyState` (content) + `StackSidebarEmpty` (GitHub status).

#### File: `app/frontend/src/components/organisms/index.ts`

**Changes:** Add `ContentEmptyState` export. (Note: `EmptyState` is not currently in the barrel — its import in `App.tsx` is a direct path import that gets removed.)

#### Files to create/modify

| File | Action | Description |
|------|--------|-------------|
| `app/frontend/src/App.tsx` | Modify | Wire empty-mode AppShell, add GitHub hook, remove EmptyState |
| `app/frontend/src/components/organisms/EmptyState.tsx` | Delete | Superseded by ContentEmptyState + StackSidebarEmpty |
| `app/frontend/src/components/organisms/index.ts` | Modify | Update exports |

---

## Complete File Tree

```
app/frontend/src/
  App.tsx                                                    [modify] Wire empty-mode AppShell
  components/
    templates/
      AppShell/
        AppShell.tsx                                         [modify] Support empty mode (optional data props)
    organisms/
      StackSidebar/
        StackSidebarEmpty.tsx                                [create] Empty sidebar with GitHub status
        StackSidebar.tsx                                     [no change]
        index.ts                                             [modify] Export StackSidebarEmpty
      ContentEmptyState/
        ContentEmptyState.tsx                                [create] In-shell centered empty state
        index.ts                                             [create] Barrel export
      EmptyState.tsx                                         [delete] Superseded
      index.ts                                               [modify] Swap EmptyState -> ContentEmptyState
    molecules/
      PRHeader/
        PRHeaderEmpty.tsx                                    [create] Minimal placeholder header
        PRHeader.tsx                                         [no change]
        index.ts                                             [modify] Export PRHeaderEmpty
```

**Summary:** 3 new files, 5 modified files, 1 deleted file.

## Stacking Strategy

These issues form a natural stack:

| Stack Index | Branch | Issue | PR |
|-------------|--------|-------|----|
| 1 | `dug/ep-011-empty-states/1-appshell-empty-mode` | SB-053 | #172 |
| 2 | `dug/ep-011-empty-states/2-sidebar-empty-state` | SB-054 | #173 |
| 3 | `dug/ep-011-empty-states/3-content-area-empty-state` | SB-055 | #174 |
| 4 | `dug/ep-011-empty-states/4-header-empty-state` | SB-056 | #175 |
| 5 | `dug/ep-011-empty-states/5-onboarding-appshell-flow` | SB-057 | #176 |

SB-054/055/056 could theoretically be parallel branches off SB-053, but in a stacked PR workflow they need sequential order. The order above is logical: sidebar first (most visible), then content, then header, then the wiring issue.

## Key Design Decisions

**1. Separate empty components vs. conditional rendering within existing components**

Decision: Create separate `StackSidebarEmpty`, `PRHeaderEmpty`, and `ContentEmptyState` components rather than adding complex conditional logic inside the existing `StackSidebar` and `PRHeader`.

Rationale: The empty variants have fundamentally different prop requirements and render trees. Mixing them into existing components would require making every prop optional and adding fallbacks throughout, harming type safety and readability. Separate components keep the populated-state components clean and make the empty variants easy to evolve independently.

**2. Empty detection in AppShell via optional props**

Decision: Detect empty mode by checking `!stackName` rather than adding an explicit `mode: "empty" | "loaded"` prop.

Rationale: Simpler API. The absence of data is the signal. No boolean or enum to keep in sync.

**3. GitHub status in sidebar, not content area**

Decision: Move the GitHub connection indicator from the standalone `EmptyState` card into the sidebar empty state.

Rationale: The sidebar is persistent chrome -- connection status belongs there. The content area is for the primary message ("No stacks yet" + CLI hint). This also matches how IDEs show environment status in sidebars.

**4. No new atoms or molecules**

Decision: All new components are organisms (sidebar empty, content empty) or molecule variants (header empty). No new design system atoms needed.

Rationale: The existing atom library (Icon, Badge, Skeleton, Button) provides everything needed. The empty states are composed from these existing atoms.

## Testing Strategy

This epic is purely frontend/visual. Testing approach:

**Visual verification (primary -- via `/verify`):**
- Register a new user, complete onboarding, verify landing on AppShell empty mode
- Verify sidebar shows GitHub connection status (green dot + username)
- Verify header shows "Stack Bench" placeholder, no diff toolbar
- Verify content area shows centered "No stacks yet" message
- Verify layout is consistent (sidebar width, header height match populated state)
- Verify no flash of error state or redirect loops on page refresh

**Manual scenarios:**
- [ ] Fresh user: register -> onboarding -> AppShell empty mode
- [ ] Returning user with no stacks: login -> AppShell empty mode
- [ ] User with stacks: login -> AppShell populated mode (regression check)
- [ ] Refresh on `/` while in empty mode stays on empty AppShell
- [ ] Browser back/forward navigation works correctly

**Render smoke tests (minimal):** One per new component to catch regressions when props change:
- `StackSidebarEmpty` renders without throwing
- `ContentEmptyState` renders without throwing
- `PRHeaderEmpty` renders without throwing
- `AppShell` in empty mode (no data props) renders without throwing

These are ~5-line tests. No snapshot or visual regression — just render-and-don't-crash.

## Open Questions

1. Should the empty content area include a "Connect a repository" button or link, or just the CLI hint? Current spec keeps it text-only to match the existing EmptyState behavior.
2. Should the empty sidebar show the SidebarModeToggle (diffs/files) or hide it? Current spec hides it since there is nothing to toggle between.
3. Long-term: should the error state (`useStackDetail` returns an error) also render inside AppShell rather than a blank red-text page? This spec defers that decision.
