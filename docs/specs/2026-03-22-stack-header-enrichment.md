---
title: Stack Header & Branch Enrichment (Round 1)
date: 2026-03-22
status: draft
branch:
depends_on: []
adrs: []
---

# Stack Header & Branch Enrichment (Round 1)

## Goal

Enrich the existing stack sidebar with three capabilities: (1) a stack header showing aggregate status summary and toolbar buttons, (2) enriched branch rows with PR numbers, CI status dots, and "needs restack" badges, and (3) an activity log panel showing timestamped stack operations. All backed by mock data -- no backend wiring. This is Round 1 of EP-007; Round 2 (branch context menus, merge flow panel) is explicitly out of scope.

## Scope

**In scope (Round 1):**
- Stack header with name, branch count, colored status summary, and Sync/Restack/Merge toolbar buttons (UI only, no-op handlers)
- Branch row enrichment: PR number display (#103), CI status dot (pass/fail/pending/none), "Needs restack" inline badge
- Activity log panel at sidebar bottom: timestamped operation entries (sync, merge, restack, push), Clear button
- Mock data for all new fields
- New icon paths for CI dots, merge, sync, and activity operations

**Out of scope (Round 2+):**
- Branch context menus / right-click actions
- Merge flow panel with readiness checks
- Conflict detection / resolution UI
- Real backend wiring / CLI integration
- Real-time event streaming from stack daemon

## Domain Model (Mock Data)

### Enriched types

```typescript
// New fields on StackConnectorItem (extend existing)
interface StackConnectorItem {
  id: string;
  title: string;
  status: string;
  additions?: number;
  deletions?: number;
  // --- New Round 1 fields ---
  prNumber?: number | null;       // e.g. 103 -> displayed as "#103"
  ciStatus?: CIStatus;            // "pass" | "fail" | "pending" | "none"
  needsRestack?: boolean;         // shows inline badge when true
}

type CIStatus = "pass" | "fail" | "pending" | "none";

// Stack-level aggregate (computed from items, not a new type)
// "draft" counts branches with status "draft", "created", or "local" (no PR yet)
// "open" counts branches with status "open", "reviewing", "review", "approved", or "ready"
interface StackSummary {
  branchCount: number;
  merged: number;
  open: number;
  needsRestack: number;
  draft: number;
}

// Activity log entries
interface ActivityLogEntry {
  id: string;
  operation: "sync" | "merge" | "restack" | "push";
  description: string;
  timestamp: string;              // ISO 8601, rendered as relative ("2m ago")
}
```

## Architecture

### Layer Assignments

| Component | Layer | New/Modified | Notes |
|-----------|-------|-------------|-------|
| `CIDot` | atom | NEW | Colored dot for CI status (pass=green, fail=red, pending=yellow, none=gray) |
| `RestackBadge` | atom | NEW | Small inline "Needs restack" badge, uses existing Badge with yellow color |
| `PRNumber` | atom | NEW | Renders `#103` in monospace muted text |
| `StackHeader` | molecule | NEW | Stack name, branch count, status summary, toolbar buttons |
| `ActivityLogEntry` | molecule | NEW | Single log row: operation icon + description + relative time |
| `ActivityLog` | molecule | NEW | List of ActivityLogEntry items with Clear button and section header |
| `StackItem` | molecule | MODIFIED | Add prNumber, ciStatus, needsRestack props; render new atoms in the second row |
| `StackConnector` | molecule | MODIFIED | Pass new props through to StackItem |
| `StackSidebar` | organism | MODIFIED | Add StackHeader at top (replacing current simple header), add ActivityLog at bottom (above footer toolbar) |
| `Icon` | atom | MODIFIED | Add new icon paths: `activity`, `git-merge`, `download-cloud`, `alert-triangle`, `check-circle` |
| mock-data.ts | lib | MODIFIED | Add new fields to existing branch mock data + new activityLog mock array |

### Component Hierarchy (updated sidebar)

```
StackSidebar (organism)
  StackHeader (molecule) .............. NEW - replaces current header div
    Icon (atom) - git-branch
    Colored summary spans x N - inline "2 merged", "3 open" chips
    Button (atom) x 3 - Sync / Restack / Merge toolbar
  StackConnector (molecule) ........... MODIFIED
    StackItem (molecule) .............. MODIFIED
      StackDot (atom)
      StatusBadge (molecule)
      PRNumber (atom) ................ NEW
      CIDot (atom) ................... NEW
      RestackBadge (atom) ............ NEW
      DiffStat (atom)
  SidebarModeToggle (atom)
  DiffFileList | FileTree
  ActivityLog (molecule) .............. NEW
    ActivityLogEntry (molecule) ....... NEW
  Footer toolbar (existing buttons)
```

## File Tree

All paths relative to `app/frontend/src/`.

### New files

```
components/atoms/CIDot/CIDot.tsx             # Colored CI status dot (6x6 circle)
components/atoms/CIDot/index.ts              # Barrel export
components/atoms/PRNumber/PRNumber.tsx        # "#103" monospace label
components/atoms/PRNumber/index.ts           # Barrel export
components/atoms/RestackBadge/RestackBadge.tsx # "Needs restack" yellow badge
components/atoms/RestackBadge/index.ts       # Barrel export
components/molecules/StackHeader/StackHeader.tsx   # Stack name + summary + toolbar
components/molecules/StackHeader/index.ts          # Barrel export
components/molecules/ActivityLogEntry/ActivityLogEntry.tsx  # Single log row
components/molecules/ActivityLogEntry/index.ts             # Barrel export
components/molecules/ActivityLog/ActivityLog.tsx   # Log list + Clear button
components/molecules/ActivityLog/index.ts          # Barrel export
types/activity.ts                                  # ActivityLogEntry type + CIStatus type
lib/mock-activity-data.ts                          # Mock activity log entries
lib/time.ts                                        # relativeTime() utility
```

### Modified files

```
components/atoms/Icon/Icon.tsx               # Add 5 new icon paths
components/atoms/index.ts                    # Export CIDot, PRNumber, RestackBadge
components/molecules/StackItem/StackItem.tsx # Add prNumber, ciStatus, needsRestack
components/molecules/StackConnector/StackConnector.tsx  # Extend StackConnectorItem, pass through
components/molecules/index.ts                # Export StackHeader, ActivityLog, ActivityLogEntry
components/organisms/StackSidebar/StackSidebar.tsx     # Replace header, add ActivityLog section
components/templates/AppShell/AppShell.tsx    # Pass new props through to StackSidebar
App.tsx                                      # Build enriched items with new mock fields; extend mockDiffStats with prNumber, ciStatus, needsRestack
types/stack.ts                               # Add CIStatus type alias (or import from activity.ts)
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | New types, mock data, utility | -- |
| 2 | New atoms (CIDot, PRNumber, RestackBadge) | Phase 1 |
| 3 | Enrich StackItem and StackConnector | Phase 2 |
| 4 | StackHeader molecule | Phase 2 |
| 5 | ActivityLog molecules | Phase 1, Phase 2 |
| 6 | Wire into StackSidebar, AppShell, App | Phases 3-5 |

## Phase Details

### Phase 1: Types, mock data, utility

1. Create `types/activity.ts` with `CIStatus`, `ActivityLogEntry`, and `StackSummary` types.

2. Create `lib/time.ts` with a `relativeTime(isoString: string): string` function that returns human-readable relative timestamps ("2m ago", "1h ago", "yesterday"). Keep it simple -- no library dependency, just a small function comparing Date.now() to the parsed date.

3. Create `lib/mock-activity-data.ts` with an array of 5-6 mock `ActivityLogEntry` objects spanning the last hour (sync trunk, push branch, restack 2 branches, merge #35, etc.).

4. Modify the `mockDiffStats` map in `App.tsx` (line 20, NOT in `lib/mock-data.ts`) to add new fields, or extend into a richer mock map:
   - b-001: `prNumber: 35, ciStatus: "pass", needsRestack: false`
   - b-002: `prNumber: 36, ciStatus: "pass", needsRestack: false`
   - b-003: `prNumber: 37, ciStatus: "pending", needsRestack: true`
   - b-004: `prNumber: null, ciStatus: "none", needsRestack: true`

### Phase 2: New atoms

5. **CIDot** (`components/atoms/CIDot/CIDot.tsx`):
   - Props: `status: CIStatus`
   - Renders a 6x6px (w-1.5 h-1.5) filled circle
   - Color map: pass=`var(--green)`, fail=`var(--red)`, pending=`var(--yellow)`, none=`var(--fg-subtle)`
   - On `none`, render nothing (return null) to avoid visual noise on local branches
   - Include a title attribute for accessibility: "CI: passing", "CI: failing", etc.

6. **PRNumber** (`components/atoms/PRNumber/PRNumber.tsx`):
   - Props: `number: number`
   - Renders `#103` in monospace, text-xs, `var(--fg-muted)` color
   - Simple span with `font-[family-name:var(--font-mono)]`

7. **RestackBadge** (`components/atoms/RestackBadge/RestackBadge.tsx`):
   - No props (or optional `className`)
   - Renders the existing `Badge` atom with `size="sm"` and `color="yellow"`
   - Text: "Restack"
   - Keep it short so it fits inline on the branch row

8. Add new icon paths to `Icon.tsx`:
   - `activity`: clock-like icon for activity log header
   - `git-merge`: merge icon for merge button
   - `download-cloud`: cloud download for sync trunk
   - `check-circle`: circled checkmark for CI pass states
   - `alert-triangle`: triangle warning for restack needed

9. Update `components/atoms/index.ts` barrel to export CIDot, PRNumber, RestackBadge.

### Phase 3: Enrich StackItem and StackConnector

10. **StackConnector** (`StackConnector.tsx`):
    - Extend `StackConnectorItem` interface with optional `prNumber?: number | null`, `ciStatus?: CIStatus`, `needsRestack?: boolean`
    - Pass these through to `StackItem`

11. **StackItem** (`StackItem.tsx`):
    - Add props: `prNumber?: number | null`, `ciStatus?: CIStatus`, `needsRestack?: boolean`
    - In the second row (below title), render in this order:
      ```
      StatusBadge | PRNumber | CIDot | RestackBadge | (spacer) | DiffStat
      ```
    - PRNumber only renders when prNumber is a positive number
    - CIDot only renders when ciStatus is not "none" (handled internally by CIDot)
    - RestackBadge only renders when needsRestack is true
    - Use `flex items-center gap-1.5` for the metadata row, with DiffStat pushed right via `ml-auto`

### Phase 4: StackHeader molecule

12. **StackHeader** (`components/molecules/StackHeader/StackHeader.tsx`):
    - Props:
      ```typescript
      interface StackHeaderProps {
        stackName: string;
        trunk: string;
        branchCount: number;
        summary: StackSummary;
        onSync?: () => void;
        onRestackAll?: () => void;
        onMerge?: () => void;
      }
      ```
    - Layout (top to bottom):
      - **Row 1**: Git-branch icon + stack name (semibold) + muted "N branches" count
      - **Row 2**: Colored summary chips -- "2 merged" (green), "3 open" (accent), "1 draft" (default/muted), "2 need restack" (yellow). Only show categories with count > 0. Each chip is a small inline span with the matching color from the design system (NOT StatusBadge -- these are simpler text spans).
      - **Row 3**: Toolbar with three `Button variant="subtle" size="sm"` buttons:
        - "Sync trunk" with download-cloud icon
        - "Restack all (N)" with refresh-cw icon, showing count of needsRestack, disabled when 0
        - "Merge stack" with git-merge icon
    - Compute `StackSummary` from items in the parent (StackSidebar or App), not inside StackHeader itself. StackHeader is a pure display component.

13. Update `components/molecules/index.ts` barrel.

### Phase 5: ActivityLog molecules

14. **ActivityLogEntry** (`components/molecules/ActivityLogEntry/ActivityLogEntry.tsx`):
    - Props: `entry: ActivityLogEntry` (the type from `types/activity.ts`)
    - Layout: single row with:
      - Operation label (colored by type): sync=accent, merge=green, restack=yellow, push=purple
      - Description text (muted, truncated)
      - Relative timestamp right-aligned (subtle, text-xs)
    - Use existing Badge atom for the operation label

15. **ActivityLog** (`components/molecules/ActivityLog/ActivityLog.tsx`):
    - Props: `entries: ActivityLogEntry[]`, `onClear?: () => void`
    - Layout:
      - Section header: "Activity" label (same 10px uppercase style as "Stack" label) + Clear button (text-only, subtle)
      - Scrollable list of ActivityLogEntry components, max-height constrained (e.g. `max-h-36`)
      - When entries is empty, show muted "No recent activity" text

16. Update `components/molecules/index.ts` barrel.

### Phase 6: Wire everything together

17. **StackSidebar** (`StackSidebar.tsx`):
    - Replace the current header `<div>` (lines 55-65) with the new `StackHeader` molecule
    - Add new props: `summary: StackSummary`, `activityEntries: ActivityLogEntry[]`, `onSync?: () => void`, `onMerge?: () => void`, `onClearActivity?: () => void`
    - Insert `ActivityLog` between the file tree area and the footer toolbar
    - Remove the existing `onRestackAll` and `onPushStack` footer buttons (they move into StackHeader toolbar)
    - The footer section can be removed entirely or repurposed

18. **AppShell** (`AppShell.tsx`):
    - Pass new props through from AppShell to StackSidebar (summary, activityEntries, onSync, onMerge, onClearActivity)

19. **App.tsx**:
    - Build enriched `StackConnectorItem[]` with prNumber, ciStatus, needsRestack from mock data
    - Compute `StackSummary` by counting statuses from items
    - Import mock activity data
    - Add `useState` for activity entries so Clear button can empty them
    - Wire no-op handlers for onSync, onMerge (or `console.log` stubs)

## Key Design Decisions

1. **StackHeader replaces the existing header div** rather than sitting alongside it. The current header is just a name + trunk label. The new StackHeader subsumes that responsibility and adds summary + toolbar.

2. **Footer toolbar buttons move into StackHeader**. The mockup shows Sync/Restack/Merge in the header area, not a separate footer. This frees the footer area and reduces visual clutter. Note: the existing "Push stack" button is deliberately removed -- pushing is a per-branch operation that will move to a branch context menu in Round 2. The "Merge stack" button replaces it as a stack-level action.

3. **CIDot returns null for "none" status**. Local branches without PRs should not show a gray dot -- they have no CI to report. This keeps the visual density proportional to actual information.

4. **RestackBadge is its own atom** rather than a variant of StatusBadge. StatusBadge maps 1:1 with PR/branch states (merged, open, draft). "Needs restack" is orthogonal metadata and should be visually distinct (yellow badge alongside the status badge, not replacing it).

5. **StackSummary is computed in App.tsx**, not inside StackHeader. This keeps StackHeader a pure presentational component and makes testing trivial -- pass in counts, verify rendering.

6. **Activity log uses mock data with relative timestamps**. The `relativeTime()` utility is intentionally simple (no moment/date-fns). When real events arrive from the stack daemon, the same component and types will work -- only the data source changes.

7. **New types live in `types/activity.ts`** rather than extending `types/stack.ts`. CIStatus and ActivityLogEntry are sidebar-UI concerns that do not belong on the core stack domain types. The StackConnectorItem interface (which is a view-model, not a domain type) gets the new optional fields.

## Open Questions

1. **Toolbar button behavior**: Should toolbar buttons show a loading/spinner state when clicked (even without backend wiring)? Decision: No for Round 1 -- just no-op or console.log. Round 2 will add optimistic UI.

2. **Activity log persistence**: Should clearing the log persist across branch switches? Decision: Yes -- activity log is stack-scoped, not branch-scoped. A single `useState` in App.tsx is sufficient.

3. **StackHeader collapse on narrow sidebar**: If the sidebar is resizable in a future iteration, should StackHeader collapse the summary row? Decision: Deferred -- current sidebar is fixed-width at 320px.

## Acceptance Criteria

- [ ] Stack header shows stack name, branch count, and colored status summary (e.g. "2 merged 3 open 2 need restack")
- [ ] Stack header toolbar has Sync trunk, Restack all (N), and Merge stack buttons
- [ ] Restack all button shows count and is disabled when no branches need restacking
- [ ] Each branch row shows PR number (e.g. #37) when a PR exists
- [ ] Each branch row shows a colored CI status dot (green/red/yellow) when CI status is not "none"
- [ ] Branches needing restack show a yellow "Restack" badge inline
- [ ] Activity log panel displays 5-6 mock entries with operation type, description, and relative timestamps
- [ ] Activity log Clear button empties the list and shows "No recent activity"
- [ ] All new atoms (CIDot, PRNumber, RestackBadge) follow existing design system tokens -- no hardcoded colors
- [ ] All new components have displayName set
- [ ] All barrel exports updated (atoms/index.ts, molecules/index.ts)
- [ ] Existing functionality (branch selection, diff/file toggle, file tree) is not broken
