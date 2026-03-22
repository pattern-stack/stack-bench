---
title: Sidebar Layout Merge — Unified Navigation
status: draft
created: 2026-03-22
branch: dugshub/round-2-polish/5-sidebar-merge
stack: round-2-polish
stack_index: 5
depends_on: 4-agent-panel
---

# Sidebar Layout Merge

## Problem

The current layout separates navigation across two surfaces:
- **StackSidebar** (left): branch list only
- **TabBar** (main content header): switches between "Files changed" (diff view) and "Source" (file explorer with its own nested sidebar)

The "Source" tab embeds a second sidebar inside `FileViewerPanel`, creating a jarring layout shift and duplicated chrome. Users must context-switch between tabs to navigate diffs vs. source, losing spatial continuity.

## Solution

Merge file navigation into the StackSidebar. Replace tabs with a sidebar toggle that switches between two tree views below the branch list:

- **Diffs mode** — shows changed files from diff data; clicking scrolls/focuses that file's diff in the main content
- **Files mode** — shows the full file explorer tree; clicking shows the file's syntax-highlighted content in the main content

```
┌──────────────────────────────────────────────────────────┐
│ Sidebar (320px)            │ Main Content       │ Agent  │
│                            │                    │        │
│ ┌── Stack ──────────────┐  │                    │        │
│ │ 1-scaffold    ●       │  │                    │        │
│ │ 2-atoms       ●       │  │  FilesChangedPanel │        │
│ │ 3-nav         ●       │  │  OR                │        │
│ └───────────────────────┘  │  PathBar +          │        │
│                            │  FileContent       │        │
│ [Diffs ◉] [Files ○]       │                    │        │
│                            │                    │        │
│ ┌── Tree ────────────────┐ │                    │        │
│ │ Changed files (diffs)  │ │                    │        │
│ │ OR full explorer tree  │ │                    │        │
│ └────────────────────────┘ │                    │        │
│                            │                    │        │
│ [Restack] [Push stack]     │                    │        │
└──────────────────────────────────────────────────────────┘
```

## Architecture

### New type: `SidebarMode`

```ts
// types/sidebar.ts
export type SidebarMode = "diffs" | "files";
```

### New atom: `SidebarModeToggle`

**Layer:** Atom (pure visual, no state)
**Path:** `components/atoms/SidebarModeToggle/`

Two-button segmented control. Receives `mode` and `onModeChange` via props. Displays counts (e.g., file count badge on "Diffs").

```tsx
interface SidebarModeToggleProps {
  mode: SidebarMode;
  onModeChange: (mode: SidebarMode) => void;
  diffFileCount?: number;
}
```

Design: compact pill/segmented control matching the existing `--bg-surface` / `--accent` tokens. Active segment uses `--accent-muted` bg + `--accent` text. Sits between branch list and tree area with `px-3 py-2` spacing.

### New molecule: `DiffFileList`

**Layer:** Molecule (single interaction — file selection from a flat list)
**Path:** `components/molecules/DiffFileList/`

Flat list of changed file paths derived from `DiffFile[]`. Each row shows the file icon, relative path, change type badge, and +/- stats. Clicking a file calls `onSelectFile(path)`.

```tsx
interface DiffFileListItem {
  path: string;
  changeType: "added" | "modified" | "deleted" | "renamed";
  additions: number;
  deletions: number;
}

interface DiffFileListProps {
  files: DiffFileListItem[];
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
}
```

Reuses `FileIcon` atom for file icons, `DiffBadge` and `DiffStat` atoms for change indicators. Renders with the same `--bg-surface` background and hover treatment as `FileTreeItem`.

### Modified organism: `StackSidebar`

**What changes:**
- Gains `sidebarMode`, `onSidebarModeChange` props
- Gains `diffFiles` prop (the `DiffFileListItem[]` for the current branch)
- Gains `fileTree`, `selectedPath`, `onSelectFile` props (forwarded to FileTree or DiffFileList)
- Gains optional `diffFileCount` for the toggle badge
- Gains optional `onRefresh` for the explorer toolbar
- Layout: branch list at top → `SidebarModeToggle` → tree area (flex-1 overflow-y-auto) → footer buttons

```tsx
interface StackSidebarProps {
  // Existing
  stackName: string;
  trunk: string;
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
  onRestackAll?: () => void;
  onPushStack?: () => void;

  // New
  sidebarMode: SidebarMode;
  onSidebarModeChange: (mode: SidebarMode) => void;
  diffFiles: DiffFileListItem[];
  fileTree: FileTreeNode | null;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
  diffFileCount?: number;
  onRefresh?: () => void;
}
```

**Internal layout structure:**
```tsx
<aside className="flex flex-col h-full w-[var(--sidebar-width)] ...">
  {/* Header — unchanged */}
  {/* Branch list (StackConnector) — unchanged, but NOT flex-1 anymore */}
  <div className="overflow-y-auto px-1 py-2">
    <StackConnector ... />
  </div>

  {/* Mode toggle */}
  <div className="px-3 py-2 border-t border-[var(--border-muted)]">
    <SidebarModeToggle mode={sidebarMode} onModeChange={onSidebarModeChange} diffFileCount={diffFileCount} />
  </div>

  {/* Tree area — takes remaining space */}
  <div className="flex-1 overflow-y-auto">
    {sidebarMode === "diffs" ? (
      <DiffFileList files={diffFiles} selectedPath={selectedPath} onSelectFile={onSelectFile} />
    ) : (
      fileTree && <FileTree tree={fileTree} selectedPath={selectedPath} onSelectFile={onSelectFile} onRefresh={onRefresh} />
    )}
  </div>

  {/* Footer — unchanged */}
</aside>
```

### Modified template: `AppShell`

**What changes:**
- **Remove** `tabs`, `activeTab`, `onTabChange` props
- **Remove** `TabBar` from the layout
- **Add** `sidebarMode` prop (passed through to drive content rendering)
- **Add** all new sidebar props and forward them to `StackSidebar`
- Main content area receives children as before (App.tsx determines what to render)

```tsx
interface AppShellProps {
  // Keep
  stackName: string;
  trunk: string;
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
  activeBranch: BranchWithPR | null;
  agentOpen: boolean;
  onAgentToggle: () => void;
  selectedLineCount: number;
  children?: ReactNode;

  // New sidebar props (forwarded to StackSidebar)
  sidebarMode: SidebarMode;
  onSidebarModeChange: (mode: SidebarMode) => void;
  diffFiles: DiffFileListItem[];
  fileTree: FileTreeNode | null;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
  diffFileCount?: number;
  onRefresh?: () => void;

  // Removed: tabs, activeTab, onTabChange
}
```

The layout simplifies — no more `<TabBar>` between `<PRHeader>` and content:

```tsx
<main className="flex-1 flex flex-col min-w-0">
  <PRHeader ... />
  <div className="flex-1 overflow-auto">
    {children}
  </div>
  <ActionBar ... />
</main>
```

### Modified: `App.tsx`

**What changes:**
- Replace `activeTab` state with `sidebarMode` state (`useState<SidebarMode>("diffs")`)
- Add `selectedPath` state for file selection in both modes
- Remove `TabItem[]` construction
- Derive `diffFiles: DiffFileListItem[]` from `diffData.files`
- Fetch `fileTree` via `useFileTree` (currently only fetched inside FileViewerPanel)
- Fetch `fileContent` via `useFileContent` when in files mode and a file is selected
- Content rendering logic:

```tsx
{sidebarMode === "diffs" && (
  diffData ? <FilesChangedPanel diffData={diffData} /> : <EmptyState />
)}
{sidebarMode === "files" && (
  fileContent ? (
    <>
      <PathBar path={fileContent.path} />
      <FileContent file={fileContent} />
    </>
  ) : (
    <EmptyState message="Select a file to view" />
  )
)}
```

- When `sidebarMode` changes, clear `selectedPath` (or keep it — TBD during implementation)
- When `activeIndex` changes (new branch selected), clear `selectedPath` and reset to diffs mode

### Removed usage: `FileViewerPanel`

`FileViewerPanel` is no longer rendered. Its responsibilities are split:
- **File tree** → rendered inside `StackSidebar` (files mode)
- **File content** → rendered directly in `App.tsx` main content area
- **PathBar** → rendered directly in `App.tsx` main content area

The component files can remain in the codebase (not deleted) but are no longer imported or used.

### Removed usage: `TabBar` in `AppShell`

`TabBar` is no longer rendered in `AppShell`. The component itself remains (it may be useful elsewhere later), but the import and usage are removed from `AppShell.tsx`.

## State Flow

```
App.tsx
├── sidebarMode: "diffs" | "files"     ← new, replaces activeTab
├── activeIndex: number                 ← existing (which branch)
├── selectedPath: string | null         ← new (which file in sidebar)
├── agentOpen: boolean                  ← existing
│
├── useBranchDiff(activeBranchId)       ← existing
├── useFileTree(activeBranchId)         ← moved up from FileViewerPanel
├── useFileContent(branchId, path)      ← moved up from FileViewerPanel
│
└── AppShell
    ├── StackSidebar
    │   ├── StackConnector (branch list)
    │   ├── SidebarModeToggle           ← new
    │   └── DiffFileList | FileTree     ← conditional on mode
    ├── PRHeader
    ├── Main content
    │   └── FilesChangedPanel | (PathBar + FileContent)  ← conditional on mode
    ├── ActionBar
    └── AgentPanel
```

## Diff File Selection → Scroll Behavior

When in diffs mode and the user clicks a file in `DiffFileList`:
1. `selectedPath` is set to that file's path
2. `FilesChangedPanel` receives a `focusedFile` prop
3. The diff for that file scrolls into view using `scrollIntoView({ behavior: 'smooth', block: 'start' })`
4. This requires each `DiffFileMolecule` to have a ref or id based on the file path

This is a follow-up enhancement. For the initial implementation, clicking a file in diffs mode just highlights it in the sidebar list. Scroll-to behavior can be added in a subsequent PR.

## Implementation Order

1. Create `SidebarModeToggle` atom
2. Create `DiffFileList` molecule
3. Modify `StackSidebar` — add toggle + tree area
4. Modify `AppShell` — remove TabBar, forward new props
5. Modify `App.tsx` — replace activeTab with sidebarMode, lift file tree/content hooks
6. Verify both modes work end-to-end

## Branch Strategy

Single branch `5-sidebar-merge` on the `round-2-polish` stack, building on top of `4-agent-panel`.
