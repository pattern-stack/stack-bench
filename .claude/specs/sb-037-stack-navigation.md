---
title: "SB-037: Stack Navigation (sidebar + branch list)"
date: 2026-03-21
status: draft
branch: dugshub/frontend-mvp/1-ep-006-frontend-mvp-stack-review-ui
depends_on:
  - SB-036
adrs: []
---

# SB-037: Stack Navigation (sidebar + branch list)

## Goal

Build the stack sidebar — left panel showing all branches in a stack with status, diff stats, and visual connectors. This is the primary navigation for the app. Uses mock data for MVP; wired to `GET /api/v1/stacks/{id}/detail` via a fetch hook.

## Domain Model

Backend state machines (from models):
- **Stack states:** draft, active, submitted, merged, closed
- **Branch states:** created, pushed, reviewing, ready, submitted, merged
- **PR states:** draft, open, approved, merged, closed

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | TypeScript types (`types/stack.ts`) | -- |
| 2 | Mock data (`lib/mock-data.ts`) | Phase 1 |
| 3 | `StackDot` atom | -- |
| 4 | `DiffStat` atom | -- |
| 5 | `StatusBadge` molecule | -- |
| 6 | `StackItem` molecule | Phase 3, 4, 5 |
| 7 | `StackConnector` molecule | Phase 6 |
| 8 | `StackSidebar` organism | Phase 7 |
| 9 | `useStackDetail` hook | Phase 1, 2 |
| 10 | Barrel exports | Phase 3-8 |
| 11 | Wire App.tsx | Phase 8, 9 |
| 12 | Verification | Phase 11 |

## Phase Details

### Phase 1: TypeScript Types

#### `app/frontend/src/types/stack.ts`

These interfaces match the backend Pydantic response schemas exactly.

```ts
export interface Stack {
  id: string;
  reference_number: string | null;
  project_id: string;
  name: string;
  base_branch_id: string | null;
  trunk: string;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface Branch {
  id: string;
  reference_number: string | null;
  stack_id: string;
  workspace_id: string;
  name: string;
  position: number;
  head_sha: string | null;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface PullRequest {
  id: string;
  reference_number: string | null;
  branch_id: string;
  external_id: number | null;
  external_url: string | null;
  title: string;
  description: string | null;
  review_notes: string | null;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface BranchWithPR {
  branch: Branch;
  pull_request: PullRequest | null;
}

export interface StackDetail {
  stack: Stack;
  branches: BranchWithPR[];
}
```

Create directory first: `mkdir -p app/frontend/src/types`

---

### Phase 2: Mock Data

#### `app/frontend/src/lib/mock-data.ts`

```ts
import type { StackDetail } from "@/types/stack";

const now = "2026-03-21T12:00:00Z";

export const mockStackDetail: StackDetail = {
  stack: {
    id: "s-001",
    reference_number: "STK-001",
    project_id: "p-001",
    name: "frontend-mvp",
    base_branch_id: null,
    trunk: "main",
    state: "active",
    created_at: now,
    updated_at: now,
  },
  branches: [
    {
      branch: {
        id: "b-001",
        reference_number: "BR-001",
        stack_id: "s-001",
        workspace_id: "w-001",
        name: "dug/frontend-mvp/1-scaffold",
        position: 1,
        head_sha: "abc1234",
        state: "merged",
        created_at: now,
        updated_at: now,
      },
      pull_request: {
        id: "pr-001",
        reference_number: "PR-001",
        branch_id: "b-001",
        external_id: 35,
        external_url: "https://github.com/org/stack-bench/pull/35",
        title: "Frontend scaffold + dark design system",
        description: "Vite + React + Tailwind 4 scaffold with dark tokens.",
        review_notes: null,
        state: "merged",
        created_at: now,
        updated_at: now,
      },
    },
    {
      branch: {
        id: "b-002",
        reference_number: "BR-002",
        stack_id: "s-001",
        workspace_id: "w-001",
        name: "dug/frontend-mvp/2-shared-atoms",
        position: 2,
        head_sha: "def5678",
        state: "merged",
        created_at: now,
        updated_at: now,
      },
      pull_request: {
        id: "pr-002",
        reference_number: "PR-002",
        branch_id: "b-002",
        external_id: 36,
        external_url: "https://github.com/org/stack-bench/pull/36",
        title: "Shared atoms: Badge, Icon, Button, Collapsible, Tab",
        description: "Foundational atom components for the design system.",
        review_notes: null,
        state: "merged",
        created_at: now,
        updated_at: now,
      },
    },
    {
      branch: {
        id: "b-003",
        reference_number: "BR-003",
        stack_id: "s-001",
        workspace_id: "w-001",
        name: "dug/frontend-mvp/3-stack-nav",
        position: 3,
        head_sha: "789abcd",
        state: "reviewing",
        created_at: now,
        updated_at: now,
      },
      pull_request: {
        id: "pr-003",
        reference_number: "PR-003",
        branch_id: "b-003",
        external_id: 37,
        external_url: "https://github.com/org/stack-bench/pull/37",
        title: "Stack navigation sidebar + branch list",
        description: "Left panel with stack branches, status badges, diff stats.",
        review_notes: "Check connector line alignment on short stacks.",
        state: "open",
        created_at: now,
        updated_at: now,
      },
    },
    {
      branch: {
        id: "b-004",
        reference_number: "BR-004",
        stack_id: "s-001",
        workspace_id: "w-001",
        name: "dug/frontend-mvp/4-app-shell",
        position: 4,
        head_sha: null,
        state: "created",
        created_at: now,
        updated_at: now,
      },
      pull_request: null,
    },
  ],
};
```

---

### Phase 3: StackDot Atom

A colored circle with a vertical connector line above and below. The line is continuous through all items. First item has no line above; last item has no line below.

#### `app/frontend/src/components/atoms/StackDot/StackDot.tsx`

```tsx
import { cn } from "@/lib/utils";

type StackDotColor = "default" | "accent" | "green";

interface StackDotProps {
  color?: StackDotColor;
  isFirst?: boolean;
  isLast?: boolean;
}

const dotColorMap: Record<StackDotColor, string> = {
  default: "bg-[var(--fg-subtle)]",
  accent: "bg-[var(--accent)]",
  green: "bg-[var(--green)]",
};

const lineColorMap: Record<StackDotColor, string> = {
  default: "bg-[var(--border)]",
  accent: "bg-[var(--border)]",
  green: "bg-[var(--border)]",
};

function StackDot({ color = "default", isFirst = false, isLast = false }: StackDotProps) {
  return (
    <div className="relative flex flex-col items-center w-4 self-stretch">
      {/* Line above the dot */}
      <div
        className={cn(
          "w-px flex-1",
          isFirst ? "bg-transparent" : lineColorMap[color]
        )}
      />
      {/* The dot */}
      <div
        className={cn(
          "w-2.5 h-2.5 rounded-full shrink-0 ring-2 ring-[var(--bg-surface)]",
          dotColorMap[color]
        )}
      />
      {/* Line below the dot */}
      <div
        className={cn(
          "w-px flex-1",
          isLast ? "bg-transparent" : lineColorMap[color]
        )}
      />
    </div>
  );
}

StackDot.displayName = "StackDot";

export { StackDot };
export type { StackDotProps, StackDotColor };
```

#### `app/frontend/src/components/atoms/StackDot/index.ts`

```ts
export { StackDot } from "./StackDot";
export type { StackDotProps, StackDotColor } from "./StackDot";
```

---

### Phase 4: DiffStat Atom

Inline `+N -N` display with green/red coloring and monospace font.

#### `app/frontend/src/components/atoms/DiffStat/DiffStat.tsx`

```tsx
interface DiffStatProps {
  additions: number;
  deletions: number;
}

function DiffStat({ additions, deletions }: DiffStatProps) {
  if (additions === 0 && deletions === 0) {
    return null;
  }

  return (
    <span className="inline-flex items-center gap-1.5 font-[family-name:var(--font-mono)] text-xs">
      {additions > 0 && (
        <span className="text-[var(--green)]">+{additions}</span>
      )}
      {deletions > 0 && (
        <span className="text-[var(--red)]">-{deletions}</span>
      )}
    </span>
  );
}

DiffStat.displayName = "DiffStat";

export { DiffStat };
export type { DiffStatProps };
```

#### `app/frontend/src/components/atoms/DiffStat/index.ts`

```ts
export { DiffStat } from "./DiffStat";
export type { DiffStatProps } from "./DiffStat";
```

---

### Phase 5: StatusBadge Molecule

Wraps the existing Badge atom with domain-specific status-to-color mapping.

#### `app/frontend/src/components/molecules/StatusBadge/StatusBadge.tsx`

```tsx
import { Badge } from "@/components/atoms";
import type { BadgeProps } from "@/components/atoms";

type StatusString =
  | "draft"
  | "created"
  | "pushed"
  | "local"
  | "open"
  | "reviewing"
  | "review"
  | "approved"
  | "ready"
  | "submitted"
  | "merged"
  | "closed"
  | "active";

const statusColorMap: Record<StatusString, BadgeProps["color"]> = {
  draft: "default",
  created: "default",
  pushed: "default",
  local: "default",
  active: "accent",
  open: "accent",
  reviewing: "accent",
  review: "purple",
  approved: "purple",
  ready: "purple",
  submitted: "yellow",
  merged: "green",
  closed: "red",
};

const statusLabelMap: Record<StatusString, string> = {
  draft: "Draft",
  created: "Local",
  pushed: "Pushed",
  local: "Local",
  active: "Active",
  open: "Open",
  reviewing: "Reviewing",
  review: "Review",
  approved: "Approved",
  ready: "Ready",
  submitted: "Submitted",
  merged: "Merged",
  closed: "Closed",
};

interface StatusBadgeProps {
  status: string;
}

function StatusBadge({ status }: StatusBadgeProps) {
  const key = status as StatusString;
  const color = statusColorMap[key] ?? "default";
  const label = statusLabelMap[key] ?? status;

  return (
    <Badge size="sm" color={color}>
      {label}
    </Badge>
  );
}

StatusBadge.displayName = "StatusBadge";

export { StatusBadge };
export type { StatusBadgeProps, StatusString };
```

#### `app/frontend/src/components/molecules/StatusBadge/index.ts`

```ts
export { StatusBadge } from "./StatusBadge";
export type { StatusBadgeProps, StatusString } from "./StatusBadge";
```

Create directory first: `mkdir -p app/frontend/src/components/molecules/StatusBadge`

---

### Phase 6: StackItem Molecule

One branch row in the sidebar. Composes StackDot, title, StatusBadge, and DiffStat.

#### `app/frontend/src/components/molecules/StackItem/StackItem.tsx`

```tsx
import { cn } from "@/lib/utils";
import { StackDot } from "@/components/atoms";
import type { StackDotColor } from "@/components/atoms";
import { DiffStat } from "@/components/atoms";
import { StatusBadge } from "@/components/molecules/StatusBadge";

interface StackItemProps {
  title: string;
  status: string;
  additions?: number;
  deletions?: number;
  isActive?: boolean;
  isFirst?: boolean;
  isLast?: boolean;
  onClick?: () => void;
}

function getStackDotColor(status: string, isActive: boolean): StackDotColor {
  if (status === "merged") return "green";
  if (isActive) return "accent";
  return "default";
}

function StackItem({
  title,
  status,
  additions = 0,
  deletions = 0,
  isActive = false,
  isFirst = false,
  isLast = false,
  onClick,
}: StackItemProps) {
  const dotColor = getStackDotColor(status, isActive);

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-stretch gap-3 w-full px-3 py-2.5 text-left transition-colors rounded-md",
        isActive
          ? "bg-[var(--accent-muted)] text-[var(--accent)]"
          : "text-[var(--fg-default)] hover:bg-[var(--bg-surface-hover)]"
      )}
    >
      <StackDot color={dotColor} isFirst={isFirst} isLast={isLast} />
      <div className="flex flex-col gap-1 min-w-0 flex-1">
        <span
          className={cn(
            "text-sm font-medium truncate",
            isActive ? "text-[var(--accent)]" : "text-[var(--fg-default)]"
          )}
        >
          {title}
        </span>
        <div className="flex items-center gap-2">
          <StatusBadge status={status} />
          {(additions > 0 || deletions > 0) && (
            <DiffStat additions={additions} deletions={deletions} />
          )}
        </div>
      </div>
    </button>
  );
}

StackItem.displayName = "StackItem";

export { StackItem };
export type { StackItemProps };
```

#### `app/frontend/src/components/molecules/StackItem/index.ts`

```ts
export { StackItem } from "./StackItem";
export type { StackItemProps } from "./StackItem";
```

---

### Phase 7: StackConnector Molecule

Vertical list of StackItems. Maps array of branch data to StackItems and handles isFirst/isLast logic.

#### `app/frontend/src/components/molecules/StackConnector/StackConnector.tsx`

```tsx
import { StackItem } from "@/components/molecules/StackItem";

interface StackConnectorItem {
  id: string;
  title: string;
  status: string;
  additions?: number;
  deletions?: number;
}

interface StackConnectorProps {
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

function StackConnector({ items, activeIndex, onSelect }: StackConnectorProps) {
  return (
    <div className="flex flex-col">
      {items.map((item, index) => (
        <StackItem
          key={item.id}
          title={item.title}
          status={item.status}
          additions={item.additions}
          deletions={item.deletions}
          isActive={index === activeIndex}
          isFirst={index === 0}
          isLast={index === items.length - 1}
          onClick={() => onSelect(index)}
        />
      ))}
    </div>
  );
}

StackConnector.displayName = "StackConnector";

export { StackConnector };
export type { StackConnectorProps, StackConnectorItem };
```

#### `app/frontend/src/components/molecules/StackConnector/index.ts`

```ts
export { StackConnector } from "./StackConnector";
export type { StackConnectorProps, StackConnectorItem } from "./StackConnector";
```

---

### Phase 8: StackSidebar Organism

Full sidebar panel with header and branch list.

#### `app/frontend/src/components/organisms/StackSidebar/StackSidebar.tsx`

```tsx
import { Icon } from "@/components/atoms";
import { StackConnector } from "@/components/molecules/StackConnector";
import type { StackConnectorItem } from "@/components/molecules/StackConnector";

interface StackSidebarProps {
  stackName: string;
  trunk: string;
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

function StackSidebar({
  stackName,
  trunk,
  items,
  activeIndex,
  onSelect,
}: StackSidebarProps) {
  return (
    <aside
      className="flex flex-col h-full w-[var(--sidebar-width)] border-r border-[var(--border)] bg-[var(--bg-surface)]"
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-muted)]">
        <Icon name="git-branch" size="sm" className="text-[var(--fg-muted)]" />
        <div className="flex flex-col min-w-0">
          <span className="text-sm font-semibold text-[var(--fg-default)] truncate">
            {stackName}
          </span>
          <span className="text-xs text-[var(--fg-subtle)]">
            {trunk}
          </span>
        </div>
      </div>

      {/* Branch list */}
      <div className="flex-1 overflow-y-auto px-1 py-2">
        <StackConnector
          items={items}
          activeIndex={activeIndex}
          onSelect={onSelect}
        />
      </div>
    </aside>
  );
}

StackSidebar.displayName = "StackSidebar";

export { StackSidebar };
export type { StackSidebarProps };
```

#### `app/frontend/src/components/organisms/StackSidebar/index.ts`

```ts
export { StackSidebar } from "./StackSidebar";
export type { StackSidebarProps } from "./StackSidebar";
```

Create directory first: `mkdir -p app/frontend/src/components/organisms/StackSidebar`

---

### Phase 9: useStackDetail Hook

Simple fetch hook. For MVP, returns mock data immediately (no actual fetch). The hook signature is ready for real API integration.

#### `app/frontend/src/hooks/useStackDetail.ts`

```ts
import { useState } from "react";
import type { StackDetail } from "@/types/stack";
import { mockStackDetail } from "@/lib/mock-data";

interface UseStackDetailResult {
  data: StackDetail | null;
  loading: boolean;
  error: string | null;
}

export function useStackDetail(_stackId?: string): UseStackDetailResult {
  // MVP: return mock data directly. Replace with real fetch when backend is wired.
  const [data] = useState<StackDetail | null>(mockStackDetail);
  const [loading] = useState(false);
  const [error] = useState<string | null>(null);

  return { data, loading, error };
}
```

Create directory first: `mkdir -p app/frontend/src/hooks`

---

### Phase 10: Barrel Exports

#### Update `app/frontend/src/components/atoms/index.ts`

Replace the entire file with:

```ts
export { Badge, badgeVariants } from "./Badge";
export type { BadgeProps } from "./Badge";

export { Icon, iconPaths, sizeMap } from "./Icon";
export type { IconName, IconSize, IconProps } from "./Icon";

export { Button, buttonVariants } from "./Button";
export type { ButtonProps } from "./Button";

export {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "./Collapsible";

export { Tab } from "./Tab";
export type { TabProps } from "./Tab";
export { CountBadge } from "./Tab";
export type { CountBadgeProps } from "./Tab";

export { StackDot } from "./StackDot";
export type { StackDotProps, StackDotColor } from "./StackDot";

export { DiffStat } from "./DiffStat";
export type { DiffStatProps } from "./DiffStat";
```

#### Create `app/frontend/src/components/molecules/index.ts`

```ts
export { StatusBadge } from "./StatusBadge";
export type { StatusBadgeProps, StatusString } from "./StatusBadge";

export { StackItem } from "./StackItem";
export type { StackItemProps } from "./StackItem";

export { StackConnector } from "./StackConnector";
export type { StackConnectorProps, StackConnectorItem } from "./StackConnector";
```

#### Create `app/frontend/src/components/organisms/index.ts`

```ts
export { StackSidebar } from "./StackSidebar";
export type { StackSidebarProps } from "./StackSidebar";
```

---

### Phase 11: Wire App.tsx

Replace `app/frontend/src/App.tsx` with:

```tsx
import { useState } from "react";
import { StackSidebar } from "@/components/organisms";
import { useStackDetail } from "@/hooks/useStackDetail";
import type { StackConnectorItem } from "@/components/molecules";

function branchTitle(name: string): string {
  // Extract the last segment: "dug/frontend-mvp/3-stack-nav" → "3-stack-nav"
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}

export function App() {
  const { data, loading, error } = useStackDetail();
  const [activeIndex, setActiveIndex] = useState(2); // Default to 3rd branch (current work)

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] flex items-center justify-center">
        <p className="text-[var(--fg-muted)] text-sm">Loading...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] flex items-center justify-center">
        <p className="text-[var(--red)] text-sm">{error ?? "No data"}</p>
      </div>
    );
  }

  const items: StackConnectorItem[] = data.branches.map((b) => {
    // Determine the display status: prefer PR state over branch state
    const displayStatus = b.pull_request?.state ?? b.branch.state;

    return {
      id: b.branch.id,
      title: branchTitle(b.branch.name),
      status: displayStatus,
      // Mock diff stats — in production these come from the diff endpoint
      additions: b.pull_request ? Math.floor(Math.random() * 200) + 10 : 0,
      deletions: b.pull_request ? Math.floor(Math.random() * 80) + 5 : 0,
    };
  });

  return (
    <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] font-[family-name:var(--font-sans)]">
      <StackSidebar
        stackName={data.stack.name}
        trunk={data.stack.trunk}
        items={items}
        activeIndex={activeIndex}
        onSelect={setActiveIndex}
      />
      {/* Main content area — placeholder until SB-038 (App Shell) */}
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold tracking-tight">
            {items[activeIndex]?.title ?? "Select a branch"}
          </h1>
          <p className="text-[var(--fg-muted)] text-sm">
            Diff review panel will render here (SB-039).
          </p>
          <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--fg-subtle)]">
            v0.0.1 &middot; Stack Bench
          </p>
        </div>
      </main>
    </div>
  );
}
```

**Note on diff stats:** The `additions`/`deletions` use `Math.random()` as temporary placeholders. This is acceptable for MVP visual development. In production, these values come from a diff API endpoint. To make the mock data deterministic, the builder MAY replace the random values with fixed numbers per branch:

```ts
// Deterministic alternative (builder may use either approach):
const mockDiffStats: Record<string, { additions: number; deletions: number }> = {
  "b-001": { additions: 48, deletions: 12 },
  "b-002": { additions: 156, deletions: 23 },
  "b-003": { additions: 89, deletions: 34 },
  "b-004": { additions: 0, deletions: 0 },
};
```

---

### Phase 12: Verification

1. **TypeScript compiles cleanly:**
   ```bash
   cd app/frontend && npx tsc --noEmit
   ```
   No errors.

2. **Dev server starts:**
   ```bash
   cd app/frontend && npm run dev
   ```
   Confirm no build errors.

3. **Visual verification in browser:**
   - Sidebar renders at 320px width on the left with surface background
   - Header shows "frontend-mvp" stack name and "main" trunk label
   - 4 branches display in order with connected dot lines
   - Branches 1-2 show green dots and "Merged" badges
   - Branch 3 shows blue/accent dot (active), "Open" badge, and diff stats
   - Branch 4 shows gray dot, "Local" badge, no diff stats
   - Clicking a branch updates the active state and main content title
   - Connector lines are continuous between dots, truncated at first/last

4. **Build succeeds:**
   ```bash
   cd app/frontend && npm run build
   ```

## File Inventory

| File | Action | Purpose |
|------|--------|---------|
| `src/types/stack.ts` | Create | TypeScript interfaces matching backend API |
| `src/lib/mock-data.ts` | Create | Realistic mock stack data (4 branches) |
| `src/hooks/useStackDetail.ts` | Create | Fetch hook (mock for MVP) |
| `src/components/atoms/StackDot/StackDot.tsx` | Create | Colored circle with connector line |
| `src/components/atoms/StackDot/index.ts` | Create | Barrel |
| `src/components/atoms/DiffStat/DiffStat.tsx` | Create | Inline +N -N display |
| `src/components/atoms/DiffStat/index.ts` | Create | Barrel |
| `src/components/atoms/index.ts` | Modify | Add StackDot + DiffStat exports |
| `src/components/molecules/StatusBadge/StatusBadge.tsx` | Create | Badge with domain status presets |
| `src/components/molecules/StatusBadge/index.ts` | Create | Barrel |
| `src/components/molecules/StackItem/StackItem.tsx` | Create | Single branch row |
| `src/components/molecules/StackItem/index.ts` | Create | Barrel |
| `src/components/molecules/StackConnector/StackConnector.tsx` | Create | Vertical connected list |
| `src/components/molecules/StackConnector/index.ts` | Create | Barrel |
| `src/components/molecules/index.ts` | Create | Barrel for all molecules |
| `src/components/organisms/StackSidebar/StackSidebar.tsx` | Create | Full sidebar panel |
| `src/components/organisms/StackSidebar/index.ts` | Create | Barrel |
| `src/components/organisms/index.ts` | Create | Barrel for all organisms |
| `src/App.tsx` | Modify | Render StackSidebar with mock data |

## Open Questions

None. All design decisions are settled.
