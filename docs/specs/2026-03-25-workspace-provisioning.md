---
title: "EP-011: Workspace Provisioning — Cloud Run + GCS Lifecycle"
date: 2026-03-25
status: draft
branch:
depends_on: [docs/specs/2026-03-19-project-workspace-domain.md]
adrs: []
epic: EP-011
issues: ["#165 (SB-068)", "#166 (SB-069)", "#167 (SB-070)"]
---

# Workspace Provisioning

## Goal

Evolve the existing Workspace feature into a provisionable cloud environment. Today a Workspace is a `BasePattern` linking a project to a git repo. This epic adds cloud lifecycle management: provision Cloud Run services, create GCS buckets, manage workspace containers where agents run code against real repositories.

The integration point with agentic-patterns: Stack Bench's WorkspaceManager deploys agencies/rosters into workspaces via `sandbox-run --agency` or `sandbox-run --roster`.

## Domain Model

### Current State

```
Workspace (BasePattern — no state machine)
  project_id, name, repo_url, provider, default_branch, local_path, metadata_, is_active
```

### Target State

```
Workspace (EventPattern — with state machine + cloud provisioning)
  # Existing fields (unchanged)
  project_id, name, repo_url, provider, default_branch, local_path, metadata_, is_active

  # New cloud provisioning fields
  resource_profile: str = "standard"       # light | standard | heavy
  region: str = "northamerica-northeast2"
  cloud_run_service: str | None            # Cloud Run service name
  cloud_run_url: str | None                # HTTPS endpoint when ready
  gcs_bucket: str | None                   # workspace storage bucket name
  config: dict = {}                        # env vars, branch overrides, agent config

  # State machine
  states: created → provisioning → ready → stopped → destroying → destroyed
```

**Key decision:** Evolve the existing model rather than creating a new entity. A Workspace IS a repo + its cloud environment. The `repo_url` tells you what code lives there; the `cloud_run_*` fields tell you where it runs. A workspace without cloud fields is simply "not yet provisioned."

### Migration Strategy

The model upgrade from `BasePattern` → `EventPattern` adds a `state` column and `reference_number`. New cloud fields are all nullable. Existing workspaces get `state = "created"` (unprompted). The `is_active` field remains for backwards compatibility but `state` becomes the primary lifecycle indicator.

## Implementation Phases

| Phase | Issue | What | Depends On |
|-------|-------|------|------------|
| 1 | SB-068 (#165) | Workspace model evolution + service | — |
| 2 | SB-069 (#166) | WorkspaceManager molecule + container image | Phase 1 |
| 3 | SB-070 (#167) | Workspace REST API | Phase 2 |

## Phase Details

### Phase 1: Workspace model evolution (SB-068)

**Upgrade Workspace from BasePattern to EventPattern with cloud fields.**

#### Model Changes

```python
# app/backend/src/features/workspaces/models.py

class Workspace(EventPattern):  # was BasePattern
    __tablename__ = "workspaces"

    class Pattern:
        entity = "workspace"
        reference_prefix = "WKSP"
        initial_state = "created"
        states = {
            "created": ["provisioning"],
            "provisioning": ["ready", "created"],    # can fail back to created
            "ready": ["stopped", "destroying"],
            "stopped": ["provisioning", "destroying"],  # can re-provision
            "destroying": ["destroyed"],
            "destroyed": [],
        }
        state_phases = {
            "created": StatePhase.INITIAL,
            "provisioning": StatePhase.ACTIVE,
            "ready": StatePhase.ACTIVE,
            "stopped": StatePhase.ACTIVE,
            "destroying": StatePhase.ACTIVE,
            "destroyed": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    # Existing fields
    project_id = Field(UUID, foreign_key="projects.id", required=True, index=True)
    name = Field(str, required=True, max_length=200)
    repo_url = Field(str, required=True, max_length=500)
    provider = Field(str, required=True, max_length=20, choices=["github", "gitlab", "bitbucket"])
    default_branch = Field(str, required=True, max_length=200, default="main")
    local_path = Field(str, nullable=True, max_length=500)
    metadata_ = Field(dict, default=dict)
    is_active = Field(bool, default=True, index=True)

    # New cloud provisioning fields
    resource_profile = Field(str, max_length=20, default="standard")
    region = Field(str, max_length=50, default="northamerica-northeast2")
    cloud_run_service = Field(str, nullable=True, max_length=200)
    cloud_run_url = Field(str, nullable=True, max_length=500)
    gcs_bucket = Field(str, nullable=True, max_length=200)
    config = Field(dict, default=dict)
```

#### Service Changes

Extend `WorkspaceService` with:
- `get_by_project(project_id)` — single workspace for a project (convenience)
- `list_ready(project_id)` — only workspaces in `ready` state
- State transition methods inherit from EventPattern's `transition_state()`

#### Schema Changes

**CreateInput:** add `resource_profile`, `region`, `config` (all optional with defaults)
**UpdateInput:** add `resource_profile`, `config`
**Response:** add `cloud_run_url`, `gcs_bucket`, `resource_profile`, `region`, `state`, `config`
**Summary:** lightweight: `id`, `name`, `state`, `resource_profile`, `cloud_run_url`

#### Migration

Alembic migration that:
1. Adds `state`, `reference_number` columns (EventPattern requirements)
2. Adds `resource_profile`, `region`, `cloud_run_service`, `cloud_run_url`, `gcs_bucket`, `config` columns
3. Sets `state = 'created'` for existing rows
4. Sets `resource_profile = 'standard'`, `region = 'northamerica-northeast2'` for existing rows
5. Backfills `reference_number` for existing rows (e.g., `WKSP-001`, `WKSP-002`, ...) — verify whether pattern-stack EventPattern requires NOT NULL or allows nullable

**Note:** This is the first use of `transition_state()` in the stack-bench codebase. Verify the pattern-stack EventPattern API before building.

**Files:**
- Edit: `app/backend/src/features/workspaces/models.py`
- Edit: `app/backend/src/features/workspaces/service.py`
- Edit: `app/backend/src/features/workspaces/schemas/input.py`
- Edit: `app/backend/src/features/workspaces/schemas/output.py`
- New: `app/backend/alembic/versions/xxx_add_workspace_provisioning.py`
- Edit: `app/backend/__tests__/features/test_workspaces.py`

---

### Phase 2: WorkspaceManager molecule (SB-069)

**Molecule-layer service that manages the cloud lifecycle.**

#### WorkspaceManager

Composes `WorkspaceService` + GCP API calls. Lives in `app/backend/src/molecules/services/workspace_manager.py`.

**Provision flow:**
1. Transition workspace to `provisioning`
2. Create GCS bucket: `workspace-{project_id[:8]}-{workspace_id[:8]}`
3. Deploy Cloud Run service from workspace image in Artifact Registry
   - Mount GCS bucket via GCS FUSE at `/workspace`
   - Set env vars: `REPO_URL`, `DEFAULT_BRANCH`, agent config from `workspace.config`
   - Region from workspace config
4. Cloud Run startup: clone repo into `/workspace/main/`
5. Store `cloud_run_url`, `cloud_run_service`, `gcs_bucket`
6. Transition to `ready`

**Teardown flow:**
1. Transition to `destroying`
2. Delete Cloud Run service
3. Optionally delete GCS bucket (flag: `preserve_storage`)
4. Transition to `destroyed`

**Stop flow (scale to zero):**
1. Scale Cloud Run to 0 instances
2. Transition to `stopped`

**Re-provision flow:**
1. From `stopped` → `provisioning` → `ready`
2. GCS bucket still exists, just redeploy Cloud Run

```python
class WorkspaceManager:
    def __init__(self, workspace_service: WorkspaceService, db: AsyncSession):
        self.workspace_service = workspace_service
        self.db = db

    async def provision(self, workspace_id: UUID) -> Workspace: ...
    async def teardown(self, workspace_id: UUID, preserve_storage: bool = True) -> Workspace: ...
    async def stop(self, workspace_id: UUID) -> Workspace: ...
    async def get_status(self, workspace_id: UUID) -> dict: ...
```

#### Workspace Container Image

Ubuntu 24.04 base with dev toolchain + a lightweight HTTP server.

**Dockerfile:** `infrastructure/workspace/Dockerfile`

**Workspace server** — runs inside the container, provides file/git/terminal access:

```
GET    /health                        # liveness
GET    /files/{path}                  # read file
PUT    /files/{path}                  # write file
DELETE /files/{path}                  # delete file
GET    /files                         # list directory
GET    /git/status                    # repo status
POST   /git/{operation}              # checkout, commit, diff, log
GET    /worktrees                     # list git worktrees
POST   /worktrees                     # create worktree (agent isolation)
DELETE /worktrees/{name}              # remove worktree
POST   /terminal                      # execute shell command
```

**Multi-agent isolation via git worktrees:**
```
/workspace/
  main/                      ← primary clone
  worktrees/
    agent-coder-abc/         ← coder agent's isolated worktree
    agent-reviewer-def/      ← reviewer agent's worktree
```

**Dependency:** The workspace image installs `agentic-patterns` as a pip dependency to get `sandbox-run`. It does NOT extend the existing sandbox Dockerfile — it's a standalone image that happens to use the `sandbox-run` entrypoint.

**Build pipeline:** Cloud Build → Artifact Registry at `northamerica-northeast2-docker.pkg.dev/stack-bench/workspace/workspace-server`

**Files:**
- New: `app/backend/src/molecules/services/workspace_manager.py`
- New: `infrastructure/workspace/Dockerfile`
- New: `infrastructure/workspace/server/` (workspace server — Python/FastAPI, lightweight)
- New: `infrastructure/workspace/cloudbuild.yaml`
- New: `app/backend/__tests__/molecules/test_workspace_manager.py`

---

### Phase 3: Workspace REST API (SB-070)

**Thin organism-layer router delegating to WorkspaceManager.**

#### Lifecycle Endpoints

```
POST   /api/projects/{project_id}/workspaces         # create workspace record
GET    /api/projects/{project_id}/workspaces         # list project workspaces
GET    /api/workspaces/{id}                          # get status + cloud_run_url
DELETE /api/workspaces/{id}                          # teardown
POST   /api/workspaces/{id}/provision                # trigger provisioning
POST   /api/workspaces/{id}/stop                     # scale to zero
```

#### Proxy Endpoints

Backend proxies requests to the workspace server (simpler auth, no CORS). The frontend never talks to Cloud Run directly.

```
ANY    /api/workspaces/{id}/proxy/{path:path}        # proxy to workspace server
```

Implementation: `httpx.AsyncClient` forwards request to `workspace.cloud_run_url/{path}`, returns response. Adds auth header for Cloud Run IAM.

#### Worktree Management

```
GET    /api/workspaces/{id}/worktrees                # list git worktrees
POST   /api/workspaces/{id}/worktrees                # create worktree
DELETE /api/workspaces/{id}/worktrees/{name}          # remove worktree
```

These are convenience endpoints that proxy to the workspace server's worktree API.

#### Router Structure

The app registers routers with `prefix="/api/v1"`, so the router itself uses no prefix. Endpoint paths are relative:

```python
# app/backend/src/organisms/api/routers/workspaces.py

router = APIRouter(tags=["workspaces"])

@router.post("/projects/{project_id}/workspaces")       # → /api/v1/projects/{id}/workspaces
@router.get("/projects/{project_id}/workspaces")
@router.get("/workspaces/{workspace_id}")
@router.delete("/workspaces/{workspace_id}")
@router.post("/workspaces/{workspace_id}/provision")
@router.post("/workspaces/{workspace_id}/stop")
@router.api_route("/workspaces/{workspace_id}/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
```

**Files:**
- New: `app/backend/src/organisms/api/routers/workspaces.py`
- Edit: `app/backend/src/organisms/api/routers/__init__.py`
- Edit: `app/backend/src/organisms/api/app.py` (register router)
- New: `app/backend/__tests__/organisms/api/test_workspaces.py`

## GCP Resource Naming

| Resource | Name Pattern |
|----------|-------------|
| Cloud Run service | `ws-{workspace_id[:8]}` |
| GCS bucket | `stack-bench-ws-{project_id[:8]}-{workspace_id[:8]}` |
| Artifact Registry image | `northamerica-northeast2-docker.pkg.dev/stack-bench/workspace/workspace-server:latest` |

## Open Questions

1. **Workspace server language** — Python/FastAPI is consistent with the backend, but Go would be lighter for a container sidecar. Recommendation: Python for now, same toolchain.

2. **GCS FUSE vs volume mount** — GCS FUSE has latency for git operations. Alternative: clone to ephemeral disk on startup, sync to GCS on shutdown. Recommendation: start with ephemeral disk + GCS backup, not FUSE.

3. **Auth for Cloud Run proxy** — service account with invoker role, or IAM token forwarding from user session? Recommendation: service account — backend is the only client.

4. **Workspace server as separate package** — should it live in `infrastructure/workspace/` or be a separate repo/package? Recommendation: keep in-tree for now, extract when it stabilizes.

## References

- Existing workspace model: `app/backend/src/features/workspaces/`
- Project domain spec: `docs/specs/2026-03-19-project-workspace-domain.md`
- EP-005 epic: `docs/epics/ep-005-project-domain.md`
- ADR-004: Stack & Branch Domain Model
- GCP deployment: Cloud Run + Cloud SQL in `northamerica-northeast2`
- agentic-patterns sandbox spec: `pattern_stack/docs/specs/003-sandbox.md`
- agentic-patterns agency/roster spec: `docs/specs/2026-03-25-agentnode-agency-roster.md`
