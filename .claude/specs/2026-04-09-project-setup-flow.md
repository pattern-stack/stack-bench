---
title: Project Setup Flow — Switcher, Creation, Auto-Workspace
date: 2026-04-09
status: in-progress
branch: null
depends_on: []
adrs: []
---

# Project Setup Flow — Switcher, Creation, Auto-Workspace

## Goal

Add a complete project management flow to the frontend so users can create projects (especially pointing at local git repos), switch between them, and have workspaces auto-created. Today the sidebar hardcodes `projects[0]?.id`, there is no creation UI, and projects must be inserted via SQL. This work unblocks the LocalGitAdapter by giving users a way to create projects with `local_path`.

## Domain Model

No new backend models needed. The existing entities and their patterns:

| Entity | Pattern | Role in this feature |
|--------|---------|---------------------|
| `Project` | EventPattern (setup -> active -> archived) | Created by the new form, listed in the switcher |
| `Workspace` | EventPattern (created -> provisioning -> ready -> ...) | Auto-created alongside the project |
| `User` | ActorPattern | `owner_id` for project, available via `useAuth().user.id` |

Key relationships:
- Project has `owner_id` FK to User
- Workspace has `project_id` FK to Project
- A local project needs both a Project (`local_path`, `github_repo`) and a Workspace (`local_path`, `repo_url`, `provider`)

## Current State Analysis

### Backend — ready, with one required change

The `POST /api/v1/projects/` endpoint works. The `ProjectCreate` schema requires `github_repo` as a validated GitHub URL. For local-only projects, we need to either:
- **(A) Make `github_repo` optional** in the backend schema and model (breaking change to the DB constraint)
- **(B) Derive `github_repo` from the git remote** in a new molecule-layer endpoint that accepts `local_path` and reads the remote URL
- **(C) Create a new composite endpoint** (`POST /api/v1/projects/setup`) that accepts `name` + `local_path`, reads the git remote origin, and creates both project and workspace in one transaction

**Decision: Option C** — a new molecule-layer workflow + organism endpoint. This keeps the existing `ProjectCreate` schema untouched, adds the composite logic in the correct layer (molecule), and gives the frontend a single API call for the common case. The existing raw CRUD endpoints remain for GitHub-based projects.

### Frontend — needs project context + UI

Three places hardcode `projects[0]?.id`:
1. `GlobalSidebar.tsx` line 92
2. `DashboardPage.tsx` line 63
3. `StacksListPage.tsx` line 41

These all need to read from a shared "active project" context instead.

### Generated schemas — codegen gap

The generated `ProjectCreateSchema` in `app/frontend/src/generated/schemas/project.ts` is missing `owner_id`, `github_repo`, and `local_path`. However, since we are adding a new composite endpoint (`/projects/setup`), we will create a manual TypeScript type for that endpoint's payload rather than fighting the codegen. The generated hooks remain useful for listing/getting projects.

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Backend: project setup workflow + endpoint | -- |
| 2 | Frontend: active project context | -- |
| 3 | Frontend: project switcher in sidebar | Phase 2 |
| 4 | Frontend: "Add Project" dialog | Phase 2 |
| 5 | Frontend: empty state + zero-project flow | Phases 3, 4 |

## Phase Details

### Phase 1: Backend — Project Setup Workflow + Endpoint

Create a molecule-layer workflow that composes ProjectService and WorkspaceService to handle local project creation in one transaction.

**Pre-requisite: Add `"local"` to workspace provider choices**

The workspace model's `provider` field has `choices=["github", "gitlab", "bitbucket"]` and the schema uses `Literal["github", "gitlab", "bitbucket"]`. There is no DB check constraint (verified — only PK and FK constraints on the workspaces table), so no migration is needed. Changes:
- `app/backend/src/features/workspaces/models.py` line 36: add `"local"` to choices list
- `app/backend/src/features/workspaces/schemas/input.py` line 12: add `"local"` to Literal in `WorkspaceCreate`
- `app/backend/src/features/workspaces/schemas/input.py` line 25: add `"local"` to Literal in `WorkspaceUpdate`

**New file: `app/backend/src/molecules/workflows/project_setup.py`**

Reference: `OnboardingWorkflow` at `molecules/workflows/onboarding.py` lines 209-265 for the identical pattern (create project + workspace in one transaction).

```
ProjectSetupWorkflow
  - create_local_project(db, user_id, name, local_path, description?) -> ProjectSetupResult
    1. Validate local_path exists and has a .git directory
    2. Read git remote origin URL:
       a. Run `git -C {local_path} remote get-url origin`
       b. If remote exists: use it as github_repo and repo_url; set provider="github" (or detect from URL)
       c. If no remote (command fails): use synthetic `https://github.com/local/{folder_name}` for github_repo;
          set provider="local"; set repo_url to the same synthetic URL
    3. Read default branch: `git -C {local_path} symbolic-ref --short HEAD` (fallback: "main")
    4. Create Project via ProjectService (owner_id=user_id, github_repo from step 2)
    5. Create Workspace with local_path, provider from step 2, repo_url from step 2
    6. Transition project to "active"
    7. Return {project_id, workspace_id, project_name}
```

**New file: `app/backend/src/organisms/api/routers/project_setup.py`**

```
Router prefix: "/projects" (same as existing projects router — the route is /setup under it)
Alternatively: separate router with prefix "/projects/setup" — either works since "setup" is not a valid UUID

POST /api/v1/projects/setup
  Body: { name: str, local_path: str, description?: str }
  Auth: CurrentUser (injects owner_id server-side)
  Response: { project_id, workspace_id, project_name }
```

This endpoint uses `CurrentUser` dependency so the frontend never needs to send `owner_id` — it is derived from the JWT token.

**Files to create:**
- `app/backend/src/molecules/workflows/project_setup.py` — workflow
- `app/backend/src/organisms/api/routers/project_setup.py` — router

**Files to modify:**
- `app/backend/src/features/workspaces/models.py` — add `"local"` to provider choices
- `app/backend/src/features/workspaces/schemas/input.py` — add `"local"` to provider Literal types
- `app/backend/src/organisms/api/app.py` — register new router

### Phase 2: Frontend — Active Project Context

Create a React context that tracks which project is active and persists the selection to `localStorage`. Every component that needs a project ID reads from this context instead of hardcoding `projects[0]`.

**New file: `app/frontend/src/contexts/ProjectContext.tsx`**

```tsx
ProjectProvider
  - Wraps AppLayout inside AppRouter.tsx (inside AuthGate, where QueryClientProvider + auth are available)
  - Fetches project list via useProjectList()
  - Reads saved project ID from localStorage
  - If saved ID not found in list, falls back to projects[0]
  - Exposes: { activeProject, setActiveProject, projects, isLoading }

useActiveProject() hook
  - Returns { activeProject, setActiveProject, projects, isLoading }
  - Throws if used outside provider
```

**Files to create:**
- `app/frontend/src/contexts/ProjectContext.tsx` — context + provider + hook

**Files to modify:**
- `app/frontend/src/main.tsx` or `app/frontend/src/AppRouter.tsx` — wrap with `ProjectProvider` (inside QueryClientProvider, since it needs react-query)
- `app/frontend/src/components/organisms/GlobalSidebar/GlobalSidebar.tsx` — replace `projects[0]?.id` with `useActiveProject().activeProject?.id`
- `app/frontend/src/pages/DashboardPage.tsx` — same replacement
- `app/frontend/src/pages/StacksListPage.tsx` — same replacement

The context should live inside the authenticated route tree (after `AuthGate`) since it needs the auth token for API calls. Placement: wrap `AppLayout` inside `AppRouter.tsx`.

### Phase 3: Frontend — Project Switcher in Sidebar

Add a dropdown/popover at the top of `GlobalSidebar` that shows all projects and lets the user switch between them.

**Design:**
- Replace the static "Stack Bench" header with a clickable project selector
- Shows current project name with a chevron-down icon
- On click, opens a dropdown listing all projects with their names
- Active project gets a check mark or highlight
- Bottom of dropdown: "Add Project" button that opens the creation dialog
- Fits within 260px sidebar width

**Component location** (atomic design): This is a molecule — it composes atoms (Icon, Button) and reads from context. However, since it is tightly coupled to the sidebar organism, it can live as an internal component within the `GlobalSidebar` directory.

**Files to create:**
- `app/frontend/src/components/organisms/GlobalSidebar/ProjectSwitcher.tsx` — the dropdown component

**Files to modify:**
- `app/frontend/src/components/organisms/GlobalSidebar/GlobalSidebar.tsx` — replace header section with `ProjectSwitcher`

**Icon additions:** The Icon atom already has `chevron-down`, `check`, `plus`, and `folder` — all sufficient for the switcher.

### Phase 4: Frontend — "Add Project" Dialog

A modal dialog for creating a new project. Since no modal/dialog infrastructure exists in the codebase, we need to create a reusable dialog atom first.

**Reusable Dialog atom:**

**New file: `app/frontend/src/components/atoms/Dialog/Dialog.tsx`**

- Renders a portal-based modal overlay
- Handles ESC to close, click-outside to close
- Accepts `isOpen`, `onClose`, `title`, `children`
- Uses CSS variables for theming
- Focus trap for accessibility

**New file: `app/frontend/src/components/atoms/Dialog/index.ts`**

- Export Dialog

**Update: `app/frontend/src/components/atoms/index.ts`**

- Add Dialog export

**Add Project Form:**

**New file: `app/frontend/src/components/organisms/AddProjectDialog/AddProjectDialog.tsx`**

Form fields:
1. **Name** (text input, required) — auto-derived from folder name if local_path is entered first
2. **Local Path** (text input, required) — the main use case; placeholder: `/Users/you/Projects/my-repo`
3. **Description** (text area, optional)

Behavior:
- On submit, calls `POST /api/v1/projects/setup` with `{ name, local_path, description }`
- Shows validation errors inline (path doesn't exist, name taken, etc.)
- On success: sets the new project as active via `setActiveProject()`, closes dialog
- Loading state on submit button

**New file: `app/frontend/src/components/organisms/AddProjectDialog/index.ts`**

**New file: `app/frontend/src/hooks/useCreateLocalProject.ts`**

Custom hook wrapping the mutation for `POST /api/v1/projects/setup`:
```tsx
function useCreateLocalProject() {
  // useMutation calling apiClient.post('/api/v1/projects/setup', data)
  // On success: invalidate project list queries
}
```

**Files to modify:**
- `app/frontend/src/components/organisms/GlobalSidebar/GlobalSidebar.tsx` — add dialog trigger state and render `AddProjectDialog`

### Phase 5: Frontend — Empty State + Zero-Project Flow

When a user has zero projects (fresh account, post-onboarding), the app needs to guide them to create one.

**DashboardPage empty state:**
- If `activeProject` is null and projects list is empty, show a centered empty state with:
  - "No projects yet" heading
  - "Create a project to start working with your code" subtitle
  - "Add Project" button that opens the same `AddProjectDialog`

**GlobalSidebar with no project:**
- The project switcher shows "No project selected" or "Add a project"
- Active tasks and stacks sections are hidden (they require a projectId)

**Files to modify:**
- `app/frontend/src/pages/DashboardPage.tsx` — add empty state before kanban
- `app/frontend/src/components/organisms/GlobalSidebar/GlobalSidebar.tsx` — conditional rendering when no active project

## File Tree

```
# NEW FILES
app/backend/src/molecules/workflows/project_setup.py     # Workflow: create project + workspace from local path
app/backend/src/organisms/api/routers/project_setup.py    # Router: POST /api/v1/projects/setup

app/frontend/src/contexts/ProjectContext.tsx               # Active project context + provider + hook
app/frontend/src/hooks/useCreateLocalProject.ts            # Mutation hook for /projects/setup
app/frontend/src/components/atoms/Dialog/Dialog.tsx        # Reusable modal dialog atom
app/frontend/src/components/atoms/Dialog/index.ts          # Dialog barrel export
app/frontend/src/components/organisms/GlobalSidebar/ProjectSwitcher.tsx  # Project dropdown in sidebar
app/frontend/src/components/organisms/AddProjectDialog/AddProjectDialog.tsx  # Project creation form dialog
app/frontend/src/components/organisms/AddProjectDialog/index.ts             # Barrel export

# MODIFIED FILES
app/backend/src/organisms/api/app.py                      # Register project_setup router
app/frontend/src/AppRouter.tsx                             # Wrap AppLayout with ProjectProvider
app/frontend/src/components/atoms/index.ts                 # Export Dialog
app/frontend/src/components/organisms/GlobalSidebar/GlobalSidebar.tsx  # Use ProjectContext, add switcher + dialog
app/frontend/src/pages/DashboardPage.tsx                   # Use ProjectContext, add empty state
app/frontend/src/pages/StacksListPage.tsx                  # Use ProjectContext
```

## Implementation Order

1. **Phase 1** (backend) — standalone, no dependencies
2. **Phase 2** (project context) — standalone frontend, no dependencies
3. **Phase 3** (project switcher) — needs Phase 2 context
4. **Phase 4** (add project dialog) — needs Phase 2 context + Phase 1 endpoint
5. **Phase 5** (empty states) — needs Phases 3 + 4

Phases 1 and 2 can be built in parallel.

## Key Design Decisions

### Why a new composite endpoint instead of fixing `github_repo` required constraint

The `github_repo` field is `required=True` on both the model and schema. Making it optional would require a migration, updating the output schema, and handling nullability across the codebase. A composite endpoint avoids this entirely — it reads the git remote to populate `github_repo` automatically. If there is no remote, it constructs a synthetic `https://github.com/local/{repo-name}` URL as a placeholder. This is pragmatic: every local git repo that was cloned from GitHub already has the correct remote URL.

### Why localStorage for active project persistence (not URL params)

The active project is a session-level concern, not a page-level concern. It persists across navigation between dashboard, stacks, and workspaces. URL params would either clutter every route (`/stacks?project=abc`) or require complex route nesting (`/projects/:id/stacks`). localStorage + React context is simpler, matches how the auth token is already persisted, and survives page refreshes.

### Why a Dialog atom instead of using a library

The codebase has zero dependencies on component libraries (no Radix, no shadcn, no Headless UI). Every atom is hand-built with CSS variables. Adding a modal library for one dialog would be inconsistent. A custom Dialog atom (~60 lines) with portal, ESC handling, and overlay is trivial and follows the existing pattern.

### Why the owner_id is injected server-side

The current project create endpoint requires `owner_id` in the request body, which means the frontend must send the user's UUID. The new `/projects/setup` endpoint uses the `CurrentUser` FastAPI dependency to inject `owner_id` from the JWT token. This is more secure (users cannot create projects owned by other users) and simpler for the frontend.

### Why workspace auto-creation matters

The `StackAPI._get_reader_for_branch()` method resolves the git reader by checking `workspace.local_path`. Without a workspace, there is no way for the stack system to serve diffs or files for a project. Auto-creating a workspace when the project is created ensures the git pipeline works immediately.

## Testing Strategy

### Backend Tests

**File: `app/backend/__tests__/test_project_setup.py`**

- **Unit tests for `ProjectSetupWorkflow`:**
  - Happy path: valid local_path with git remote -> creates project + workspace + transitions to active
  - Local path with no remote -> uses synthetic github_repo URL
  - Local path that doesn't exist -> raises validation error
  - Local path that isn't a git repo -> raises validation error
  - Duplicate project name -> raises error
  - Marker: `@pytest.mark.asyncio`

- **API integration tests:**
  - `POST /api/v1/projects/setup` with valid payload -> 201, returns project_id + workspace_id
  - Missing auth token -> 401
  - Invalid local_path -> 422 validation error
  - Marker: `@pytest.mark.asyncio`

### Frontend Tests

No formal test framework appears to be set up for the frontend (no `vitest.config.ts` or `jest.config.ts` found). Manual testing plan:

1. **Zero-project state:** New user sees empty state on dashboard, can create project
2. **Create project:** Fill in name + local path, submit -> project appears in switcher, auto-selected
3. **Project switching:** Create two projects, switch between them -> dashboard/stacks update
4. **Persistence:** Switch to project B, refresh page -> project B still selected
5. **Validation:** Submit form with empty name or invalid path -> inline errors shown
6. **Dialog UX:** ESC closes dialog, clicking overlay closes dialog, focus trapped inside

## Open Questions

1. **Should we also add a "GitHub repo" project creation path in this same dialog?** The onboarding flow already handles GitHub projects, but that flow is only for first-time setup. A second tab or mode in the dialog for "Import from GitHub" would be useful but could be deferred to a follow-up.

2. **Should the project switcher show project state (setup/active/archived)?** Probably yes for archived projects (greyed out), but setup projects should auto-transition to active via the new endpoint, so they should rarely appear.

3. **Should we add a "Settings" page for the active project?** This would show project details, workspace status, allow editing name/description, and eventually manage GitHub app integration. Not in scope for this spec but a natural follow-up.
