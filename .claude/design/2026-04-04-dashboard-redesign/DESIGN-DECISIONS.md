# Stack Bench Dashboard Redesign — Design Decisions

Date: 2026-04-04
Tool: Google Stitch 2.0
Reference mockups: `01-*.png` through `11-*.png` in this directory

## Final Design Direction

**Primary reference: `12-final-workspace-switcher.png`** — task detail with sidebar workspace switching + top pipeline bar
**Fallback reference: `11-final-task-detail.png`** — similar layout, closer to our existing design tokens
**Dashboard: `03-dashboard-kanban-v3.png`** — the kanban task board

### Implementation notes (divergences from mockups to fix):
- Remove "PRECISION ENGINE" branding — use "Stack Bench" only
- Remove "Deploy" button from header — premature for MVP
- Move "Commit" into right panel action bar (alongside Add to Stack / Create PR)
- Drop "ACTIVE TASKS" section label — workspace items go directly under Workspaces nav
- Use our existing design tokens, not Stitch's slightly diverged colors

## Research Sources

Patterns drawn from: Graphite (stacked PR inbox), Conductor (agent workspaces + checkpoints),
Nimbalyst (kanban sessions + visual editing), Linear (sidebar hierarchy + keyboard nav),
GitButler (branch lanes), Cursor (multi-session agents), Devin (parallel agent workspaces).

## Navigation Model

Sidebar-driven hierarchy (Linear-style):
- **Dashboard** — kanban overview of all tasks
- **Workspaces** — active agent sessions (Conductor-style)
  - Clicking a workspace opens the task detail view
- **Stacks** — PR groupings (Graphite-style)
  - Clicking a stack opens the current stack detail view (branch list + diffs)

## Three Core Screens

### Screen 1: Dashboard (Kanban)
- Kanban columns: Backlog | In Progress | Review | Done
- Task cards show: ID, title, agent status, stack link, diff stats, PR number
- Active agent cards get a blue left border
- Sidebar shows: Dashboard (active), Workspaces, Stacks sections
- `+ New Task` button at sidebar bottom

### Screen 2: Task Detail (Agent Workspace) — THE KEY SCREEN
- **Sidebar**: Active workspace switcher — each workspace shows task name, agent status
  (one line), stack position + diff stats. Enough to glance at all active work without
  leaving the current task. NOT used for pipeline or task metadata.
- **Pipeline bar** at top of chat area (horizontal, compact ~40px) — the primary pipeline nav
  - Shows all phases: Architect → Builder → Validator → Builder → Validator...
  - Supports loops (builder → validator → builder)
  - Clicking a node scrolls chat to that phase
  - Completed nodes muted with checkmark, active node bright + pulsing, pending dimmed
- **Chat area**: Continuous conversation stream with thin phase dividers ("PHASE: BUILDER")
  - Each agent has a colored avatar (blue=architect, green=builder, purple=validator)
  - Inline code blocks showing what agents wrote
  - Tool call blocks (Read/Edit) with expand chevrons
- **Right panel**: Changes tab with file list + inline diff preview when file selected
  - Also: History, Discussion tabs
- **Bottom actions**: "Add to Stack" dropdown + "Create PR" button
- **Chat input**: "Ask the agent..." with attach files + reference task options

### Screen 3: Stack Detail (Existing, refined)
- The current app view: branch connector list in sidebar, diff viewer in main content
- Tabs: Stack Diffs | Code | Browser
- Already implemented, needs minor refinements

## Multi-Agent Flow (Key Design Decision)

Tasks use sequential agent teams: orchestrator → architect → builder → validator.
Builder and validator can loop (builder → validator → builder when issues found).

Representation:
- **Pipeline bar** (horizontal, top of chat) — compact navigation, shows all phases
- **Sidebar pipeline** (vertical) — detailed view with times per phase
- **Chat stream** — single continuous thread with thin phase dividers, no collapsed blocks
- Clicking a pipeline node (sidebar or top bar) scrolls to that phase in chat

## Design Language

Follows existing Stack Bench tokens (GitHub-dark inspired):
- Canvas: #0d1117, Surface: #161b22, Borders: #30363d
- Text: #e6edf3 (default), #7d8590 (muted), #484f58 (subtle)
- Accent: #58a6ff, Green: #3fb950, Red: #f85149, Purple: #bc8cff, Yellow: #d29922
- Font: IBM Plex Sans (UI), IBM Plex Mono (code)
- No shadows, border-driven, 6px rounded corners

Note: Stitch mockups diverged slightly from our tokens in later iterations
(variants 09/10). Implementation should use our existing design system, not
the Stitch-generated colors.
