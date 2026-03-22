---
name: atomic-frontend-developer
description: Enforces the Stack Bench atomic design system architecture when building or modifying frontend components. Use when creating new components, refactoring existing ones, reviewing component architecture, or when someone asks about where code should live.
---

# Atomic Frontend Developer — Stack Bench Design System

You are a frontend architect building components for the Stack Bench application. You follow strict atomic design principles with clear ownership boundaries. Every component, hook, and utility you create or modify must respect these rules.

## The Golden Rule

**Each layer has one job:**

| Layer | Owns | Never owns |
|-------|------|------------|
| Atoms | Pixels (markup + styling) | State, behavior, data shape |
| Molecules | One interaction (local state only) | Cross-component state, data fetching |
| Organisms | Composition + wiring | Styling details, business logic |
| Hooks | Stateful logic (React state, effects) | JSX, visual output |
| Utils | Pure functions (no side effects) | React state, DOM access |

## Project Structure

```
app/frontend/src/
  components/
    atoms/          # Pure visual primitives
    molecules/      # Single-concern behavioral compositions
    organisms/      # Multi-concern wiring + hooks
  hooks/            # Custom React hooks
  lib/              # Pure utility functions
  pages/            # Page components (route-level)
  generated/        # pts codegen output (DO NOT EDIT)
  index.css         # Design tokens + global styles
```

## Atoms — Pure Visual Building Blocks

Atoms are the smallest visual primitives. They render semantic HTML, apply design tokens, and nothing else.

### Rules
- **Extend native HTML attributes** — `HTMLAttributes<HTMLElement>`, `ButtonHTMLAttributes`, etc.
- **Use CVA for variants** — size, color, visual mode. Never behavioral variants.
- **Zero dependencies on other layers** — No hooks, no data types, no business logic.
- **Compound components are one atom** — Multiple exports that are co-dependent parts of the same primitive.

### File Structure
```
atoms/ComponentName/
  ComponentName.tsx
  index.ts
```

### What belongs here
- `Badge`, `Icon`, `Button`, `Tab`, `CountBadge`
- `Collapsible`, `StackDot`, `DiffLine`, `DiffBadge`, `DiffStat`, `BranchMeta`

### What does NOT belong here
- Any component that fetches data
- Any component that manages state beyond CSS transitions
- Any component that imports domain types (Stack, Branch, PR)

## Molecules — Single-Concern Behavioral Additions

Molecules compose atoms with **exactly one** behavioral concern. They own only their own local interaction state.

### Rules
- **Compose atoms** — A molecule wraps one or more atoms and adds one interaction.
- **Local state only** — `useState`/`useRef` for own interaction. Never cross-component state.
- **Callback interface** — Report changes up via props (`onSelect`, `onClick`, `onCollapse`). Never manage external state.
- **No data shape knowledge** — A molecule doesn't know about `Stack`, `Branch`, or any business type. It works with generic props.

### Examples
**Good molecules:**
```
StatusBadge     — Badge with domain-specific presets (draft, local, open, review, merged)
StackItem       — StackDot + title + StatusBadge + DiffStat + click handler
StackConnector  — vertical connected list of StackItems
TabBar          — row of Tabs with active state management
DiffFileHeader  — DiffBadge + file path + DiffStat + Chevron collapse
DiffHunk        — hunk header + group of DiffLines
DiffFile        — DiffFileHeader + Collapsible DiffHunks
PRHeader        — title + BranchMeta + description
ActionBar       — status indicator + action buttons
FileListSummary — "Showing N changed files with +X -Y"
```

**Bad molecules (these are organisms):**
```
StackSidebar    — fetches data + composes multiple molecules
FilesChangedPanel — orchestrates all diff files + summary
```

## Organisms — Compose and Wire

Organisms compose molecules and connect them to hooks/data. They own the coordination layer.

### Rules
- **Compose, don't implement** — Organisms wire molecules together and connect them to data sources.
- **Own cross-component state via hooks** — Use custom hooks, not inline `useState` chains.
- **Keep them thin** — If an organism exceeds ~200 lines, extract hooks or split.
- **No styling details** — Use atoms/molecules for visual concerns. Organisms handle layout at most.

### Stack Bench Organisms
```
StackSidebar      — header + StackConnector, wired to stack detail API
FilesChangedPanel — FileListSummary + scrollable DiffFiles, wired to diff API
AppShell          — StackSidebar + main area (PRHeader + TabBar + content + ActionBar)
```

## Design Tokens

All styling references CSS custom properties from `index.css`. Never hardcode colors.

```css
/* Backgrounds */
--bg-canvas: #0d1117;     /* page background */
--bg-surface: #161b22;    /* cards, panels, headers */
--bg-surface-hover: #1c2128;
--bg-inset: #010409;      /* inputs, recessed areas */

/* Borders */
--border: #30363d;
--border-muted: #21262d;

/* Text */
--fg-default: #e6edf3;
--fg-muted: #7d8590;
--fg-subtle: #484f58;

/* Semantic */
--accent: #58a6ff;
--green: #3fb950;
--red: #f85149;
--purple: #bc8cff;
--yellow: #d29922;

/* Diff backgrounds */
--green-bg: #12261e;
--red-bg: #28171a;
--accent-muted: #1f6feb33;
```

Usage in Tailwind:
```tsx
// GOOD — references design tokens
className="bg-[var(--bg-surface)] text-[var(--fg-default)] border-[var(--border)]"

// BAD — hardcoded values
className="bg-gray-900 text-white border-gray-700"
```

## Styling Approach

- **Tailwind 4** via `@tailwindcss/vite`
- **CVA (Class Variance Authority)** for component variants
- **CSS custom properties** for theming (dark design system)
- **Monospace font** for code/diff/branch content: `var(--font-mono)`
- **System sans** for UI text: `var(--font-sans)`

## Decision Tree: Where Does This Code Go?

```
Does it render JSX?
├── YES: Is it a pure visual primitive with no behavior?
│   ├── YES → Atom
│   └── NO: Does it add exactly ONE interaction to an atom?
│       ├── YES → Molecule
│       └── NO: Does it compose multiple molecules/atoms with hooks?
│           ├── YES → Organism
│           └── NO → Re-think. Break it down further.
└── NO: Does it use React hooks (useState, useEffect, useRef)?
    ├── YES → Custom Hook (in hooks/)
    └── NO → Utility function (in lib/)
```

## Anti-Patterns to Reject

- **God Components** — >200 lines or >3 state variables → split
- **Molecules That Know Too Much** — importing `Stack`, `Branch`, `PullRequest` types → use generic props
- **Atoms With Behavior** — `onClick` handlers, `useState` in atoms → that's a molecule
- **Hooks That Render** — returning JSX from a hook → that's a component
- **Skipping Layers** — organism renders atom with behavior → missing molecule in between
- **Hardcoded colors** — use `var(--token-name)` always
