---
title: "SB-038: App Shell + Chrome (layout, tabs, PR header)"
date: 2026-03-21
status: draft
branch: dugshub/frontend-mvp/1-ep-006-frontend-mvp-stack-review-ui
depends_on:
  - SB-036
  - SB-037
adrs: []
---

# SB-038: App Shell + Chrome (layout, tabs, PR header)

## Goal

Build the app layout composing StackSidebar with the main content area. Main area shows the selected branch's PR header, tab bar, content panel, and action bar. Selection state from sidebar drives the main content. App.tsx becomes thin — just `useStackDetail()` + `AppShell` render.

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | `BranchMeta` atom | -- |
| 2 | `PRHeader` molecule | Phase 1 |
| 3 | `TabBar` molecule | Tab + CountBadge from SB-036 |
| 4 | `ActionBar` molecule | Button, StatusBadge from SB-036/037 |
| 5 | `AppShell` organism | Phase 2, 3, 4 + StackSidebar from SB-037 |
| 6 | Update `App.tsx` | Phase 5 |
| 7 | Barrel exports | Phase 1-5 |
| 8 | Verification | Phase 6, 7 |

## Phase Details

### Phase 1: BranchMeta Atom

Monospace display of `base ← head` with accent-colored arrow.

#### `app/frontend/src/components/atoms/BranchMeta/BranchMeta.tsx`

```tsx
import { cn } from "@/lib/utils";

interface BranchMetaProps {
  base: string;
  head: string;
  className?: string;
}

function BranchMeta({ base, head, className }: BranchMetaProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-[family-name:var(--font-mono)] text-xs text-[var(--fg-muted)]",
        className
      )}
    >
      <span>{base}</span>
      <span className="text-[var(--accent)]">&larr;</span>
      <span>{head}</span>
    </span>
  );
}

BranchMeta.displayName = "BranchMeta";

export { BranchMeta };
export type { BranchMetaProps };
```

#### `app/frontend/src/components/atoms/BranchMeta/index.ts`

```ts
export { BranchMeta } from "./BranchMeta";
export type { BranchMetaProps } from "./BranchMeta";
```

---

### Phase 2: PRHeader Molecule

PR title + branch info + description. When no PR exists, shows branch name as title and "No pull request" as description.

#### `app/frontend/src/components/molecules/PRHeader/PRHeader.tsx`

```tsx
import { BranchMeta } from "@/components/atoms/BranchMeta";

interface PRHeaderProps {
  title: string;
  baseBranch: string;
  headBranch: string;
  description?: string | null;
}

function PRHeader({ title, baseBranch, headBranch, description }: PRHeaderProps) {
  return (
    <div className="px-6 py-5 bg-[var(--bg-surface)] border-b border-[var(--border)]">
      <h2 className="text-xl font-semibold text-[var(--fg-default)] leading-tight">
        {title}
      </h2>
      <div className="mt-2">
        <BranchMeta base={baseBranch} head={headBranch} />
      </div>
      {description && (
        <p className="mt-3 text-sm text-[var(--fg-muted)] leading-relaxed">
          {description}
        </p>
      )}
    </div>
  );
}

PRHeader.displayName = "PRHeader";

export { PRHeader };
export type { PRHeaderProps };
```

#### `app/frontend/src/components/molecules/PRHeader/index.ts`

```ts
export { PRHeader } from "./PRHeader";
export type { PRHeaderProps } from "./PRHeader";
```

---

### Phase 3: TabBar Molecule

Horizontal row of Tab atoms with active state management. Uses Tab + CountBadge from SB-036.

#### `app/frontend/src/components/molecules/TabBar/TabBar.tsx`

```tsx
import { Tab, CountBadge } from "@/components/atoms";

interface TabItem {
  id: string;
  label: string;
  count?: number;
}

interface TabBarProps {
  tabs: TabItem[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

function TabBar({ tabs, activeTab, onTabChange }: TabBarProps) {
  return (
    <div
      className="flex items-end gap-0 px-6 bg-[var(--bg-surface)] border-b border-[var(--border)]"
      role="tablist"
    >
      {tabs.map((tab) => (
        <Tab
          key={tab.id}
          active={tab.id === activeTab}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.label}
          {tab.count !== undefined && (
            <CountBadge count={tab.count} />
          )}
        </Tab>
      ))}
    </div>
  );
}

TabBar.displayName = "TabBar";

export { TabBar };
export type { TabBarProps, TabItem };
```

#### `app/frontend/src/components/molecules/TabBar/index.ts`

```ts
export { TabBar } from "./TabBar";
export type { TabBarProps, TabItem } from "./TabBar";
```

---

### Phase 4: ActionBar Molecule

Bottom bar with status on the left and action buttons on the right. For MVP: StatusBadge on the left, "Mark ready & push" Button on the right (inert).

#### `app/frontend/src/components/molecules/ActionBar/ActionBar.tsx`

```tsx
import { Button } from "@/components/atoms";
import { StatusBadge } from "@/components/molecules/StatusBadge";

interface ActionBarProps {
  status: string;
  onPush?: () => void;
}

function ActionBar({ status, onPush }: ActionBarProps) {
  return (
    <div className="flex items-center justify-between px-6 py-3 bg-[var(--bg-surface)] border-t border-[var(--border)]">
      <div className="flex items-center gap-2">
        <StatusBadge status={status} />
        <span className="text-xs text-[var(--fg-muted)]">
          {status === "created" ? "Not yet pushed" : `Status: ${status}`}
        </span>
      </div>
      <Button
        variant="primary"
        size="sm"
        onClick={onPush}
        disabled={!onPush}
      >
        Mark ready &amp; push
      </Button>
    </div>
  );
}

ActionBar.displayName = "ActionBar";

export { ActionBar };
export type { ActionBarProps };
```

#### `app/frontend/src/components/molecules/ActionBar/index.ts`

```ts
export { ActionBar } from "./ActionBar";
export type { ActionBarProps } from "./ActionBar";
```

---

### Phase 5: AppShell Organism

Full page layout composing StackSidebar (fixed left) + main area. Main area is a flex column: PRHeader, TabBar, content slot (flex-1, scroll), ActionBar. Selection state drives everything.

#### `app/frontend/src/components/organisms/AppShell/AppShell.tsx`

```tsx
import type { ReactNode } from "react";
import { StackSidebar } from "@/components/organisms/StackSidebar";
import { PRHeader } from "@/components/molecules/PRHeader";
import { TabBar } from "@/components/molecules/TabBar";
import type { TabItem } from "@/components/molecules/TabBar";
import { ActionBar } from "@/components/molecules/ActionBar";
import type { StackConnectorItem } from "@/components/molecules/StackConnector";
import type { BranchWithPR } from "@/types/stack";

interface AppShellProps {
  stackName: string;
  trunk: string;
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
  activeBranch: BranchWithPR | null;
  tabs: TabItem[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  children?: ReactNode;
}

/** Extract short branch name from full ref: "dug/frontend-mvp/3-stack-nav" → "3-stack-nav" */
function shortBranch(name: string): string {
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}

function AppShell({
  stackName,
  trunk,
  items,
  activeIndex,
  onSelect,
  activeBranch,
  tabs,
  activeTab,
  onTabChange,
  children,
}: AppShellProps) {
  // Derive PRHeader props from the active branch
  const pr = activeBranch?.pull_request;
  const branchName = activeBranch?.branch.name ?? "";
  const title = pr?.title ?? shortBranch(branchName);
  const description = pr?.description ?? (pr ? null : "No pull request");
  const headBranch = shortBranch(branchName);

  // Base branch: for position 1, base is trunk. For others, it's the previous branch.
  const position = activeBranch?.branch.position ?? 1;
  const baseBranch = position <= 1 ? trunk : shortBranch(
    // Find branch at position - 1
    items[activeIndex - 1]?.title ?? trunk
  );

  // Display status: prefer PR state over branch state
  const displayStatus = pr?.state ?? activeBranch?.branch.state ?? "created";

  return (
    <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] font-[family-name:var(--font-sans)]">
      <StackSidebar
        stackName={stackName}
        trunk={trunk}
        items={items}
        activeIndex={activeIndex}
        onSelect={onSelect}
      />
      <main className="flex-1 flex flex-col min-w-0">
        <PRHeader
          title={title}
          baseBranch={baseBranch}
          headBranch={headBranch}
          description={description}
        />
        <TabBar
          tabs={tabs}
          activeTab={activeTab}
          onTabChange={onTabChange}
        />
        <div className="flex-1 overflow-auto">
          {children}
        </div>
        <ActionBar status={displayStatus} />
      </main>
    </div>
  );
}

AppShell.displayName = "AppShell";

export { AppShell };
export type { AppShellProps };
```

#### `app/frontend/src/components/organisms/AppShell/index.ts`

```ts
export { AppShell } from "./AppShell";
export type { AppShellProps } from "./AppShell";
```

---

### Phase 6: Update App.tsx

App.tsx becomes thin: hook + data transform + AppShell. The `branchTitle` helper and `mockDiffStats` stay here since they're app-level data transforms, not component concerns.

#### `app/frontend/src/App.tsx`

Replace the entire file with:

```tsx
import { useState } from "react";
import { AppShell } from "@/components/organisms";
import { useStackDetail } from "@/hooks/useStackDetail";
import type { StackConnectorItem } from "@/components/molecules";
import type { TabItem } from "@/components/molecules/TabBar";

function branchTitle(name: string): string {
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}

const mockDiffStats: Record<string, { additions: number; deletions: number }> = {
  "b-001": { additions: 48, deletions: 12 },
  "b-002": { additions: 156, deletions: 23 },
  "b-003": { additions: 89, deletions: 34 },
  "b-004": { additions: 0, deletions: 0 },
};

export function App() {
  const { data, loading, error } = useStackDetail();
  const [activeIndex, setActiveIndex] = useState(2);
  const [activeTab, setActiveTab] = useState("files");

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
    const displayStatus = b.pull_request?.state ?? b.branch.state;
    const stats = mockDiffStats[b.branch.id] ?? { additions: 0, deletions: 0 };

    return {
      id: b.branch.id,
      title: branchTitle(b.branch.name),
      status: displayStatus,
      additions: stats.additions,
      deletions: stats.deletions,
    };
  });

  const activeBranch = data.branches[activeIndex] ?? null;

  // Compute file count from diff stats for the active branch
  const activeStats = mockDiffStats[activeBranch?.branch.id ?? ""];
  const fileCount = activeStats && (activeStats.additions > 0 || activeStats.deletions > 0)
    ? Math.ceil((activeStats.additions + activeStats.deletions) / 20)
    : 0;

  const tabs: TabItem[] = [
    { id: "files", label: "Files changed", count: fileCount || undefined },
  ];

  return (
    <AppShell
      stackName={data.stack.name}
      trunk={data.stack.trunk}
      items={items}
      activeIndex={activeIndex}
      onSelect={setActiveIndex}
      activeBranch={activeBranch}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
    >
      {/* Content slot — placeholder until SB-039 (Diff Review) */}
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-3">
          <p className="text-[var(--fg-muted)] text-sm">
            Diff review panel will render here (SB-039).
          </p>
          <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--fg-subtle)]">
            v0.0.1 &middot; Stack Bench
          </p>
        </div>
      </div>
    </AppShell>
  );
}
```

---

### Phase 7: Barrel Exports

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

export { BranchMeta } from "./BranchMeta";
export type { BranchMetaProps } from "./BranchMeta";
```

#### Update `app/frontend/src/components/molecules/index.ts`

Replace the entire file with:

```ts
export { StatusBadge } from "./StatusBadge";
export type { StatusBadgeProps, StatusString } from "./StatusBadge";

export { StackItem } from "./StackItem";
export type { StackItemProps } from "./StackItem";

export { StackConnector } from "./StackConnector";
export type { StackConnectorProps, StackConnectorItem } from "./StackConnector";

export { PRHeader } from "./PRHeader";
export type { PRHeaderProps } from "./PRHeader";

export { TabBar } from "./TabBar";
export type { TabBarProps, TabItem } from "./TabBar";

export { ActionBar } from "./ActionBar";
export type { ActionBarProps } from "./ActionBar";
```

#### Update `app/frontend/src/components/organisms/index.ts`

Replace the entire file with:

```ts
export { StackSidebar } from "./StackSidebar";
export type { StackSidebarProps } from "./StackSidebar";

export { AppShell } from "./AppShell";
export type { AppShellProps } from "./AppShell";
```

---

### Phase 8: Verification

1. **TypeScript compiles cleanly:**
   ```bash
   cd app/frontend && npx tsc --noEmit
   ```

2. **Dev server starts:**
   ```bash
   cd app/frontend && npm run dev
   ```

3. **Visual verification in browser:**
   - Full page: sidebar left (320px), main area right, no scroll on body
   - Selecting a branch in sidebar updates PRHeader with correct title and branch info
   - Branch with PR (e.g. index 2 "3-stack-nav"): shows PR title "Stack navigation sidebar + branch list", BranchMeta `2-shared-atoms <- 3-stack-nav`, and description
   - Branch without PR (e.g. index 3 "4-app-shell"): shows "4-app-shell" as title, "No pull request" as description
   - Tab bar shows single "Files changed" tab with count badge, active by default
   - Action bar pinned to bottom with StatusBadge and "Mark ready & push" button (disabled/inert)
   - Content slot between TabBar and ActionBar fills remaining space with scroll
   - Layout is full viewport height, main area scrolls independently

4. **Build succeeds:**
   ```bash
   cd app/frontend && npm run build
   ```

## File Inventory

| File | Action | Purpose |
|------|--------|---------|
| `src/components/atoms/BranchMeta/BranchMeta.tsx` | Create | `base <- head` monospace display |
| `src/components/atoms/BranchMeta/index.ts` | Create | Barrel |
| `src/components/atoms/index.ts` | Modify | Add BranchMeta export |
| `src/components/molecules/PRHeader/PRHeader.tsx` | Create | PR title + branch info + description |
| `src/components/molecules/PRHeader/index.ts` | Create | Barrel |
| `src/components/molecules/TabBar/TabBar.tsx` | Create | Horizontal tab row with active state |
| `src/components/molecules/TabBar/index.ts` | Create | Barrel |
| `src/components/molecules/ActionBar/ActionBar.tsx` | Create | Bottom bar: status + push button |
| `src/components/molecules/ActionBar/index.ts` | Create | Barrel |
| `src/components/molecules/index.ts` | Modify | Add PRHeader, TabBar, ActionBar exports |
| `src/components/organisms/AppShell/AppShell.tsx` | Create | Full layout: sidebar + main chrome |
| `src/components/organisms/AppShell/index.ts` | Create | Barrel |
| `src/components/organisms/index.ts` | Modify | Add AppShell export |
| `src/App.tsx` | Modify | Thin wrapper using AppShell |

## Open Questions

None. All design decisions are settled.
