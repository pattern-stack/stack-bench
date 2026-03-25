---
title: "SB-046: Merge Flow Panel"
date: 2026-03-24
status: draft
branch:
depends_on: [2026-03-24-merge-cascade-check-gate]
adrs: [004-stack-branch-domain-model]
---

# SB-046: Merge Flow Panel

## Goal

Build a frontend merge flow panel that surfaces the backend merge cascade system as an interactive UI. The panel shows an ordered list of PRs with per-branch merge readiness (CI, reviews, conflicts, restack status), supports "merge up to here" targeting, displays live cascade progress, and provides post-merge trunk sync cleanup. This replaces the current inline `onMerge` handler in `App.tsx` that calls the deprecated `POST /stacks/{id}/merge` endpoint.

## Problem Statement

The current merge UX is a single "Merge" button in `StackHeader` that fires a synchronous merge-all request. There is no visibility into:
- Which branches are ready to merge and which are blocked
- Why a branch is blocked (CI failing, needs restack, missing reviews)
- Progress of an active cascade (which step is running, which are done)
- Partial failure recovery (which branches merged before the failure)

The backend merge cascade (MergeCascade + CascadeStep models, webhook-driven) is fully built. This spec covers only the frontend.

## Architecture Decision

### Panel placement: Overlay panel, not new page

The merge flow is a transient operation on the current stack. It belongs as a slide-over panel (like AgentPanel) anchored to the right side of the AppShell, triggered from the existing "Merge" button in StackHeader. This keeps the user in context -- they can still see the stack sidebar and branch list while the merge runs.

### Layer placement (Atomic Frontend Design)

| Component | Layer | Rationale |
|-----------|-------|-----------|
| `MergeStepDot` | Atom | Single dot indicator for cascade step state -- mirrors StackDot pattern |
| `BlockerBadge` | Atom | Small badge showing a single blocker reason (CI, restack, review) |
| `MergeStepItem` | Molecule | One row in the merge queue -- branch name + readiness + step state |
| `MergeQueueList` | Molecule | Ordered list of MergeStepItems with "merge up to here" targeting |
| `CascadeProgressBar` | Molecule | Compact progress summary (3/5 merged, step 4 rebasing...) |
| `MergeFlowPanel` | Organism | Full panel: header, queue list, progress, actions, error display |

### Data flow: Hooks + polling

The cascade is webhook-driven on the backend, but the frontend has no WebSocket/SSE channel yet. The frontend polls `GET /stacks/{id}/merge-cascade/{cascade_id}` at a 2-second interval while a cascade is active. Polling stops when the cascade reaches a terminal state (completed, failed, cancelled). Future work can replace polling with the Broadcast subsystem (SSE).

### API contract

The cascade REST endpoints are defined in the backend spec but not yet wired into the stacks router. This spec assumes the following endpoints will be added:

```
POST   /api/v1/stacks/{stack_id}/merge-cascade
GET    /api/v1/stacks/{stack_id}/merge-cascade/{cascade_id}
POST   /api/v1/stacks/{stack_id}/merge-cascade/{cascade_id}/cancel
```

The POST response and GET response share the same shape -- a `MergeCascadeDetail` that includes the cascade plus its steps with branch/PR data joined:

```typescript
interface MergeCascadeDetail {
  id: string;
  stack_id: string;
  triggered_by: string;
  current_position: number;
  state: CascadeState;
  error: string | null;
  created_at: string;
  updated_at: string;
  steps: CascadeStepDetail[];
}

interface CascadeStepDetail {
  id: string;
  cascade_id: string;
  branch_id: string;
  pull_request_id: string | null;
  position: number;
  state: CascadeStepState;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  // Joined from branch/PR for display:
  branch_name: string;
  pr_number: number | null;
  pr_title: string | null;
}
```

**Note for backend wiring**: The organism endpoint should compose the cascade + steps + branch/PR data into this joined response, similar to how `get_stack_detail` joins branches with PRs. The `MergeCascadeEntity` molecule should provide a `get_cascade_detail` method that does this join.

## Domain Model (Frontend Types)

```typescript
// types/merge-cascade.ts

type CascadeState = "pending" | "running" | "completed" | "failed" | "cancelled";

type CascadeStepState =
  | "pending"
  | "retargeting"
  | "rebasing"
  | "ci_pending"
  | "completing"
  | "merged"
  | "conflict"
  | "failed"
  | "skipped";

// Readiness assessment (computed client-side from stack detail data)
interface MergeReadiness {
  ready: boolean;
  blockers: MergeBlocker[];
}

type MergeBlockerKind = "ci_failing" | "needs_restack" | "no_pr" | "not_submitted" | "already_merged";

interface MergeBlocker {
  kind: MergeBlockerKind;
  label: string;
}
```

### Readiness computation

Merge readiness is derived client-side from the existing `BranchWithPR` data (already fetched by `useStackDetail`). A branch is merge-ready when:
1. It has a pull request (`pull_request !== null`)
2. PR state is `open`, `approved`, or `ready` (not `draft`, `closed`, `merged`)
3. `needs_restack` is `false`
4. CI status is not `fail` (when CI data is available)

A branch that is already `merged` is excluded from the cascade entirely (the backend handles this). Branches that are blocked show their specific blocker(s).

## Component Hierarchy

```
MergeFlowPanel (organism)
  +-- Panel header (title, close button)
  +-- CascadeProgressBar (molecule) -- visible when cascade is active
  +-- MergeQueueList (molecule)
  |     +-- MergeStepItem (molecule) x N
  |           +-- MergeStepDot (atom)
  |           +-- StatusBadge (molecule, existing)
  |           +-- BlockerBadge (atom) x 0..N
  |           +-- PRNumber (atom, existing)
  +-- Action footer
  |     +-- "Merge up to [branch]" / "Merge all" button
  |     +-- "Cancel" button (when cascade active)
  |     +-- "Sync trunk" button (when cascade completed)
  +-- Error display (when cascade failed/conflict)
```

## UI States

### 1. Idle (no active cascade)

The panel shows the merge queue: all unmerged branches in stack order (bottom-up, position 1 first). Each branch shows:
- Branch short name
- PR number (if exists)
- Merge readiness indicators (green check or blocker badges)
- A clickable "merge up to here" target marker

The footer shows "Merge all" (merges entire stack) or "Merge up to [branch]" if the user has selected a partial target.

### 2. Pre-merge validation

Before starting a cascade, the panel checks readiness. If any branch up to the target has blockers, the merge button is disabled and blockers are shown inline. The user must resolve blockers first (restack, fix CI, submit PRs).

### 3. Active cascade (running)

Once the cascade starts:
- `CascadeProgressBar` shows: "Merging 2 of 5..." with a segmented bar
- Each `MergeStepItem` shows its current step state with a color-coded dot:
  - `pending` -- gray dot
  - `retargeting` / `rebasing` / `ci_pending` / `completing` -- yellow pulsing dot
  - `merged` -- green dot
  - `conflict` / `failed` -- red dot
  - `skipped` -- gray strikethrough
- The "Merge" button becomes "Cancel cascade"
- Polling is active (2s interval)

### 4. Completed

All steps merged:
- Progress bar shows "All branches merged" (green)
- All dots are green
- Footer shows "Sync trunk" button to clean up merged branches
- Footer also shows "Close" button

### 5. Failed / Conflict

A step hit an error:
- The failed step shows a red dot with the error message
- Subsequent steps show gray "skipped" state
- An error banner appears below the progress bar with the specific error
- For conflicts: show "Conflict in [branch] -- resolve locally and retry"
- Footer shows "Close" (user resolves, then starts a new cascade)

### 6. Loading

While the cascade detail is being fetched, show skeleton states matching the MergeStepItem layout.

## File Tree

```
app/frontend/src/
  types/
    merge-cascade.ts                          # NEW -- CascadeState, CascadeStepState, MergeReadiness types

  hooks/
    useMergeCascade.ts                        # NEW -- start, poll, cancel cascade
    useMergeReadiness.ts                      # NEW -- compute readiness from stack detail

  components/
    atoms/
      MergeStepDot/
        MergeStepDot.tsx                      # NEW -- colored dot for cascade step state
        index.ts                              # NEW
      BlockerBadge/
        BlockerBadge.tsx                      # NEW -- small badge for a single blocker
        index.ts                              # NEW
      atoms/index.ts                          # MODIFY -- add exports

    molecules/
      MergeStepItem/
        MergeStepItem.tsx                     # NEW -- one row in merge queue
        index.ts                              # NEW
      MergeQueueList/
        MergeQueueList.tsx                    # NEW -- ordered list with targeting
        index.ts                              # NEW
      CascadeProgressBar/
        CascadeProgressBar.tsx                # NEW -- compact progress summary
        index.ts                              # NEW
      molecules/index.ts                      # MODIFY -- add exports

    organisms/
      MergeFlowPanel/
        MergeFlowPanel.tsx                    # NEW -- full panel organism
        MergeFlowSkeleton.tsx                 # NEW -- loading skeleton
        index.ts                              # NEW
      organisms/index.ts                      # MODIFY -- add export

    templates/
      AppShell/AppShell.tsx                   # MODIFY -- add mergeOpen state, wire panel

  App.tsx                                     # MODIFY -- replace onMerge handler, add cascade state
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Types + readiness hook | -- |
| 2 | Atoms: MergeStepDot, BlockerBadge | -- |
| 3 | Cascade API hook (useMergeCascade) | Phase 1 |
| 4 | Molecules: MergeStepItem, MergeQueueList, CascadeProgressBar | Phase 1, 2 |
| 5 | Organism: MergeFlowPanel + skeleton | Phase 3, 4 |
| 6 | Integration: wire into AppShell + App.tsx | Phase 5 |

## Phase Details

### Phase 1: Types + Readiness Hook

**`types/merge-cascade.ts`**: Define `CascadeState`, `CascadeStepState`, `MergeCascadeDetail`, `CascadeStepDetail`, `MergeReadiness`, `MergeBlocker`, `MergeBlockerKind`.

**`hooks/useMergeReadiness.ts`**: Pure computation hook. Takes `BranchWithPR[]` from `useStackDetail`, returns `Map<string, MergeReadiness>` keyed by branch ID. For each unmerged branch:
- Check `pull_request !== null` (blocker: `no_pr`)
- Check PR state is submittable (blocker: `not_submitted`)
- Check `needs_restack === false` (blocker: `needs_restack`)
- Check CI status (blocker: `ci_failing` -- when CI data is available, currently mocked as `"none"`)
- Skip branches already in `merged` state (blocker: `already_merged`, excluded from queue)

Returns a `useMemo`-wrapped computation. No API calls.

### Phase 2: Atoms

**`MergeStepDot`**: A small colored dot (similar to `StackDot` but simpler -- no connector lines). Props: `state: CascadeStepState`. Color mapping:
- `pending` -> `var(--fg-subtle)` (gray)
- `retargeting`, `rebasing`, `ci_pending`, `completing` -> `var(--yellow)` with CSS `animate-pulse`
- `merged` -> `var(--green)`
- `conflict`, `failed` -> `var(--red)`
- `skipped` -> `var(--fg-subtle)` with `opacity-50`

Rendered as a `<span>` with `w-2 h-2 rounded-full inline-block`.

**`BlockerBadge`**: Uses the existing `Badge` atom with `size="sm"`. Props: `kind: MergeBlockerKind`. Maps kind to color and label:
- `ci_failing` -> red, "CI failing"
- `needs_restack` -> yellow, "Needs restack"
- `no_pr` -> default, "No PR"
- `not_submitted` -> default, "Not submitted"

### Phase 3: Cascade API Hook

**`hooks/useMergeCascade.ts`**: Manages the full cascade lifecycle.

```typescript
function useMergeCascade(stackId?: string)
```

Returns:
- `cascade: MergeCascadeDetail | null` -- current cascade data
- `isActive: boolean` -- cascade is in `pending` or `running` state
- `isPolling: boolean` -- polling is happening
- `startCascade: (mergeUpTo?: number) => Promise<void>` -- POST to start
- `cancelCascade: () => Promise<void>` -- POST to cancel
- `reset: () => void` -- clear cascade state (after close)
- `error: string | null`

Implementation:
- `startCascade` calls `POST /api/v1/stacks/{stackId}/merge-cascade` with optional `{ merge_up_to: position }` body
- On success, stores `cascade_id` in local state
- Uses `useQuery` with `refetchInterval: 2000` and `enabled: isActive` to poll `GET /api/v1/stacks/{stackId}/merge-cascade/{cascadeId}`
- Polling stops automatically when `cascade.state` is terminal (`completed`, `failed`, `cancelled`)
- `cancelCascade` calls `POST /api/v1/stacks/{stackId}/merge-cascade/{cascadeId}/cancel`
- On cascade completion, invalidates `stackDetailKeys` to refresh the sidebar

### Phase 4: Molecules

**`MergeStepItem`**: One row in the merge queue. Two visual modes:

*Idle mode* (no active cascade): Shows branch name, PR number, readiness indicators, and a hover-target for "merge up to here".

```typescript
interface MergeStepItemProps {
  branchName: string;
  prNumber: number | null;
  position: number;
  readiness: MergeReadiness;
  stepState?: CascadeStepState;  // undefined when idle
  stepError?: string | null;
  isTarget: boolean;             // highlighted as merge target
  onSetTarget?: () => void;      // click to set "merge up to here"
}
```

Layout: `MergeStepDot` | branch name + PR number | readiness badges or step state label | target indicator

*Active mode* (cascade running): Shows step state with descriptive label:
- `retargeting` -> "Retargeting to trunk..."
- `rebasing` -> "Rebasing..."
- `ci_pending` -> "Waiting for CI..."
- `completing` -> "Completing merge..."
- `merged` -> "Merged" (green text)
- `conflict` -> "Conflict" (red text) + error detail
- `failed` -> "Failed" (red text) + error detail
- `skipped` -> "Skipped" (muted, strikethrough)

**`MergeQueueList`**: Renders `MergeStepItem` list in position order. Props:

```typescript
interface MergeQueueListProps {
  branches: BranchWithPR[];
  readinessMap: Map<string, MergeReadiness>;
  steps?: CascadeStepDetail[];  // from active cascade, if any
  targetPosition: number | null;
  onSetTarget: (position: number | null) => void;
}
```

Filters out already-merged branches. Maps each branch to a `MergeStepItem`, joining with `steps` data when a cascade is active. The target position determines which branches will be included in the merge (all branches at position <= target).

**`CascadeProgressBar`**: Compact summary bar. Props:

```typescript
interface CascadeProgressBarProps {
  steps: CascadeStepDetail[];
  state: CascadeState;
}
```

Renders:
- A segmented bar where each segment is colored by step state
- Text: "Merging 2 of 5..." or "All 5 merged" or "Failed at step 3 of 5"
- Uses CSS grid with `grid-template-columns: repeat(N, 1fr)` for equal segments

### Phase 5: Organism -- MergeFlowPanel

**`MergeFlowPanel`**: The full slide-over panel. Matches the visual pattern of `AgentPanel` (right-anchored, collapsible).

```typescript
interface MergeFlowPanelProps {
  isOpen: boolean;
  onClose: () => void;
  stackId: string;
  branches: BranchWithPR[];
  onSyncTrunk?: () => void;
}
```

Internal state:
- `targetPosition: number | null` -- which branch to merge up to (null = all)
- Cascade state from `useMergeCascade(stackId)`
- Readiness from `useMergeReadiness(branches)`

Layout:
```
+-- Panel container (fixed width, right side) ---------------+
|  [Icon: git-merge] Merge Stack               [X close]     |
|                                                             |
|  [CascadeProgressBar] -- only when cascade active           |
|                                                             |
|  [Error banner] -- only when failed/conflict                |
|                                                             |
|  [MergeQueueList]                                           |
|    1. branch-a  #42  [green check]                          |
|    2. branch-b  #43  [Needs restack]                        |
|    3. branch-c  #44  [green check]    <-- merge up to here  |
|    4. branch-d       [No PR]                                |
|                                                             |
|  +-- Footer ------------------------------------------+    |
|  | [Merge up to branch-c]  or  [Cancel cascade]       |    |
|  +-----------------------------------------------------+   |
+-------------------------------------------------------------+
```

Panel width: `w-80` (320px), matching AgentPanel sizing conventions.

**`MergeFlowSkeleton`**: Loading state skeleton matching MergeStepItem layout. 4 rows of skeleton bars.

### Phase 6: Integration

**`AppShell`**: Add `mergeOpen: boolean` and `onMergeToggle` to props. Render `MergeFlowPanel` alongside `AgentPanel` (they are mutually exclusive -- opening merge closes agent and vice versa, or they stack).

**`App.tsx`**:
- Add `mergeOpen` state
- Replace the current inline `onMerge` handler (lines 215-231) with `() => setMergeOpen(true)`
- Pass `mergeOpen`, `onMergeClose`, `stackId`, and `branches` down to AppShell
- The `MergeFlowPanel` internally manages cascade lifecycle via its hooks

## Key Design Decisions

### 1. Panel, not modal

A modal would block interaction with the rest of the UI during a long-running cascade. A slide-over panel lets the user continue viewing diffs and branch details while the merge progresses. This matches the AgentPanel pattern already established.

### 2. Client-side readiness computation

Readiness is computed from data already fetched by `useStackDetail` (branch state, PR state, needs_restack flag). No new backend endpoint needed. The backend enforces readiness at cascade creation time and returns a 422 if preconditions fail, but the frontend pre-validates to avoid unnecessary round trips.

### 3. "Merge up to here" targeting

The cascade spec supports merging a subset of the stack (all branches up to position N). This is exposed as a click target on each branch row. Clicking a branch highlights it and all branches below it as the merge set. This is more useful than merge-all for stacks where upper branches are still in progress.

### 4. Polling, not WebSocket

The project does not have a real-time channel yet. Polling at 2s is acceptable for a merge cascade that typically takes 30-120 seconds. The `refetchInterval` on `useQuery` handles this cleanly with automatic cleanup. When the Broadcast subsystem is wired to the frontend (future), polling can be replaced with SSE subscription.

### 5. Cascade state lives in the hook, not global store

The cascade is transient and scoped to a single stack. There is no need for global state management. The `useMergeCascade` hook manages cascade ID and polling internally. When the panel closes, `reset()` clears the state.

### 6. Mutually exclusive with AgentPanel (deferred)

For MVP, both panels can be open simultaneously (they both anchor right). If screen real estate is a concern, a future iteration can make them mutually exclusive. The AppShell already manages `agentOpen` state -- adding `mergeOpen` follows the same pattern.

## Backend Endpoint Wiring (Prerequisite)

The frontend depends on three cascade endpoints being wired into the stacks router. This is backend Phase 5 from the cascade spec and should be completed before or in parallel with frontend Phase 3. Specifically:

1. Add `POST /{stack_id}/merge-cascade` to `organisms/api/routers/stacks.py`
2. Add `GET /{stack_id}/merge-cascade/{cascade_id}` -- must return the joined `MergeCascadeDetail` shape (cascade + steps + branch names + PR numbers)
3. Add `POST /{stack_id}/merge-cascade/{cascade_id}/cancel`
4. Wire `MergeCascadeEntity` through dependencies

The GET endpoint response shape must match the `MergeCascadeDetail` TypeScript interface defined in Phase 1.

## Testing Strategy

### Component Tests (Vitest + React Testing Library)

**Atoms:**
- `MergeStepDot`: Renders correct color/class for each `CascadeStepState` value. Pulsing animation for active states.
- `BlockerBadge`: Renders correct label and color for each `MergeBlockerKind`.

**Molecules:**
- `MergeStepItem`: Renders branch name, PR number, readiness badges in idle mode. Renders step state label in active mode. Shows error detail for failed/conflict states.
- `MergeQueueList`: Renders correct number of items (excludes merged branches). Highlights target position. Calls `onSetTarget` on click.
- `CascadeProgressBar`: Segment colors match step states. Text matches cascade state.

**Organism:**
- `MergeFlowPanel`: Renders idle state with merge queue. Shows progress bar when cascade is active. Shows error banner on failure. Disables merge button when blockers exist. Calls `onClose` when close button clicked.

Marker: Vitest `describe` blocks per component.

### Hook Tests (Vitest)

- `useMergeReadiness`: Returns correct blockers for branches missing PRs, needing restack, already merged. Returns `ready: true` for clean branches.
- `useMergeCascade`: Mock `apiClient`. Verify `startCascade` calls correct endpoint. Verify polling starts on active cascade. Verify polling stops on terminal state. Verify `cancelCascade` calls cancel endpoint.

### Integration Tests

- Full panel flow: Open panel -> see queue -> click "merge up to" -> click merge -> see progress -> cascade completes -> see "sync trunk" button.
- Error flow: Open panel -> start merge -> cascade fails -> see error banner with details.
- Blocker flow: Branch needs restack -> merge button disabled -> resolve -> merge button enabled.

These use `msw` (Mock Service Worker) to intercept API calls and return controlled responses.

## Open Questions

### 1. Should "Sync trunk" trigger a real backend operation?

The issue mentions "Sync trunk cleans up merged branches". The backend `POST /stacks/{id}/sync` already exists but is for syncing state from `st push`. A dedicated "cleanup merged branches" endpoint (delete remote branches, close stale PRs) does not exist yet. For MVP, "Sync trunk" can call the existing sync endpoint and rely on the stack detail refresh to reflect the cleaned-up state. A dedicated cleanup endpoint is future work.

**Decision**: MVP -- refresh stack detail after cascade completes. The sync button in StackHeader already handles the general case. The "Sync trunk" button in the merge panel is a convenience shortcut that calls the same `onSync` handler.

### 2. Merge method selection (squash vs merge vs rebase)?

The cascade spec defaults to squash merge. Should the UI expose a merge method selector? For MVP, no -- squash is the default and the only supported method. A dropdown can be added later if needed.

**Decision**: Hardcode squash for MVP. No UI selector.

### 3. Real-time updates vs polling interval?

2-second polling is a pragmatic choice. If the cascade typically takes 30-120 seconds, users will see 15-60 polls. This is acceptable. If latency feels sluggish, the interval can be reduced to 1 second. SSE via Broadcast subsystem is the long-term solution.

**Decision**: 2-second polling for MVP. Revisit when Broadcast subsystem has frontend wiring.
