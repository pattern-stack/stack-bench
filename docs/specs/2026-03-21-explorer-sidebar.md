---
title: VS Code-style Explorer Sidebar Polish
date: 2026-03-21
status: draft
branch: dugshub/file-viewer/2-explorer-polish
depends_on: [2026-03-21-file-viewer-scaffold]
adrs: []
---

# VS Code-style Explorer Sidebar Polish

## Goal

Elevate the file explorer sidebar from a basic tree to a VS Code-quality experience. Add a toolbar with collapse/expand/refresh actions, a search filter for fast file finding, indent guides, extension-aware file icons, and a breadcrumb path bar above file content.

## Current State

The explorer works but is visually basic:
- `FileTree` (organism) — renders tree recursively, manages expanded state
- `FileTreeItem` (molecule) — button with icon + name, depth-based padding
- `FileIcon` (atom) — generic file/folder icon via `Icon` atom
- `FileContent` (molecule) — already has a simple path display at top
- `FileViewerPanel` (organism) — wires tree + content side by side

## Component Breakdown

### New Components

| Component | Layer | Purpose |
|-----------|-------|---------|
| `SearchInput` | atom | Styled text input with search icon and clear button |
| `ExplorerToolbar` | molecule | Row of icon buttons: collapse all, expand all, refresh |
| `IndentGuide` | atom | Vertical line rendered at each depth level |
| `PathBar` | molecule | Breadcrumb-style path display with clickable segments |

### Modified Components

| Component | Layer | Changes |
|-----------|-------|---------|
| `FileIcon` | atom | Extension-aware colors/icons (tsx, ts, css, json, md, etc.) |
| `FileTreeItem` | molecule | Integrate `IndentGuide`, pass `fileName` for icon extension detection |
| `FileTree` | organism | Add toolbar, search filter, collapseAll/expandAll/refresh callbacks |
| `FileViewerPanel` | organism | Replace simple path text with `PathBar` molecule |
| `Icon` | atom | Add new icon paths: `search`, `x-circle`, `collapse-all`, `refresh-cw`, `expand-all` |

### Design Tokens

Add to `index.css`:
```css
--indent-guide: #21262d;          /* Indent guide line color */
--indent-guide-active: #30363d;   /* Indent guide on hover scope */
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Icon additions + FileIcon extension awareness | -- |
| 2 | IndentGuide atom + FileTreeItem integration | Phase 1 |
| 3 | SearchInput atom + ExplorerToolbar molecule | Phase 1 |
| 4 | FileTree search/filter + toolbar wiring | Phase 3 |
| 5 | PathBar molecule + FileViewerPanel integration | -- |

## Phase Details

### Phase 1: Icon & FileIcon Extension Awareness

**Icon atom** — add SVG paths for: `search`, `x-circle`, `collapse-all` (stacked chevrons pointing right), `refresh-cw`, `expand-all` (stacked chevrons pointing down).

**FileIcon atom** — accept `fileName` prop alongside `type`. Map extensions to colors:

| Extension | Color Token | Icon |
|-----------|------------|------|
| `.tsx`, `.jsx` | `var(--accent)` (blue) | file |
| `.ts`, `.js` | `var(--yellow)` | file |
| `.css`, `.scss` | `var(--purple)` | file |
| `.json` | `var(--yellow)` | file |
| `.md` | `var(--fg-muted)` (gray) | file |
| `.html` | `var(--red)` | file |
| `.go` | `var(--accent)` | file |
| `.py` | `var(--yellow)` | file |
| other | `var(--fg-subtle)` | file (current default) |

The `FileIcon` atom remains purely visual — it maps extension to color via a lookup object. No behavior, no state.

### Phase 2: IndentGuide + FileTreeItem

**IndentGuide atom:**
```tsx
interface IndentGuideProps {
  depth: number;
  className?: string;
}
```

Renders `depth` vertical lines, each 12px apart (matching current indent spacing). Uses CSS `border-left` with `var(--indent-guide)` color. Each guide is a `<span>` absolutely positioned within the tree item row.

Implementation approach: Instead of a separate component, use CSS pseudo-elements on FileTreeItem. For each depth level, render a `<span>` element that draws a 1px vertical line. This avoids extra DOM nesting.

**FileTreeItem changes:**
- Accept `fileName` prop (full filename like `App.tsx`) and pass to `FileIcon`
- Replace `paddingLeft` inline style with indent guides: render `depth` guide spans, each positioned at `n * 12 + 8` px from left
- Guides visible on hover via `group` hover on the tree item row

### Phase 3: SearchInput + ExplorerToolbar

**SearchInput atom:**
```tsx
interface SearchInputProps extends InputHTMLAttributes<HTMLInputElement> {
  onClear?: () => void;
}
```
- Compact input (h-7) with search icon on left, clear (x) button on right when value is non-empty
- Uses `var(--bg-inset)` background, `var(--border-muted)` border
- Focus ring uses `var(--accent)`

**ExplorerToolbar molecule:**
```tsx
interface ExplorerToolbarProps {
  title?: string;
  onCollapseAll: () => void;
  onExpandAll: () => void;
  onRefresh: () => void;
}
```
- Flex row: title on left ("EXPLORER"), icon buttons on right
- Icon buttons are `<button>` elements with `Icon` atoms, 24x24 hit target
- Subtle hover: `var(--bg-surface-hover)`
- Title uses `text-[11px] font-semibold tracking-wider uppercase text-[var(--fg-muted)]` (VS Code section header style)

### Phase 4: FileTree Search/Filter + Toolbar Wiring

**FileTree organism changes:**

State additions:
- `filterText: string` — current search input value
- `collapseAll()` — clears expanded set
- `expandAll()` — recursively adds all dir paths to expanded set
- `refresh()` — calls a new `onRefresh` callback prop (for re-fetching tree data)

Filter logic:
- When `filterText` is non-empty, walk the tree and collect all nodes whose `path` includes the filter text (case-insensitive substring match)
- Auto-expand parent directories of matched files
- Highlight matched portion of filename (wrap in `<mark>` with `var(--accent-muted)` background)
- Clear filter resets to previous expanded state (save/restore)

Layout within sidebar:
```
┌──────────────────────┐
│ EXPLORER   [⫿] [⫽] [↻]│  ← ExplorerToolbar
├──────────────────────┤
│ 🔍 Search files...   │  ← SearchInput
├──────────────────────┤
│ ▸ src/               │  ← FileTree (scrollable)
│   ▸ components/      │
│   ...                │
└──────────────────────┘
```

### Phase 5: PathBar + FileViewerPanel Integration

**PathBar molecule:**
```tsx
interface PathBarProps {
  path: string;
  onNavigate?: (segmentPath: string) => void;
}
```
- Splits path on `/` and renders each segment as a clickable breadcrumb
- Segments separated by `>` chevron icons (xs size)
- Last segment is bold/highlighted, previous segments are `var(--fg-muted)`
- `onNavigate` fires with the path up to that segment (for future: clicking a dir segment could expand it in the tree)
- File extension of last segment gets the same color as `FileIcon` extension mapping

**FileViewerPanel changes:**
- Replace the existing `FileContent` path breadcrumb line (line 16 of FileContent.tsx) — extract path display out of `FileContent` and into `FileViewerPanel` using `PathBar`
- `FileContent` becomes purely about rendering code, `PathBar` sits above it in the panel layout

## File Manifest

```
# New files
app/frontend/src/components/atoms/SearchInput/SearchInput.tsx
app/frontend/src/components/atoms/SearchInput/index.ts
app/frontend/src/components/atoms/IndentGuide/IndentGuide.tsx
app/frontend/src/components/atoms/IndentGuide/index.ts
app/frontend/src/components/molecules/ExplorerToolbar/ExplorerToolbar.tsx
app/frontend/src/components/molecules/ExplorerToolbar/index.ts
app/frontend/src/components/molecules/PathBar/PathBar.tsx
app/frontend/src/components/molecules/PathBar/index.ts

# Modified files
app/frontend/src/components/atoms/Icon/Icon.tsx              # New icon paths
app/frontend/src/components/atoms/FileIcon/FileIcon.tsx      # Extension colors
app/frontend/src/components/molecules/FileTreeItem/FileTreeItem.tsx  # Indent guides, fileName
app/frontend/src/components/molecules/FileContent/FileContent.tsx    # Remove path display
app/frontend/src/components/organisms/FileTree/FileTree.tsx  # Toolbar, search, expand/collapse
app/frontend/src/components/organisms/FileViewerPanel/FileViewerPanel.tsx  # PathBar integration
app/frontend/src/index.css                                   # Indent guide tokens
```

## Open Questions

1. Should `SearchInput` be a shared atom reusable outside file tree, or scoped specifically? → Recommend shared atom — search inputs will appear elsewhere.
2. Should fuzzy matching (fzf-style) be used instead of substring? → Start with substring, upgrade later if needed. Keep the filter function in a `lib/` util so it's swappable.
3. Should indent guides highlight the "active scope" (the vertical line for the directory containing the selected file)? → Nice to have, defer to iteration.
