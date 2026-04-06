---
title: Dashboard Redesign — Navigation, Kanban, Agent Workspaces
status: draft
created: 2026-04-05
epic: EP-016
depends_on: []
---

# Dashboard Redesign

## Goal

Replace the single-stack-only frontend with a three-screen app: (1) a kanban task dashboard, (2) a task detail / agent workspace view with multi-agent pipeline visualization, and (3) the existing stack detail view — all navigated via a persistent sidebar. This makes Stack Bench usable as a task-driven development workbench rather than a code review tool for one stack at a time.

## Context

**Design mockups**: `.claude/design/2026-04-04-dashboard-redesign/` (12 Stitch mockups + DESIGN-DECISIONS.md)
**Primary reference**: `12-final-workspace-switcher.png` (task detail with sidebar workspace cards + pipeline bar)
**Dashboard reference**: `03-dashboard-kanban-v3.png` (kanban board)

### What exists today

**Backend** — ready:
- `Task` model with states: backlog → ready → in_progress → in_review → done | cancelled. Fields: title, description, priority, issue_type, project_id, assignee_id. Table exists. Service + schemas exist. **No router/API yet.**
- `Job` model (queued → running → complete) and `AgentRun` model (pending → running → complete) with phase tracking. Tables exist. **No router/API. No link to Task.**
- Stack/Branch/PR workflow fully working (push/submit/ready/merge all tested).
- Event bus with domain events, SSE streaming via `/events/stream`.

**Frontend** — needs restructuring:
- `AppRouter.tsx` routes `/*` to `<App />` which renders a single-stack view.
- `AppShell` template is tightly coupled to stack detail (takes 40+ props for branch list, diffs, file tree).
- `StackSidebar` only shows branches for one stack. No global nav.
- Extensive Chat* component library (atoms + molecules + ChatRoom organism) from PR #193.
- React Query for data fetching, AuthContext for auth, no global state store.

### Key gap: Task ↔ Agent linking

Task, Job, and AgentRun are separate domains with no foreign key linking them. The dashboard needs to show agent status per task, which requires bridging these models.

**Decision**: Add `task_id` to Job model (nullable FK). A Job is the execution of agent work *for* a task. AgentRuns already link to Job via `job_id`, giving us Task → Job → AgentRun[].

## Plan

### Phase 1: Backend — Task API + Job linking (backend-only, no frontend)

#### Step 1.1: Add task_id to Job model
- **Files**: `app/backend/src/features/jobs/models.py`, new Alembic migration
- **Changes**: Add `task_id = Field(UUID, foreign_key="tasks.id", nullable=True, index=True)` to Job model. Generate migration.
- **Why**: Bridges Task and AgentRun domains. Nullable so existing jobs aren't broken.

#### Step 1.2: Task API router
- **Files**: New `app/backend/src/organisms/api/routers/tasks.py`
- **Changes**: CRUD endpoints following the stacks router pattern:
  - `POST /tasks/` — create task (requires project_id)
  - `GET /tasks/?project_id=` — list tasks by project
  - `GET /tasks/{task_id}` — get task
  - `PATCH /tasks/{task_id}` — update task (title, description, priority, state transition)
  - `DELETE /tasks/{task_id}` — soft-delete
  - `GET /tasks/{task_id}/detail` — task + linked job + agent runs + stack info
- **Why**: Frontend kanban and task detail need CRUD. The `/detail` endpoint is the key one — it returns everything the task detail view needs in one call.

#### Step 1.3: Register router + dependencies
- **Files**: `app/backend/src/organisms/api/app.py`, `app/backend/src/organisms/api/dependencies.py`
- **Changes**: Add `TaskAPIDep`, register tasks router at `/api/v1/tasks`.
- **Why**: Standard wiring following existing patterns.

#### Step 1.4: Job + AgentRun read endpoints
- **Files**: New `app/backend/src/organisms/api/routers/jobs.py`
- **Changes**: Read-only endpoints for jobs and agent runs:
  - `GET /jobs/?task_id=` — list jobs for a task
  - `GET /jobs/{job_id}` — get job with agent runs
- **Why**: Task detail view needs to show the agent pipeline (Job phases from AgentRun records).

### Phase 2: Frontend — Global layout + routing

#### Step 2.1: Route restructuring
- **Files**: `app/frontend/src/AppRouter.tsx`
- **Changes**: Replace the catch-all `/*` → `<App />` route with:
  ```
  /                    → <DashboardPage />
  /workspaces/:taskId  → <WorkspaceDetailPage />
  /stacks/:stackId     → <StackDetailPage />
  ```
  All wrapped in a new `<AppLayout />` that provides the persistent sidebar.
- **Why**: Each screen needs its own route. The sidebar persists across all views.

#### Step 2.2: AppLayout template (new)
- **Files**: New `app/frontend/src/components/templates/AppLayout/AppLayout.tsx`
- **Changes**: New layout template:
  - Left: `<GlobalSidebar />` (260px, always visible)
  - Right: `<Outlet />` (React Router outlet for page content)
- **Why**: The sidebar must persist across page transitions. AppShell stays as-is for the stack detail content area.

#### Step 2.3: GlobalSidebar organism (new)
- **Files**: New `app/frontend/src/components/organisms/GlobalSidebar/GlobalSidebar.tsx`
- **Changes**: Persistent sidebar with three sections:
  - **Nav**: Dashboard link, Workspaces link, Stacks link
  - **Workspaces**: List of active tasks with agent status cards (task name, agent status line, stack link + diff stats). Active workspace highlighted with left accent border.
  - **Stacks**: List of stacks with "N open" badge pills
  - **Bottom**: + New Task button, Settings, user avatar
- **Data**: Fetches `/api/v1/tasks/?project_id=` and `/api/v1/stacks/?project_id=` via React Query.
- **Why**: This replaces StackSidebar as the primary navigation. StackSidebar still renders inside the stack detail view for branch-level navigation.

#### Step 2.4: Hooks for new data
- **Files**: New hooks in `app/frontend/src/hooks/`:
  - `useTaskList.ts` — fetch tasks by project
  - `useTaskDetail.ts` — fetch task + job + agent runs
  - `useProjectList.ts` — fetch user's projects (already partially exists in App.tsx auto-discovery)
- **Why**: Standard React Query hooks following existing patterns (useStackList, useStackDetail).

### Phase 3: Frontend — Dashboard (Kanban)

#### Step 3.1: DashboardPage
- **Files**: New `app/frontend/src/pages/DashboardPage.tsx`
- **Changes**: Page component that renders the kanban board. Fetches tasks via `useTaskList`, groups by state into columns.
- **Why**: Screen 1 from the design.

#### Step 3.2: KanbanBoard molecule (new)
- **Files**: New `app/frontend/src/components/molecules/KanbanBoard/KanbanBoard.tsx`
- **Changes**: Four-column layout: Backlog | In Progress | Review | Done. Each column header shows count badge. Cards are draggable (use `@dnd-kit/core` for drag-and-drop between columns — state transition on drop).
- **Why**: Core dashboard interaction.

#### Step 3.3: TaskCard molecule (new)
- **Files**: New `app/frontend/src/components/molecules/TaskCard/TaskCard.tsx`
- **Changes**: Card component showing:
  - Task ID (monospace muted) + title
  - Agent status line: colored dot + "claude working..." or "idle"
  - Stack link: branch icon + "auth-stack 2/5" in muted text
  - Bottom row: diff stats "+142 -38" in green/red, PR pill "#190" in accent
  - Left border color: blue for active agent, purple for review, none for backlog
  - Click navigates to `/workspaces/:taskId`
- **Why**: The atomic unit of the kanban board. Also used in sidebar workspace cards (compact variant).

### Phase 4: Frontend — Task Detail (Agent Workspace)

#### Step 4.1: WorkspaceDetailPage
- **Files**: New `app/frontend/src/pages/WorkspaceDetailPage.tsx`
- **Changes**: Page component that orchestrates the task detail view:
  - Header: task ID + title + status badge + agent badge
  - Pipeline bar (compact, horizontal)
  - Below: split layout — chat (60%) + changes panel (40%)
  - Bottom: chat input + action bar
- **Data**: `useTaskDetail(taskId)` for task + job + agent runs.
- **Why**: Screen 2 from the design — the key screen.

#### Step 4.2: PipelineBar molecule (new)
- **Files**: New `app/frontend/src/components/molecules/PipelineBar/PipelineBar.tsx`
- **Changes**: Horizontal bar (~40px) showing connected phase nodes:
  - Each node: agent role name + duration/status
  - States: completed (✓ muted), active (● pulsing green), pending (○ dimmed)
  - Connected by thin lines
  - Clicking a node calls `onPhaseClick(phaseIndex)` to scroll chat
  - Supports loops (same role can appear multiple times)
- **Props**: `phases: { role: string; state: 'completed' | 'active' | 'pending'; duration?: string }[]`, `onPhaseClick: (index: number) => void`
- **Why**: Primary pipeline navigation. Design decision: lives in main content, not sidebar.

#### Step 4.3: AgentChat organism (new)
- **Files**: New `app/frontend/src/components/organisms/AgentChat/AgentChat.tsx`
- **Changes**: Continuous chat stream with phase dividers. Renders:
  - User messages (right-aligned, accent-muted bg)
  - Agent messages (left-aligned, surface bg) with colored role dot avatar
  - Tool call blocks (collapsible, monospace, inset bg) — reuse existing ChatToolCallBlock
  - Inline code blocks — reuse existing ChatCodeBlock
  - Phase dividers: thin horizontal line with "── PHASE: BUILDER ──" label
  - Each phase section gets a ref for scroll-to-phase
- **Reuse**: ChatMessageRow, ChatToolCallBlock, ChatCodeBlock, ChatInput atoms/molecules from PR #193.
- **Why**: The chat area is the main interaction surface. Builds on existing chat components.

#### Step 4.4: WorkspaceChangesPanel organism (new)
- **Files**: New `app/frontend/src/components/organisms/WorkspaceChangesPanel/WorkspaceChangesPanel.tsx`
- **Changes**: Right panel with tabs:
  - **Changes** (default): file list with M/A/D badges + diff stats. Click file → inline diff preview below.
  - **History**: checkpoint list (future — stub for now)
  - **Discussion**: comments thread (future — stub for now)
  - Bottom action bar: branch name, "Add to Stack" dropdown, "Create PR" button
- **Why**: Shows the output of agent work. Reuses DiffBadge, DiffStat atoms.

### Phase 5: Stack Detail Integration

#### Step 5.1: StackDetailPage (refactor existing App.tsx)
- **Files**: New `app/frontend/src/pages/StackDetailPage.tsx`, modify `app/frontend/src/App.tsx`
- **Changes**: Extract the `AuthenticatedApp` component from App.tsx into StackDetailPage. It becomes a route-level page that receives `stackId` from URL params instead of local state. The existing AppShell + StackSidebar + FilesChangedPanel continue to work as-is inside this page.
- **Why**: Minimal refactor — the existing stack detail view is already good. Just needs to work within the new routing model.

#### Step 5.2: Sidebar workspace cards in workspace view
- **Files**: `GlobalSidebar.tsx`
- **Changes**: When on `/workspaces/:taskId`, the sidebar's Workspaces section expands to show richer task cards (same TaskCard molecule in compact mode). The active task is highlighted. Clicking another task navigates to that workspace.
- **Why**: Quick workspace switching without going back to dashboard.

## Types

### New frontend types (`app/frontend/src/types/task.ts`)

```typescript
interface Task {
  id: string;
  reference_number: string;
  title: string;
  description: string | null;
  priority: 'critical' | 'high' | 'medium' | 'low' | 'none';
  issue_type: 'story' | 'bug' | 'task' | 'spike' | 'epic';
  state: 'backlog' | 'ready' | 'in_progress' | 'in_review' | 'done' | 'cancelled';
  status_category: 'todo' | 'in_progress' | 'done';
  project_id: string | null;
  assignee_id: string | null;
  created_at: string;
  updated_at: string;
}

interface AgentPhase {
  id: string;
  phase: string;        // "architect", "builder", "validator"
  runner_type: string;
  state: 'pending' | 'running' | 'complete' | 'failed';
  duration_ms: number | null;
  attempt: number;
}

interface TaskDetail {
  task: Task;
  job: Job | null;
  agent_runs: AgentPhase[];
  stack: { id: string; name: string; position: number; total: number } | null;
  diff_stats: { additions: number; deletions: number; files: number } | null;
}
```

## Acceptance Criteria

- [ ] Sidebar navigation persists across all views (dashboard, workspace, stack)
- [ ] Dashboard shows kanban board with tasks grouped by state
- [ ] Task cards show agent status, stack link, and diff stats
- [ ] Clicking a task card navigates to the workspace detail view
- [ ] Workspace detail shows pipeline bar with clickable phase nodes
- [ ] Pipeline bar supports loops (builder → validator → builder)
- [ ] Chat stream shows phase dividers and per-agent colored avatars
- [ ] Clicking pipeline node scrolls chat to that phase
- [ ] Right panel shows changed files with inline diff preview
- [ ] Stack detail view continues to work (branch list, diffs, code, browser tabs)
- [ ] Sidebar shows active workspaces with agent status for quick switching
- [ ] Backend task CRUD API works (create, list, update, delete, detail)
- [ ] Job model links to Task via task_id

## Open Questions

1. **Drag-and-drop library**: `@dnd-kit/core` vs `react-beautiful-dnd` vs simple click-to-move for kanban. DnD kit is more maintained but adds bundle size. Could start with click-to-move and add drag later.

2. **Task ↔ Stack linking**: Tasks link to Jobs, but how does a task know which stack/branch it produced? Options: (a) add `stack_id` + `branch_id` to Task model, (b) derive from Job artifacts, (c) manual linking via "Add to Stack" action. Recommend (a) for simplicity.

3. **Real-time agent updates**: The pipeline bar needs live updates as agents progress. The event bus + SSE infrastructure exists (`/events/stream`). Need to subscribe to `agent_run.*` events and update React Query cache. The `useEventSource` hook already exists.

4. **Chat persistence**: Where do agent workspace chat messages live? Options: (a) reuse Conversation model (already has messages + SSE streaming), (b) new model. Recommend (a) — add `task_id` to Conversation model.

5. **Project context**: The frontend currently discovers projects via a hacky auto-select. Need a proper project context (URL param, localStorage, or user preference). Recommend localStorage + URL override.

## Implementation Order

Ship incrementally — each phase is independently deployable:

1. **Phase 1** (backend) — Task API + Job linking. Pure backend, no frontend changes.
2. **Phase 2** (frontend shell) — Routing + AppLayout + GlobalSidebar. Dashboard shows empty state, workspace/stack routes work.
3. **Phase 3** (dashboard) — Kanban board with real data. First usable feature.
4. **Phase 4** (workspace detail) — Agent workspace view. The big one.
5. **Phase 5** (integration) — Wire stack detail into new nav, workspace switching.

Each phase is 1-2 days of focused work. Total: ~1-2 weeks.
