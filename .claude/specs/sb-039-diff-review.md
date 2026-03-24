---
title: "SB-039: Diff Review (diff viewer, mock data, no backend)"
date: 2026-03-21
status: draft
branch: dugshub/frontend-mvp/1-ep-006-frontend-mvp-stack-review-ui
depends_on:
  - SB-036
  - SB-037
  - SB-038
adrs: []
---

# SB-039: Diff Review (diff viewer, mock data, no backend)

## Goal

Build the diff viewer panel that renders file changes for a selected branch. This is the main content area inside AppShell's content slot. Uses mock diff data on the frontend only — no backend endpoint. The mock data follows the proposed JSON structure so the real endpoint can be wired later with zero component changes.

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Diff types | -- |
| 2 | Mock diff data | Phase 1 |
| 3 | `useBranchDiff` hook | Phase 2 |
| 4 | `DiffLineAtom` atom | Phase 1 |
| 5 | `DiffBadge` atom | -- |
| 6 | `FileListSummary` molecule | Phase 1 |
| 7 | `DiffHunk` molecule | Phase 4 |
| 8 | `DiffFileHeader` molecule | Phase 5, existing DiffStat + Icon + Collapsible |
| 9 | `DiffFile` molecule | Phase 7, 8 |
| 10 | `FilesChangedPanel` organism | Phase 6, 9 |
| 11 | Update `App.tsx` | Phase 3, 10 |
| 12 | Barrel exports | Phase 4-10 |
| 13 | Verification | Phase 11, 12 |

## Phase Details

### Phase 1: Diff Types

#### `app/frontend/src/types/diff.ts`

```ts
export interface DiffLine {
  type: "context" | "add" | "del" | "hunk";
  old_num: number | null;
  new_num: number | null;
  content: string;
}

export interface DiffHunk {
  header: string;
  lines: DiffLine[];
}

export interface DiffFile {
  path: string;
  change_type: "added" | "modified" | "deleted" | "renamed";
  additions: number;
  deletions: number;
  hunks: DiffHunk[];
}

export interface DiffData {
  files: DiffFile[];
  total_additions: number;
  total_deletions: number;
}
```

---

### Phase 2: Mock Diff Data

#### `app/frontend/src/lib/mock-diff-data.ts`

```ts
import type { DiffData } from "@/types/diff";

/**
 * Mock diff data keyed by branch ID.
 * Each entry contains realistic file diffs with TypeScript/React code.
 */
export const mockDiffDataByBranch: Record<string, DiffData> = {
  // Branch b-001: scaffold — mostly new files
  "b-001": {
    total_additions: 48,
    total_deletions: 12,
    files: [
      {
        path: "app/frontend/package.json",
        change_type: "added",
        additions: 28,
        deletions: 0,
        hunks: [
          {
            header: "@@ -0,0 +1,28 @@",
            lines: [
              { type: "add", old_num: null, new_num: 1, content: "{" },
              { type: "add", old_num: null, new_num: 2, content: '  "name": "@stack-bench/frontend",' },
              { type: "add", old_num: null, new_num: 3, content: '  "private": true,' },
              { type: "add", old_num: null, new_num: 4, content: '  "version": "0.0.1",' },
              { type: "add", old_num: null, new_num: 5, content: '  "type": "module",' },
              { type: "add", old_num: null, new_num: 6, content: '  "scripts": {' },
              { type: "add", old_num: null, new_num: 7, content: '    "dev": "vite --port 3000",' },
              { type: "add", old_num: null, new_num: 8, content: '    "build": "tsc -b && vite build"' },
              { type: "add", old_num: null, new_num: 9, content: "  }," },
              { type: "add", old_num: null, new_num: 10, content: '  "dependencies": {' },
              { type: "add", old_num: null, new_num: 11, content: '    "react": "^18.3.0",' },
              { type: "add", old_num: null, new_num: 12, content: '    "react-dom": "^18.3.0"' },
              { type: "add", old_num: null, new_num: 13, content: "  }" },
              { type: "add", old_num: null, new_num: 14, content: "}" },
            ],
          },
        ],
      },
      {
        path: "app/frontend/src/index.css",
        change_type: "modified",
        additions: 20,
        deletions: 12,
        hunks: [
          {
            header: "@@ -1,15 +1,23 @@",
            lines: [
              { type: "context", old_num: 1, new_num: 1, content: '@import "tailwindcss";' },
              { type: "context", old_num: 2, new_num: 2, content: "" },
              { type: "del", old_num: 3, new_num: null, content: "/* Default theme */" },
              { type: "del", old_num: 4, new_num: null, content: ":root {" },
              { type: "del", old_num: 5, new_num: null, content: "  --bg: white;" },
              { type: "del", old_num: 6, new_num: null, content: "  --fg: #111;" },
              { type: "del", old_num: 7, new_num: null, content: "}" },
              { type: "add", old_num: null, new_num: 3, content: "/*" },
              { type: "add", old_num: null, new_num: 4, content: " * Stack Bench — Dark Design System Tokens" },
              { type: "add", old_num: null, new_num: 5, content: " */" },
              { type: "add", old_num: null, new_num: 6, content: ":root {" },
              { type: "add", old_num: null, new_num: 7, content: "  --bg-canvas: #0d1117;" },
              { type: "add", old_num: null, new_num: 8, content: "  --bg-surface: #161b22;" },
              { type: "add", old_num: null, new_num: 9, content: "  --bg-surface-hover: #1c2128;" },
              { type: "add", old_num: null, new_num: 10, content: "  --border: #30363d;" },
              { type: "add", old_num: null, new_num: 11, content: "  --fg-default: #e6edf3;" },
              { type: "add", old_num: null, new_num: 12, content: "  --fg-muted: #7d8590;" },
              { type: "add", old_num: null, new_num: 13, content: "  --green: #3fb950;" },
              { type: "add", old_num: null, new_num: 14, content: "  --red: #f85149;" },
              { type: "add", old_num: null, new_num: 15, content: "}" },
            ],
          },
          {
            header: "@@ -20,8 +28,13 @@",
            lines: [
              { type: "context", old_num: 20, new_num: 28, content: "body {" },
              { type: "context", old_num: 21, new_num: 29, content: "  margin: 0;" },
              { type: "context", old_num: 22, new_num: 30, content: "  padding: 0;" },
              { type: "del", old_num: 23, new_num: null, content: "  background-color: var(--bg);" },
              { type: "del", old_num: 24, new_num: null, content: "  color: var(--fg);" },
              { type: "del", old_num: 25, new_num: null, content: "  font-family: sans-serif;" },
              { type: "del", old_num: 26, new_num: null, content: "  line-height: 1.5;" },
              { type: "del", old_num: 27, new_num: null, content: "}" },
              { type: "add", old_num: null, new_num: 31, content: "  background-color: var(--bg-canvas);" },
              { type: "add", old_num: null, new_num: 32, content: "  color: var(--fg-default);" },
              { type: "add", old_num: null, new_num: 33, content: "  font-family: var(--font-sans);" },
              { type: "add", old_num: null, new_num: 34, content: "  -webkit-font-smoothing: antialiased;" },
              { type: "add", old_num: null, new_num: 35, content: "  -moz-osx-font-smoothing: grayscale;" },
              { type: "add", old_num: null, new_num: 36, content: "}" },
            ],
          },
        ],
      },
    ],
  },

  // Branch b-002: shared atoms — new component files
  "b-002": {
    total_additions: 156,
    total_deletions: 23,
    files: [
      {
        path: "app/frontend/src/components/atoms/Icon/Icon.tsx",
        change_type: "added",
        additions: 62,
        deletions: 0,
        hunks: [
          {
            header: "@@ -0,0 +1,62 @@",
            lines: [
              { type: "add", old_num: null, new_num: 1, content: 'import { forwardRef, type SVGAttributes } from "react";' },
              { type: "add", old_num: null, new_num: 2, content: 'import { cn } from "@/lib/utils";' },
              { type: "add", old_num: null, new_num: 3, content: "" },
              { type: "add", old_num: null, new_num: 4, content: "const iconPaths: Record<string, React.ReactNode> = {" },
              { type: "add", old_num: null, new_num: 5, content: '  "chevron-right": (' },
              { type: "add", old_num: null, new_num: 6, content: '    <polyline points="9 18 15 12 9 6" />' },
              { type: "add", old_num: null, new_num: 7, content: "  )," },
              { type: "add", old_num: null, new_num: 8, content: '  "chevron-down": (' },
              { type: "add", old_num: null, new_num: 9, content: '    <polyline points="6 9 12 15 18 9" />' },
              { type: "add", old_num: null, new_num: 10, content: "  )," },
              { type: "add", old_num: null, new_num: 11, content: "};" },
              { type: "add", old_num: null, new_num: 12, content: "" },
              { type: "add", old_num: null, new_num: 13, content: "type IconName = keyof typeof iconPaths;" },
            ],
          },
        ],
      },
      {
        path: "app/frontend/src/components/atoms/Badge/Badge.tsx",
        change_type: "added",
        additions: 54,
        deletions: 0,
        hunks: [
          {
            header: "@@ -0,0 +1,54 @@",
            lines: [
              { type: "add", old_num: null, new_num: 1, content: 'import { forwardRef, type HTMLAttributes } from "react";' },
              { type: "add", old_num: null, new_num: 2, content: 'import { cva, type VariantProps } from "class-variance-authority";' },
              { type: "add", old_num: null, new_num: 3, content: 'import { cn } from "@/lib/utils";' },
              { type: "add", old_num: null, new_num: 4, content: "" },
              { type: "add", old_num: null, new_num: 5, content: "const badgeVariants = cva(" },
              { type: "add", old_num: null, new_num: 6, content: '  "inline-flex items-center rounded-full font-medium",' },
              { type: "add", old_num: null, new_num: 7, content: "  {" },
              { type: "add", old_num: null, new_num: 8, content: "    variants: {" },
              { type: "add", old_num: null, new_num: 9, content: "      color: {" },
              { type: "add", old_num: null, new_num: 10, content: '        green: "bg-[var(--green-bg)] text-[var(--green)]",' },
              { type: "add", old_num: null, new_num: 11, content: '        red: "bg-[var(--red-bg)] text-[var(--red)]",' },
              { type: "add", old_num: null, new_num: 12, content: "      }," },
              { type: "add", old_num: null, new_num: 13, content: "    }," },
              { type: "add", old_num: null, new_num: 14, content: "  }" },
              { type: "add", old_num: null, new_num: 15, content: ");" },
            ],
          },
        ],
      },
      {
        path: "app/frontend/src/lib/utils.ts",
        change_type: "modified",
        additions: 5,
        deletions: 2,
        hunks: [
          {
            header: "@@ -1,4 +1,7 @@",
            lines: [
              { type: "del", old_num: 1, new_num: null, content: 'import { clsx } from "clsx";' },
              { type: "add", old_num: null, new_num: 1, content: 'import { clsx, type ClassValue } from "clsx";' },
              { type: "context", old_num: 2, new_num: 2, content: "" },
              { type: "del", old_num: 3, new_num: null, content: "export function cn(...inputs: string[]) {" },
              { type: "add", old_num: null, new_num: 3, content: "export function cn(...inputs: ClassValue[]): string {" },
              { type: "context", old_num: 4, new_num: 4, content: "  return clsx(inputs);" },
              { type: "context", old_num: 5, new_num: 5, content: "}" },
            ],
          },
        ],
      },
      {
        path: "app/frontend/src/components/atoms/Collapsible/Collapsible.tsx",
        change_type: "added",
        additions: 35,
        deletions: 0,
        hunks: [
          {
            header: "@@ -0,0 +1,29 @@",
            lines: [
              { type: "add", old_num: null, new_num: 1, content: "import {" },
              { type: "add", old_num: null, new_num: 2, content: "  Root," },
              { type: "add", old_num: null, new_num: 3, content: "  Trigger," },
              { type: "add", old_num: null, new_num: 4, content: "  Content," },
              { type: "add", old_num: null, new_num: 5, content: '} from "@radix-ui/react-collapsible";' },
              { type: "add", old_num: null, new_num: 6, content: 'import { forwardRef, type ComponentPropsWithoutRef } from "react";' },
              { type: "add", old_num: null, new_num: 7, content: 'import { cn } from "@/lib/utils";' },
              { type: "add", old_num: null, new_num: 8, content: "" },
              { type: "add", old_num: null, new_num: 9, content: "const Collapsible = Root;" },
              { type: "add", old_num: null, new_num: 10, content: "const CollapsibleTrigger = Trigger;" },
            ],
          },
        ],
      },
    ],
  },

  // Branch b-003: stack nav — modifying existing + adding molecules
  "b-003": {
    total_additions: 89,
    total_deletions: 34,
    files: [
      {
        path: "app/frontend/src/components/molecules/StackItem/StackItem.tsx",
        change_type: "added",
        additions: 45,
        deletions: 0,
        hunks: [
          {
            header: "@@ -0,0 +1,45 @@",
            lines: [
              { type: "add", old_num: null, new_num: 1, content: 'import { DiffStat } from "@/components/atoms";' },
              { type: "add", old_num: null, new_num: 2, content: 'import { StatusBadge } from "@/components/molecules/StatusBadge";' },
              { type: "add", old_num: null, new_num: 3, content: 'import { cn } from "@/lib/utils";' },
              { type: "add", old_num: null, new_num: 4, content: "" },
              { type: "add", old_num: null, new_num: 5, content: "interface StackItemProps {" },
              { type: "add", old_num: null, new_num: 6, content: "  title: string;" },
              { type: "add", old_num: null, new_num: 7, content: "  status: string;" },
              { type: "add", old_num: null, new_num: 8, content: "  additions: number;" },
              { type: "add", old_num: null, new_num: 9, content: "  deletions: number;" },
              { type: "add", old_num: null, new_num: 10, content: "  active?: boolean;" },
              { type: "add", old_num: null, new_num: 11, content: "  onClick?: () => void;" },
              { type: "add", old_num: null, new_num: 12, content: "}" },
            ],
          },
        ],
      },
      {
        path: "app/frontend/src/components/organisms/StackSidebar/StackSidebar.tsx",
        change_type: "added",
        additions: 32,
        deletions: 0,
        hunks: [
          {
            header: "@@ -0,0 +1,32 @@",
            lines: [
              { type: "add", old_num: null, new_num: 1, content: 'import { StackConnector } from "@/components/molecules/StackConnector";' },
              { type: "add", old_num: null, new_num: 2, content: 'import type { StackConnectorItem } from "@/components/molecules/StackConnector";' },
              { type: "add", old_num: null, new_num: 3, content: "" },
              { type: "add", old_num: null, new_num: 4, content: "interface StackSidebarProps {" },
              { type: "add", old_num: null, new_num: 5, content: "  stackName: string;" },
              { type: "add", old_num: null, new_num: 6, content: "  trunk: string;" },
              { type: "add", old_num: null, new_num: 7, content: "  items: StackConnectorItem[];" },
              { type: "add", old_num: null, new_num: 8, content: "  activeIndex: number;" },
              { type: "add", old_num: null, new_num: 9, content: "  onSelect: (index: number) => void;" },
              { type: "add", old_num: null, new_num: 10, content: "}" },
            ],
          },
        ],
      },
      {
        path: "app/frontend/src/App.tsx",
        change_type: "modified",
        additions: 12,
        deletions: 34,
        hunks: [
          {
            header: "@@ -1,40 +1,18 @@",
            lines: [
              { type: "context", old_num: 1, new_num: 1, content: 'import { useState } from "react";' },
              { type: "del", old_num: 2, new_num: null, content: 'import { Badge, Icon, DiffStat } from "@/components/atoms";' },
              { type: "add", old_num: null, new_num: 2, content: 'import { StackSidebar } from "@/components/organisms/StackSidebar";' },
              { type: "add", old_num: null, new_num: 3, content: 'import { useStackDetail } from "@/hooks/useStackDetail";' },
              { type: "context", old_num: 3, new_num: 4, content: "" },
              { type: "del", old_num: 4, new_num: null, content: "export function App() {" },
              { type: "del", old_num: 5, new_num: null, content: "  return (" },
              { type: "del", old_num: 6, new_num: null, content: '    <div className="p-8 space-y-4">' },
              { type: "del", old_num: 7, new_num: null, content: "      <h1>Component Gallery</h1>" },
              { type: "del", old_num: 8, new_num: null, content: "    </div>" },
              { type: "del", old_num: 9, new_num: null, content: "  );" },
              { type: "del", old_num: 10, new_num: null, content: "}" },
              { type: "add", old_num: null, new_num: 5, content: "export function App() {" },
              { type: "add", old_num: null, new_num: 6, content: "  const { data, loading, error } = useStackDetail();" },
              { type: "add", old_num: null, new_num: 7, content: '  const [activeIndex, setActiveIndex] = useState(2);' },
              { type: "add", old_num: null, new_num: 8, content: "  // ..." },
              { type: "add", old_num: null, new_num: 9, content: "}" },
            ],
          },
        ],
      },
    ],
  },

  // Branch b-004: no changes yet
  "b-004": {
    total_additions: 0,
    total_deletions: 0,
    files: [],
  },
};
```

---

### Phase 3: `useBranchDiff` Hook

#### `app/frontend/src/hooks/useBranchDiff.ts`

```ts
import { useState } from "react";
import type { DiffData } from "@/types/diff";
import { mockDiffDataByBranch } from "@/lib/mock-diff-data";

interface UseBranchDiffResult {
  data: DiffData | null;
  loading: boolean;
  error: string | null;
}

export function useBranchDiff(branchId: string | undefined): UseBranchDiffResult {
  // MVP: return mock data directly. Replace with real fetch when backend is wired.
  const [loading] = useState(false);
  const [error] = useState<string | null>(null);

  const data = branchId ? (mockDiffDataByBranch[branchId] ?? null) : null;

  return { data, loading, error };
}
```

---

### Phase 4: DiffLineAtom

Single diff line with gutter (line numbers) and content. Monospace throughout.

#### `app/frontend/src/components/atoms/DiffLine/DiffLine.tsx`

```tsx
import { cn } from "@/lib/utils";
import type { DiffLine as DiffLineType } from "@/types/diff";

interface DiffLineAtomProps {
  line: DiffLineType;
}

const bgMap: Record<DiffLineType["type"], string> = {
  add: "bg-[var(--green-bg)]",
  del: "bg-[var(--red-bg)]",
  context: "",
  hunk: "bg-[var(--accent-muted)]",
};

const prefixMap: Record<DiffLineType["type"], string> = {
  add: "+",
  del: "-",
  context: " ",
  hunk: "",
};

function DiffLineAtom({ line }: DiffLineAtomProps) {
  const isHunk = line.type === "hunk";

  return (
    <div
      className={cn(
        "flex font-[family-name:var(--font-mono)] text-xs leading-5 border-b border-[var(--border-muted)]/50",
        bgMap[line.type]
      )}
    >
      {/* Gutter: old line number */}
      <span
        className="w-[50px] shrink-0 text-right pr-2 pl-2 select-none text-[var(--fg-subtle)] border-r border-[var(--border-muted)]/50"
        aria-hidden="true"
      >
        {line.old_num ?? ""}
      </span>

      {/* Gutter: new line number */}
      <span
        className="w-[50px] shrink-0 text-right pr-2 pl-2 select-none text-[var(--fg-subtle)] border-r border-[var(--border-muted)]/50"
        aria-hidden="true"
      >
        {line.new_num ?? ""}
      </span>

      {/* Content */}
      <span
        className={cn(
          "flex-1 pl-2 pr-4 whitespace-pre",
          isHunk ? "text-[var(--fg-muted)] italic" : "text-[var(--fg-default)]"
        )}
      >
        {isHunk ? line.content : `${prefixMap[line.type]}${line.content}`}
      </span>
    </div>
  );
}

DiffLineAtom.displayName = "DiffLineAtom";

export { DiffLineAtom };
export type { DiffLineAtomProps };
```

#### `app/frontend/src/components/atoms/DiffLine/index.ts`

```ts
export { DiffLineAtom } from "./DiffLine";
export type { DiffLineAtomProps } from "./DiffLine";
```

---

### Phase 5: DiffBadge Atom

Single-letter badge indicating file change type. Uses the existing Badge atom's styling pattern but is a purpose-built component for compact display.

#### `app/frontend/src/components/atoms/DiffBadge/DiffBadge.tsx`

```tsx
import type { DiffFile } from "@/types/diff";

interface DiffBadgeProps {
  changeType: DiffFile["change_type"];
}

const badgeConfig: Record<
  DiffFile["change_type"],
  { letter: string; bg: string; fg: string }
> = {
  added: { letter: "A", bg: "bg-[var(--green-bg)]", fg: "text-[var(--green)]" },
  modified: { letter: "M", bg: "bg-[var(--yellow)]/10", fg: "text-[var(--yellow)]" },
  deleted: { letter: "D", bg: "bg-[var(--red-bg)]", fg: "text-[var(--red)]" },
  renamed: { letter: "R", bg: "bg-[var(--purple)]/10", fg: "text-[var(--purple)]" },
};

function DiffBadge({ changeType }: DiffBadgeProps) {
  const config = badgeConfig[changeType];

  return (
    <span
      className={`inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold leading-none ${config.bg} ${config.fg}`}
    >
      {config.letter}
    </span>
  );
}

DiffBadge.displayName = "DiffBadge";

export { DiffBadge };
export type { DiffBadgeProps };
```

#### `app/frontend/src/components/atoms/DiffBadge/index.ts`

```ts
export { DiffBadge } from "./DiffBadge";
export type { DiffBadgeProps } from "./DiffBadge";
```

---

### Phase 6: FileListSummary Molecule

Summary line: "Showing N changed files with +X additions and -Y deletions".

#### `app/frontend/src/components/molecules/FileListSummary/FileListSummary.tsx`

```tsx
interface FileListSummaryProps {
  fileCount: number;
  additions: number;
  deletions: number;
}

function FileListSummary({ fileCount, additions, deletions }: FileListSummaryProps) {
  return (
    <p className="text-xs text-[var(--fg-muted)] px-4 py-3">
      Showing{" "}
      <span className="text-[var(--fg-default)] font-medium">
        {fileCount} changed {fileCount === 1 ? "file" : "files"}
      </span>
      {" "}with{" "}
      <span className="text-[var(--green)] font-medium">+{additions}</span>
      {" "}and{" "}
      <span className="text-[var(--red)] font-medium">-{deletions}</span>
    </p>
  );
}

FileListSummary.displayName = "FileListSummary";

export { FileListSummary };
export type { FileListSummaryProps };
```

#### `app/frontend/src/components/molecules/FileListSummary/index.ts`

```ts
export { FileListSummary } from "./FileListSummary";
export type { FileListSummaryProps } from "./FileListSummary";
```

---

### Phase 7: DiffHunk Molecule

Renders a hunk header followed by its lines.

#### `app/frontend/src/components/molecules/DiffHunk/DiffHunk.tsx`

```tsx
import { DiffLineAtom } from "@/components/atoms/DiffLine";
import type { DiffHunk as DiffHunkType } from "@/types/diff";

interface DiffHunkMoleculeProps {
  hunk: DiffHunkType;
}

function DiffHunkMolecule({ hunk }: DiffHunkMoleculeProps) {
  return (
    <div>
      {/* Hunk header */}
      <DiffLineAtom
        line={{
          type: "hunk",
          old_num: null,
          new_num: null,
          content: hunk.header,
        }}
      />

      {/* Hunk lines */}
      {hunk.lines.map((line, i) => (
        <DiffLineAtom key={i} line={line} />
      ))}
    </div>
  );
}

DiffHunkMolecule.displayName = "DiffHunkMolecule";

export { DiffHunkMolecule };
export type { DiffHunkMoleculeProps };
```

#### `app/frontend/src/components/molecules/DiffHunk/index.ts`

```ts
export { DiffHunkMolecule } from "./DiffHunk";
export type { DiffHunkMoleculeProps } from "./DiffHunk";
```

---

### Phase 8: DiffFileHeader Molecule

File header with DiffBadge, file path (directory dimmed, filename bright), DiffStat, and chevron toggle. Sticky positioning. Click toggles collapse.

#### `app/frontend/src/components/molecules/DiffFileHeader/DiffFileHeader.tsx`

```tsx
import { DiffBadge } from "@/components/atoms/DiffBadge";
import { DiffStat } from "@/components/atoms/DiffStat";
import { Icon } from "@/components/atoms/Icon";
import type { DiffFile } from "@/types/diff";

interface DiffFileHeaderProps {
  file: DiffFile;
  expanded: boolean;
  onToggle: () => void;
}

/** Split path into directory (dimmed) and filename (bright). */
function splitPath(path: string): { dir: string; name: string } {
  const lastSlash = path.lastIndexOf("/");
  if (lastSlash === -1) {
    return { dir: "", name: path };
  }
  return {
    dir: path.slice(0, lastSlash + 1),
    name: path.slice(lastSlash + 1),
  };
}

function DiffFileHeader({ file, expanded, onToggle }: DiffFileHeaderProps) {
  const { dir, name } = splitPath(file.path);

  return (
    <button
      type="button"
      onClick={onToggle}
      className="sticky top-0 z-10 flex items-center gap-2 w-full px-4 py-2 bg-[var(--bg-surface)] border border-[var(--border)] rounded-t text-left hover:bg-[var(--bg-surface-hover)] transition-colors cursor-pointer"
    >
      <Icon
        name={expanded ? "chevron-down" : "chevron-right"}
        size="sm"
        className="text-[var(--fg-muted)] shrink-0"
      />

      <DiffBadge changeType={file.change_type} />

      <span className="font-[family-name:var(--font-mono)] text-xs truncate min-w-0">
        <span className="text-[var(--fg-muted)]">{dir}</span>
        <span className="text-[var(--fg-default)] font-medium">{name}</span>
      </span>

      <span className="ml-auto shrink-0">
        <DiffStat additions={file.additions} deletions={file.deletions} />
      </span>
    </button>
  );
}

DiffFileHeader.displayName = "DiffFileHeader";

export { DiffFileHeader };
export type { DiffFileHeaderProps };
```

#### `app/frontend/src/components/molecules/DiffFileHeader/index.ts`

```ts
export { DiffFileHeader } from "./DiffFileHeader";
export type { DiffFileHeaderProps } from "./DiffFileHeader";
```

---

### Phase 9: DiffFile Molecule

Complete file diff: DiffFileHeader + collapsible list of DiffHunks. Starts expanded.

#### `app/frontend/src/components/molecules/DiffFile/DiffFile.tsx`

```tsx
import { useState } from "react";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/atoms/Collapsible";
import { DiffFileHeader } from "@/components/molecules/DiffFileHeader";
import { DiffHunkMolecule } from "@/components/molecules/DiffHunk";
import type { DiffFile as DiffFileType } from "@/types/diff";

interface DiffFileMoleculeProps {
  file: DiffFileType;
}

function DiffFileMolecule({ file }: DiffFileMoleculeProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded}>
      <CollapsibleTrigger asChild>
        <DiffFileHeader
          file={file}
          expanded={expanded}
          onToggle={() => setExpanded(!expanded)}
        />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="border-x border-b border-[var(--border)] rounded-b overflow-hidden">
          {file.hunks.map((hunk, i) => (
            <DiffHunkMolecule key={i} hunk={hunk} />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

DiffFileMolecule.displayName = "DiffFileMolecule";

export { DiffFileMolecule };
export type { DiffFileMoleculeProps };
```

#### `app/frontend/src/components/molecules/DiffFile/index.ts`

```ts
export { DiffFileMolecule } from "./DiffFile";
export type { DiffFileMoleculeProps } from "./DiffFile";
```

---

### Phase 10: FilesChangedPanel Organism

Complete panel composing FileListSummary + scrollable list of DiffFile components.

#### `app/frontend/src/components/organisms/FilesChangedPanel/FilesChangedPanel.tsx`

```tsx
import { FileListSummary } from "@/components/molecules/FileListSummary";
import { DiffFileMolecule } from "@/components/molecules/DiffFile";
import type { DiffData } from "@/types/diff";

interface FilesChangedPanelProps {
  diffData: DiffData;
}

function FilesChangedPanel({ diffData }: FilesChangedPanelProps) {
  if (diffData.files.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-[var(--fg-muted)] text-sm">No files changed</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <FileListSummary
        fileCount={diffData.files.length}
        additions={diffData.total_additions}
        deletions={diffData.total_deletions}
      />
      {diffData.files.map((file) => (
        <DiffFileMolecule key={file.path} file={file} />
      ))}
    </div>
  );
}

FilesChangedPanel.displayName = "FilesChangedPanel";

export { FilesChangedPanel };
export type { FilesChangedPanelProps };
```

#### `app/frontend/src/components/organisms/FilesChangedPanel/index.ts`

```ts
export { FilesChangedPanel } from "./FilesChangedPanel";
export type { FilesChangedPanelProps } from "./FilesChangedPanel";
```

---

### Phase 11: Update App.tsx

Replace the SB-039 placeholder in the content slot with the `FilesChangedPanel` wired to the `useBranchDiff` hook. The `mockDiffStats` lookup for `fileCount` in the tab bar is also updated to use the real mock diff data.

#### `app/frontend/src/App.tsx`

Replace the entire file with:

```tsx
import { useState } from "react";
import { AppShell } from "@/components/organisms";
import { FilesChangedPanel } from "@/components/organisms/FilesChangedPanel";
import { useStackDetail } from "@/hooks/useStackDetail";
import { useBranchDiff } from "@/hooks/useBranchDiff";
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

  const activeBranchId = data?.branches[activeIndex]?.branch.id;
  const { data: diffData } = useBranchDiff(activeBranchId);

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

  // File count from actual diff data
  const fileCount = diffData?.files.length ?? 0;

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
      {diffData ? (
        <FilesChangedPanel diffData={diffData} />
      ) : (
        <div className="flex items-center justify-center h-full">
          <p className="text-[var(--fg-muted)] text-sm">Select a branch to view changes</p>
        </div>
      )}
    </AppShell>
  );
}
```

---

### Phase 12: Barrel Exports

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

export { DiffLineAtom } from "./DiffLine";
export type { DiffLineAtomProps } from "./DiffLine";

export { DiffBadge } from "./DiffBadge";
export type { DiffBadgeProps } from "./DiffBadge";
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

export { FileListSummary } from "./FileListSummary";
export type { FileListSummaryProps } from "./FileListSummary";

export { DiffHunkMolecule } from "./DiffHunk";
export type { DiffHunkMoleculeProps } from "./DiffHunk";

export { DiffFileHeader } from "./DiffFileHeader";
export type { DiffFileHeaderProps } from "./DiffFileHeader";

export { DiffFileMolecule } from "./DiffFile";
export type { DiffFileMoleculeProps } from "./DiffFile";
```

#### Update `app/frontend/src/components/organisms/index.ts`

Replace the entire file with:

```ts
export { StackSidebar } from "./StackSidebar";
export type { StackSidebarProps } from "./StackSidebar";

export { AppShell } from "./AppShell";
export type { AppShellProps } from "./AppShell";

export { FilesChangedPanel } from "./FilesChangedPanel";
export type { FilesChangedPanelProps } from "./FilesChangedPanel";
```

---

### Phase 13: Verification

1. **TypeScript compiles cleanly:**
   ```bash
   cd app/frontend && npx tsc --noEmit
   ```

2. **Dev server starts:**
   ```bash
   cd app/frontend && npm run dev
   ```

3. **Visual verification in browser:**
   - Select branch "3-stack-nav" (index 2, active by default): should show 3 file diffs with realistic code
   - FileListSummary shows "Showing 3 changed files with +89 and -34"
   - Tab badge shows "3" (file count)
   - Each file has a DiffBadge (A green for added, M yellow for modified)
   - File paths show directory in muted, filename in bright
   - DiffStat shows +N/-N for each file
   - Clicking a file header collapses/expands the hunks
   - Hunk headers show @@ lines in italic with accent-muted background
   - Addition lines have green background with + prefix
   - Deletion lines have red background with - prefix
   - Context lines have no background with space prefix
   - Line number gutters show old/new numbers in muted color
   - Select branch "1-scaffold" (index 0): shows 2 files (package.json added, index.css modified)
   - Select branch "4-app-shell" (index 3): shows "No files changed" empty state
   - All text is monospace in the diff viewer
   - Collapsible animation works (collapse-up/collapse-down from Radix)

4. **Build succeeds:**
   ```bash
   cd app/frontend && npm run build
   ```

## File Inventory

| File | Action | Purpose |
|------|--------|---------|
| `src/types/diff.ts` | Create | DiffLine, DiffHunk, DiffFile, DiffData types |
| `src/lib/mock-diff-data.ts` | Create | Mock diff data keyed by branch ID |
| `src/hooks/useBranchDiff.ts` | Create | Hook returning mock diff data for a branch |
| `src/components/atoms/DiffLine/DiffLine.tsx` | Create | Single diff line with gutter + content |
| `src/components/atoms/DiffLine/index.ts` | Create | Barrel |
| `src/components/atoms/DiffBadge/DiffBadge.tsx` | Create | Single-letter file change type badge |
| `src/components/atoms/DiffBadge/index.ts` | Create | Barrel |
| `src/components/atoms/index.ts` | Modify | Add DiffLineAtom, DiffBadge exports |
| `src/components/molecules/FileListSummary/FileListSummary.tsx` | Create | Summary text: N files, +X, -Y |
| `src/components/molecules/FileListSummary/index.ts` | Create | Barrel |
| `src/components/molecules/DiffHunk/DiffHunk.tsx` | Create | Hunk header + DiffLine list |
| `src/components/molecules/DiffHunk/index.ts` | Create | Barrel |
| `src/components/molecules/DiffFileHeader/DiffFileHeader.tsx` | Create | File header: badge + path + stat + chevron |
| `src/components/molecules/DiffFileHeader/index.ts` | Create | Barrel |
| `src/components/molecules/DiffFile/DiffFile.tsx` | Create | Complete file diff with collapsible hunks |
| `src/components/molecules/DiffFile/index.ts` | Create | Barrel |
| `src/components/molecules/index.ts` | Modify | Add FileListSummary, DiffHunk, DiffFileHeader, DiffFile exports |
| `src/components/organisms/FilesChangedPanel/FilesChangedPanel.tsx` | Create | Full panel: summary + file list |
| `src/components/organisms/FilesChangedPanel/index.ts` | Create | Barrel |
| `src/components/organisms/index.ts` | Modify | Add FilesChangedPanel export |
| `src/App.tsx` | Modify | Wire FilesChangedPanel + useBranchDiff into content slot |

## Open Questions

None. All design decisions are settled.
