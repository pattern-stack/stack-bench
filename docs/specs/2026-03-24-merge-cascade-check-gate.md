---
title: Merge Cascade Check Run Gate
date: 2026-03-24
status: draft
branch:
depends_on: []
adrs: [004-stack-branch-domain-model]
---

# Merge Cascade Check Run Gate

## Goal

Implement a webhook-driven merge cascade system that uses the Stack Bench GitHub App to gate merges to trunk via check runs. When a user triggers "Merge Stack", branches merge one-at-a-time bottom-up: each PR is retargeted to trunk, gated by a Stack Bench check run, rebased via ephemeral clone, verified against external CI, and auto-merged by GitHub -- all orchestrated through webhooks with zero polling.

## Problem Statement

The current `merge_stack` endpoint (in `StackAPI.merge_stack`) merges all PRs synchronously in a single request. This approach has critical problems:

1. **No CI verification** -- PRs are merged without waiting for CI to pass on the rebased branch
2. **No conflict detection** -- if a rebase onto trunk introduces conflicts, the merge blindly fails at the GitHub API level
3. **No atomicity** -- a partial failure leaves the stack in an inconsistent state with no recovery path
4. **Out-of-order merging** -- nothing prevents someone from merging a higher branch before lower ones
5. **Long-running request** -- merging a 5-branch stack with rebases can easily exceed HTTP timeout

The check run gate solves all of these by making GitHub itself enforce merge ordering and CI status, while webhooks drive the cascade asynchronously.

## Architecture Decision

### Why a MergeCascade model (not state on Stack)

A stack can have multiple cascade attempts over its lifetime. A cascade might partially complete (3 of 5 branches merged), then stop on a conflict. The user fixes the conflict and starts a new cascade for the remaining branches. Tracking this as state on `Stack` would lose history and make it impossible to report on past cascade attempts. A separate `MergeCascade` EventPattern with its own state machine cleanly models this lifecycle.

### Why CascadeStep (not state on Branch)

Each cascade needs to track per-branch progress through a multi-phase pipeline: retarget, rebase, CI wait, check completion, merge. This is per-cascade state, not intrinsic to the branch. A `Branch` might participate in multiple cascades over its lifetime (if the first attempt fails and a second is started). A `CascadeStep` model -- one per branch per cascade -- captures this cleanly.

### Why webhooks, not jobs

The cascade is inherently driven by external events (PR merged, check suite completed). Using the Jobs subsystem would require polling GitHub for status changes. Webhooks eliminate polling entirely -- GitHub tells us when things happen. The webhook handler is the "worker" that advances the cascade.

### Layer placement

| Component | Layer | Rationale |
|-----------|-------|-----------|
| `MergeCascade` model | Feature | Single-model CRUD, EventPattern with state machine |
| `CascadeStep` model | Feature | Single-model CRUD, EventPattern with state machine |
| `CheckRunService` | Feature | Single-model operations for check_runs table |
| `MergeCascadeEntity` | Molecule (entity) | Composes MergeCascade + CascadeStep + Branch + PR + GitHub operations |
| `CascadeWorkflow` | Molecule (workflow) | Multi-step cascade orchestration logic |
| Webhook router | Organism | HTTP input, signature verification, dispatches to molecule layer |
| Merge cascade endpoint | Organism | Thin route that creates cascade and kicks off first step |

## Domain Model

```
Stack (existing)
  |
  | 1:N
  v
MergeCascade (new, EventPattern)
  - stack_id (FK)
  - triggered_by (str -- who initiated)
  - current_position (int -- which branch is being processed)
  - state: pending -> running -> completed | failed | cancelled
  |
  | 1:N
  v
CascadeStep (new, EventPattern)
  - cascade_id (FK)
  - branch_id (FK)
  - pull_request_id (FK, nullable)
  - position (int)
  - state: pending -> retargeting -> rebasing -> ci_pending -> completing -> merged | conflict | failed | skipped
  - check_run_external_id (BigInteger, nullable -- GitHub check run ID)
  - error (str, nullable)
  - started_at (datetime, nullable)
  - completed_at (datetime, nullable)

CheckRun (new, BasePattern)
  - pull_request_id (FK)
  - external_id (int -- GitHub check run ID)
  - head_sha (str)
  - status (str -- queued | in_progress | completed)
  - conclusion (str, nullable -- success | failure | cancelled)
```

### State Machines

**MergeCascade states:**
```
pending -----> running -----> completed
  |              |
  |              +----------> failed
  |
  +------------------------> cancelled
```

**CascadeStep states:**
```
pending -> retargeting -> rebasing -> ci_pending -> completing -> merged
  |           |              |            |              |
  +-----------|--------------|------------|--------------|------> skipped
              +--------------|------------|--------------|------> failed
                             +------------|--------------|------> conflict
                                          +--------------|------> failed
                                                         +-----> failed
```

### Webhook Flow (the core cascade loop)

```
User clicks "Merge Stack"
  |
  v
POST /api/v1/stacks/{id}/merge-cascade
  |
  v
Create MergeCascade (pending)
Create CascadeSteps (pending) for each unmerged branch
Transition cascade to running
  |
  v
Start Step 1 (bottom branch, already targets trunk):
  transition step -> retargeting (no-op, already targets trunk)
  transition step -> rebasing
  Ephemeral clone: rebase branch onto trunk, force-push
  Update branch head_sha in DB
  transition step -> ci_pending
  Create/update check run (status: in_progress) via GitHub API
  |
  v
[Wait -- no polling, webhook-driven]
  |
  v
Webhook: check_suite.completed (external CI finishes)
  |
  v
Webhook handler:
  Find cascade step by head_sha
  Verify: external CI green + predecessors merged
  If yes:
    Complete Stack Bench check run (conclusion: success)
    transition step -> completing
  |
  v
Webhook: pull_request.closed (merged: true)
  |
  v
Webhook handler:
  transition step -> merged
  transition branch -> merged, PR -> merged
  |
  v
Advance to next step:
  Retarget next PR to trunk (GitHub API: PATCH /pulls/{n})
  Rebase next branch onto trunk (ephemeral clone)
  Create new check run on next PR
  transition next step -> ci_pending
  |
  v
[Repeat until all steps merged or one fails]
  |
  v
All steps merged -> transition cascade to completed
Any step conflict/failed -> transition cascade to failed
```

## GitHub App API Operations

These are the specific GitHub API calls needed. All use the GitHub App installation token (not personal access token). The existing `GitHubAdapter` will be extended.

| Operation | API Call | Notes |
|-----------|----------|-------|
| Create check run | `POST /repos/{owner}/{repo}/check-runs` | Body: `{name, head_sha, status: "in_progress"}` |
| Complete check run | `PATCH /repos/{owner}/{repo}/check-runs/{id}` | Body: `{status: "completed", conclusion: "success"}` |
| Fail check run | `PATCH /repos/{owner}/{repo}/check-runs/{id}` | Body: `{status: "completed", conclusion: "failure"}` |
| Retarget PR base | `PATCH /repos/{owner}/{repo}/pulls/{number}` | Body: `{base: "main"}` |
| Merge PR | `PUT /repos/{owner}/{repo}/pulls/{number}/merge` | With `merge_method: "squash"` -- same as existing `merge_pr` |
| Get check suites for ref | `GET /repos/{owner}/{repo}/commits/{ref}/check-suites` | To verify external CI status |

**Check run name**: `"Stack Bench / merge-gate"` -- consistent name so branch protection rules can reference it.

**Authentication**: GitHub App check run APIs require a JWT-based installation access token, not a personal access token. The `GITHUB_TOKEN` in settings may need to become an app installation token, or we add `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, and `GITHUB_INSTALLATION_ID` settings. This is a deployment concern -- for MVP, we can use a fine-grained PAT with `checks:write` permission if the repo is configured to accept it. True GitHub App auth is a future phase.

## Data Model Changes

### New Feature: `merge_cascades`

```python
# features/merge_cascades/models.py
class MergeCascade(EventPattern):
    __tablename__ = "merge_cascades"

    class Pattern:
        entity = "merge_cascade"
        reference_prefix = "MC"
        initial_state = "pending"
        states = {
            "pending": ["running", "cancelled"],
            "running": ["completed", "failed", "cancelled"],
            "completed": [],
            "failed": [],
            "cancelled": [],
        }
        state_phases = {
            "pending": StatePhase.INITIAL,
            "running": StatePhase.ACTIVE,
            "completed": StatePhase.SUCCESS,
            "failed": StatePhase.FAILURE,
            "cancelled": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    stack_id = Field(UUID, foreign_key="stacks.id", required=True, index=True)
    triggered_by = Field(str, required=True, max_length=200)
    current_position = Field(int, default=0)
    error = Field(str, nullable=True)
```

### New Feature: `cascade_steps`

```python
# features/cascade_steps/models.py
class CascadeStep(EventPattern):
    __tablename__ = "cascade_steps"

    class Pattern:
        entity = "cascade_step"
        reference_prefix = "CS"
        initial_state = "pending"
        states = {
            "pending": ["retargeting", "skipped"],
            "retargeting": ["rebasing", "failed"],
            "rebasing": ["ci_pending", "conflict", "failed"],
            "ci_pending": ["completing", "failed"],
            "completing": ["merged", "failed"],
            "merged": [],
            "conflict": [],
            "failed": [],
            "skipped": [],
        }
        state_phases = {
            "pending": StatePhase.INITIAL,
            "retargeting": StatePhase.ACTIVE,
            "rebasing": StatePhase.ACTIVE,
            "ci_pending": StatePhase.PENDING,
            "completing": StatePhase.PENDING,
            "merged": StatePhase.SUCCESS,
            "conflict": StatePhase.FAILURE,
            "failed": StatePhase.FAILURE,
            "skipped": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    cascade_id = Field(UUID, foreign_key="merge_cascades.id", required=True, index=True)
    branch_id = Field(UUID, foreign_key="branches.id", required=True, index=True)
    pull_request_id = Field(UUID, foreign_key="pull_requests.id", nullable=True, index=True)
    position = Field(int, required=True, min=1)
    check_run_external_id = Field(BigInteger, nullable=True)  # GitHub check run IDs can exceed 32-bit
    head_sha = Field(str, nullable=True, max_length=40)
    error = Field(str, nullable=True)
    started_at = Field(datetime, nullable=True)
    completed_at = Field(datetime, nullable=True)
```

### New Feature: `check_runs`

```python
# features/check_runs/models.py
class CheckRun(BasePattern):
    __tablename__ = "check_runs"

    class Pattern:
        entity = "check_run"
        reference_prefix = "CHK"
        track_changes = True

    pull_request_id = Field(UUID, foreign_key="pull_requests.id", required=True, index=True)
    external_id = Field(BigInteger, required=True, unique=True, index=True)  # GitHub IDs can exceed 32-bit
    head_sha = Field(str, required=True, max_length=40, index=True)
    name = Field(str, required=True, max_length=200)
    status = Field(str, required=True, max_length=20, choices=["queued", "in_progress", "completed"])
    conclusion = Field(str, nullable=True, max_length=20, choices=["success", "failure", "cancelled"])
```

### Existing Model Changes

**PullRequest** -- add `base_ref` field:

```python
# The PR needs to know its current base branch for retargeting logic
base_ref = Field(str, nullable=True, max_length=200)
```

No state machine changes needed on existing models. The existing `PullRequest` and `Branch` state transitions are triggered by the cascade workflow when appropriate.

**Important**: The existing state machines require intermediate transitions:
- **PullRequest**: `open -> approved -> merged` (not `open -> merged` directly). The cascade workflow must transition through `approved` before `merged`.
- **Branch**: Must be in `submitted` state before transitioning to `merged`. The cascade should transition branches through `pushed -> ... -> submitted` as needed, or validate that branches are in `submitted` state at cascade creation time. For MVP, the cascade startup validates all branches are in `submitted` state and rejects the cascade otherwise.

## API Changes

### New Endpoint: Start Merge Cascade

```
POST /api/v1/stacks/{stack_id}/merge-cascade
```

Request body:
```json
{
  "merge_method": "squash"  // optional, default "squash"
}
```

Response:
```json
{
  "cascade_id": "uuid",
  "stack_id": "uuid",
  "state": "running",
  "steps": [
    {
      "step_id": "uuid",
      "branch_name": "user/stack/1-first",
      "position": 1,
      "state": "rebasing"
    },
    ...
  ]
}
```

This replaces the existing `POST /stacks/{stack_id}/merge` endpoint. The old endpoint should be deprecated (return 410 Gone) or removed.

### New Endpoint: Get Cascade Status

```
GET /api/v1/stacks/{stack_id}/merge-cascade/{cascade_id}
```

Returns the cascade with all steps and their current states. Used by the frontend to render cascade progress.

### New Endpoint: Cancel Cascade

```
POST /api/v1/stacks/{stack_id}/merge-cascade/{cascade_id}/cancel
```

Cancels a running cascade. Skips remaining steps. Does not revert already-merged branches.

### New Router: Webhooks

```
POST /api/v1/webhooks/github
```

Single endpoint that receives all GitHub webhook events. Dispatched by event type:

- `check_suite.completed` -- external CI finished, evaluate cascade step
- `pull_request.closed` (with `merged: true`) -- PR merged, advance cascade
- `check_run.completed` -- our own check run completed (informational)

**Signature verification**: The webhook payload is verified using `WEBHOOK_SECRET` (already in settings) via HMAC-SHA256 against the `X-Hub-Signature-256` header. This happens at the organism layer before any domain logic.

## File Tree

```
app/backend/src/
  features/
    merge_cascades/                    # NEW feature
      __init__.py
      models.py                        # MergeCascade EventPattern
      schemas/
        __init__.py
        input.py                       # MergeCascadeCreate, MergeCascadeUpdate
        output.py                      # MergeCascadeResponse
      service.py                       # MergeCascadeService(EventService)

    cascade_steps/                     # NEW feature
      __init__.py
      models.py                        # CascadeStep EventPattern
      schemas/
        __init__.py
        input.py                       # CascadeStepCreate, CascadeStepUpdate
        output.py                      # CascadeStepResponse
      service.py                       # CascadeStepService(EventService)

    check_runs/                        # NEW feature
      __init__.py
      models.py                        # CheckRun BasePattern
      schemas/
        __init__.py
        input.py                       # CheckRunCreate, CheckRunUpdate
        output.py                      # CheckRunResponse
      service.py                       # CheckRunService(BaseService)

    pull_requests/
      models.py                        # MODIFY -- add base_ref field

  molecules/
    entities/
      merge_cascade_entity.py          # NEW -- domain aggregate for cascade lifecycle
    workflows/
      cascade_workflow.py              # NEW -- multi-step cascade orchestration
    services/
      webhook_dispatcher.py            # NEW -- routes webhook events to handlers
    providers/
      github_adapter.py                # MODIFY -- add check run + retarget methods

  organisms/
    api/
      routers/
        stacks.py                      # MODIFY -- add cascade endpoints, deprecate old merge
        webhooks.py                    # NEW -- webhook receiver + signature verification
      app.py                           # MODIFY -- register webhook router
      dependencies.py                  # MODIFY -- add cascade dependencies

  config/
    settings.py                        # MODIFY -- add GITHUB_APP_ID etc. (future)

app/backend/
  alembic/
    versions/
      XXXX_add_merge_cascade_tables.py # NEW migration
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Feature models + services (MergeCascade, CascadeStep, CheckRun) + migration | -- |
| 2 | GitHubAdapter extensions (check runs, retarget PR) | -- |
| 3 | MergeCascadeEntity + CascadeWorkflow (molecule layer) | Phase 1, 2 |
| 4 | Webhook router + dispatcher (organism layer) | Phase 3 |
| 5 | Cascade REST endpoints + dependency wiring | Phase 3, 4 |
| 6 | Frontend cascade UI (progress indicator, conflict reporting) | Phase 5 |

## Phase Details

### Phase 1: Feature Models + Services + Migration

Create three new features following the standard pattern-stack feature structure.

**`features/merge_cascades/`**: Model, create/update schemas, response schema, service extending `EventService`. The service needs a custom `get_active_for_stack` method to find the running cascade for a stack (at most one active cascade per stack).

**`features/cascade_steps/`**: Model, schemas, service. Custom methods: `list_by_cascade(db, cascade_id)`, `get_by_head_sha(db, head_sha)` (for `check_suite.completed` webhook lookup), `get_by_pull_request(db, pull_request_id)` (for `pull_request.closed` webhook lookup), `get_pending_step(db, cascade_id)` (next step to process).

**`features/check_runs/`**: Model, schemas, service. Custom methods: `get_by_external_id(db, external_id)`, `get_by_pull_request(db, pr_id)`.

**Migration**: Single alembic migration creating all three tables. Add `base_ref` column to `pull_requests`.

### Phase 2: GitHubAdapter Extensions

Add methods to `GitHubAdapter` in `molecules/providers/github_adapter.py`:

```python
async def create_check_run(self, owner, repo, name, head_sha) -> dict:
    """POST /repos/{owner}/{repo}/check-runs"""

async def update_check_run(self, owner, repo, check_run_id, status, conclusion=None, output=None) -> dict:
    """PATCH /repos/{owner}/{repo}/check-runs/{check_run_id}"""

async def retarget_pr(self, owner, repo, pr_number, new_base) -> dict:
    """PATCH /repos/{owner}/{repo}/pulls/{pr_number} with base update"""

async def get_check_suites(self, owner, repo, ref) -> list[dict]:
    """GET /repos/{owner}/{repo}/commits/{ref}/check-suites"""
```

These are pure API wrappers with no business logic. They follow the same pattern as existing `merge_pr` and `mark_pr_ready`.

### Phase 3: MergeCascadeEntity + CascadeWorkflow

**`molecules/entities/merge_cascade_entity.py`**:

Domain aggregate that composes `MergeCascadeService`, `CascadeStepService`, `CheckRunService`, `BranchService`, `PullRequestService`. Key methods:

- `create_cascade(stack_id, triggered_by)` -- creates cascade + steps for all unmerged branches
- `get_cascade_detail(cascade_id)` -- cascade with steps and branch/PR data
- `advance_cascade(cascade_id)` -- processes the next pending step
- `complete_step(step_id)` -- marks step as merged, calls advance
- `fail_step(step_id, error)` -- marks step as failed, fails cascade

**`molecules/workflows/cascade_workflow.py`**:

The core orchestration logic. A single `process_step` method that:

1. Retargets the PR to trunk (GitHub API)
2. Rebases the branch onto trunk (ephemeral clone via `RemoteRestackService`)
3. Updates `head_sha` in DB
4. Creates/updates the Stack Bench check run (in_progress)
5. Transitions step to `ci_pending`

And a `evaluate_step` method (called from webhook) that:

1. Checks external CI status (all check suites green, excluding our own)
2. Checks predecessor steps are all merged
3. If both pass: completes check run (success), transitions to `completing`
4. If CI failed: fails check run, transitions to `failed`

### Phase 4: Webhook Router + Dispatcher

**`organisms/api/routers/webhooks.py`**:

Single `POST /api/v1/webhooks/github` endpoint. Responsibilities (organism layer only):

1. Read raw body for signature verification
2. Verify HMAC-SHA256 signature using `WEBHOOK_SECRET`
3. Parse event type from `X-GitHub-Event` header
4. Parse JSON payload
5. Dispatch to `WebhookDispatcher`

**`molecules/services/webhook_dispatcher.py`**:

Routes events to domain handlers. Lives in molecule layer because it contains domain logic:

- `handle_check_suite_completed(payload)` -- find cascade step by `head_sha` (from payload `check_suite.head_sha`), call `evaluate_step`
- `handle_pull_request_merged(payload)` -- find PR by `external_id` (from payload `pull_request.number`), then find cascade step by `pull_request_id`, call `complete_step` (transitioning PR `open -> approved -> merged` and Branch `-> merged`), then `advance_cascade`
- Ignores events not related to an active cascade (idempotent, safe)

### Phase 5: Cascade REST Endpoints + Wiring

Add to `organisms/api/routers/stacks.py`:

- `POST /{stack_id}/merge-cascade` -- creates and starts cascade
- `GET /{stack_id}/merge-cascade/{cascade_id}` -- get cascade status
- `POST /{stack_id}/merge-cascade/{cascade_id}/cancel` -- cancel

Deprecate `POST /{stack_id}/merge` (return 410 or redirect).

Wire `MergeCascadeEntity` through `StackAPI` or a new `CascadeAPI` facade in dependencies.

Register webhook router in `app.py`.

### Phase 6: Frontend Cascade UI

- Replace "Merge Stack" button action to call merge-cascade endpoint
- Show cascade progress: per-step status with state indicators
- Show conflict details when cascade fails
- Poll cascade status endpoint (or use SSE/broadcast subsystem in future)

## Key Design Decisions

### 1. One active cascade per stack

Enforced at the entity level. Starting a new cascade while one is running returns an error. The user must cancel the running cascade first. This prevents conflicting operations.

### 2. Check run only on trunk-targeting PR

Per the core design constraint, only the PR currently targeting trunk gets a Stack Bench check run. Intermediate branch-to-branch PRs have no Stack Bench check run. This means users can freely manage intermediate PRs without Stack Bench interference.

### 3. Retarget-then-rebase ordering

When advancing to the next branch after a merge, we retarget the PR to trunk first (so GitHub shows the right diff), then rebase the branch onto trunk (so the code is correct). The check run is created after the rebase completes with the new head SHA.

### 4. Ephemeral clone reuse

The existing `RemoteRestackService` already handles single-branch rebasing. For the cascade, we rebase one branch at a time (not the full stack at once) because each rebase depends on the previous branch being merged into trunk. We can call `RemoteRestackService.restack` with a single-branch list, or extract the single-branch rebase logic into a reusable method.

### 5. Webhook idempotency

Webhooks can be delivered multiple times. Every handler must be idempotent:
- If a step is already in `merged` state and we get another `pull_request.closed` event, ignore it
- If a check suite completion arrives for a step already past `ci_pending`, ignore it
- State transition guards (EventPattern's `can_transition_to`) provide natural idempotency

### 6. Check run naming and filtering

The Stack Bench check run is named `"Stack Bench / merge-gate"`. When evaluating external CI status, we filter out check suites created by our own GitHub App (by app ID or check name) to avoid circular dependencies.

### 7. Conflict handling

If the ephemeral clone rebase hits a conflict:
- The cascade step transitions to `conflict` (terminal state)
- The cascade transitions to `failed`
- Remaining steps transition to `skipped`
- The UI shows which files conflicted (from `RestackBranchResult.conflicting_files`)
- The user resolves conflicts locally, force-pushes, and starts a new cascade

### 8. No auto-merge API

We do not use GitHub's "enable auto-merge" API. Instead, we complete the check run (which satisfies branch protection) and let GitHub merge because branch protection + auto-merge is already configured on the repo. If auto-merge is not enabled, the check run completion still signals readiness, and the user (or a subsequent webhook handler) can trigger the merge API call directly. For MVP, we call `merge_pr` immediately after completing the check run, rather than relying on GitHub auto-merge configuration.

### 9. Separate webhook router (not on stacks router)

Webhooks are a distinct input channel from the REST API. They have different auth (HMAC signature vs bearer token), different payload formats, and different consumers (GitHub vs frontend). A separate router under `/api/v1/webhooks/github` is cleaner than nesting under `/stacks`.

### 10. BasePattern for CheckRun (not EventPattern)

CheckRuns don't need a state machine. Their `status` and `conclusion` are simple string fields mirroring GitHub's API, not transitions we enforce. They are a record of what we told GitHub, updated via simple field writes.

## Testing Strategy

### Unit Tests (no DB, no network)

- **CascadeWorkflow logic**: Mock all services, verify correct step transitions for happy path, conflict, CI failure
- **WebhookDispatcher routing**: Mock entity, verify correct handler called for each event type
- **Webhook signature verification**: Test HMAC validation with known secrets/payloads
- **Idempotency**: Verify duplicate webhook delivery is safely ignored

Marker: `@pytest.mark.unit`

### Integration Tests (DB, no network)

- **MergeCascadeEntity**: Create cascade, verify steps created for all unmerged branches
- **Step advancement**: Mock GitHubAdapter, verify retarget + rebase + check run creation sequence
- **State machine transitions**: Verify all valid/invalid transitions on MergeCascade and CascadeStep
- **One-active-cascade enforcement**: Verify second cascade creation fails while one is running

Marker: `@pytest.mark.integration`
Fixtures: `stack_with_branches` factory that creates a full stack with branches and PRs

### End-to-End Tests (DB + mocked GitHub)

- **Full cascade flow**: Start cascade, simulate webhooks for each step, verify final state is `completed`
- **Conflict mid-cascade**: Simulate conflict on step 3 of 5, verify steps 4-5 are `skipped`
- **Cancel mid-cascade**: Start cascade, cancel after step 2, verify remaining steps `skipped`

Marker: `@pytest.mark.integration`
Use `httpx.MockTransport` or `respx` for GitHub API mocking.

## Open Questions (Resolved)

### 1. Is MergeCascade a new feature model or does it live on Stack?

**Decision**: New feature model. A stack can have multiple cascades over its lifetime. Each cascade has its own state machine and history. See "Architecture Decision" section above.

### 2. Where do webhook handlers live?

**Decision**: The HTTP endpoint (signature verification, routing) lives in the organism layer (`organisms/api/routers/webhooks.py`). The domain logic (finding cascade steps, evaluating CI status, advancing cascades) lives in the molecule layer (`molecules/services/webhook_dispatcher.py`). This follows the standard organism/molecule separation: organisms handle HTTP concerns, molecules handle business logic.

### 3. Per-branch cascade state?

**Decision**: `CascadeStep` model -- a through entity between `MergeCascade` and `Branch`. Not on Branch itself, because cascade state is per-cascade, not intrinsic to the branch.

### 4. GitHub API operations needed?

**Decision**: See "GitHub App API Operations" section. Six operations total: create check run, complete/fail check run, retarget PR base, merge PR (existing), get check suites.

### 5. How does this interact with the existing merge endpoint?

**Decision**: The existing `POST /stacks/{stack_id}/merge` endpoint is deprecated and replaced by `POST /stacks/{stack_id}/merge-cascade`. The old synchronous merge was always a stepping stone. The cascade approach is the correct long-term design.

## Future Considerations

- **Intermediate branch gates**: The current design only gates the trunk-targeting PR. Future work could add check runs to intermediate PRs to prevent premature merging within the stack.
- **GitHub App auth**: MVP uses a fine-grained PAT with `checks:write`. Production should use proper GitHub App JWT-based installation tokens for better security and higher rate limits.
- **Broadcast/SSE for real-time UI**: Instead of polling the cascade status endpoint, the Broadcast subsystem could push step state changes to the frontend in real time.
- **Retry failed steps**: A failed step (non-conflict) could be retried without creating an entirely new cascade.
- **Parallel CI**: For stacks where branches are independent, future work could run CI on multiple branches simultaneously rather than strictly sequential.
