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
