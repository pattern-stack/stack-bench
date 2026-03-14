---
title: Agent Orchestration Backend (v1)
date: 2026-03-07
status: implemented
branch: feat/pattern-stack-app
commit: 03c4837
---

> **Archived:** All 10 phases implemented in `agentic-patterns/app/backend/` on branch `feat/pattern-stack-app`. 36 tests passing. See ADR-002 for the decision to keep this as the Python backend.

# Pattern Stack App — Implementation Spec

**Date:** 2026-03-07
**Branch:** `feat/pattern-stack-app`
**Dependencies:** `agentic-patterns`, `backend-patterns` (pattern-stack)

## Goal

Rebuild the sandbox prototype as a proper Pattern Stack application. GitHub webhooks trigger multi-phase SDLC jobs (understand → plan → spec → implement → validate) using the agentic-patterns framework. Jobs are persisted, observable via Langfuse/Jaeger, and managed via `pts` CLI + REST API.

## Architecture

```
pattern-stack-app/
├── pyproject.toml
├── patterns.yaml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── .env.example
├── setup.sh
├── CLAUDE.md
├── .claude/commands/
├── app/
│   └── backend/
│       ├── __init__.py
│       ├── main.py                         # FastAPI entry + scope registration
│       ├── features/
│       │   ├── __init__.py                 # Model registration
│       │   ├── jobs/
│       │   │   ├── __init__.py
│       │   │   ├── models.py               # Job(EventPattern) — state machine
│       │   │   ├── service.py              # auto-generated EventService
│       │   │   └── schemas/
│       │   │       ├── __init__.py
│       │   │       ├── input.py            # JobCreate, JobUpdate
│       │   │       └── output.py           # JobResponse
│       │   └── agent_runs/
│       │       ├── __init__.py
│       │       ├── models.py               # AgentRun(EventPattern) — per-phase record
│       │       ├── service.py              # auto-generated EventService
│       │       └── schemas/
│       │           ├── __init__.py
│       │           ├── input.py            # AgentRunCreate, AgentRunUpdate
│       │           └── output.py           # AgentRunResponse
│       ├── molecules/
│       │   ├── __init__.py
│       │   ├── exceptions.py               # OrchestratorError, JobNotFoundError
│       │   ├── runner_pool.py              # Runner selection logic
│       │   ├── gates.py                    # GateHandler protocol + implementations
│       │   └── workflows/
│       │       ├── __init__.py
│       │       └── develop.py              # DevelopWorkflow (ported + adapted)
│       ├── organisms/
│       │   ├── __init__.py                 # Facade exports
│       │   ├── dispatcher.py               # Dispatcher facade
│       │   ├── task.py                     # Task facade (status/logs/cancel)
│       │   ├── rest/
│       │   │   ├── __init__.py             # App factory + router registration
│       │   │   ├── dependencies.py         # Auth/DI (simplified — no household)
│       │   │   ├── webhooks.py             # POST /webhook/github
│       │   │   └── jobs.py                 # GET /jobs, GET /jobs/:id, POST /jobs/:id/cancel
│       │   └── cli/
│       │       ├── __init__.py
│       │       ├── dispatch.py             # pts dispatch <repo> <issue>
│       │       ├── status.py               # pts status, pts status <job-id>
│       │       └── logs.py                 # pts logs <job-id>
│       ├── workers/
│       │   ├── __init__.py
│       │   ├── handlers.py                 # Job handlers (develop.run → DevelopWorkflow)
│       │   └── cli.py                      # pts worker start (separate process)
│       ├── seeds/
│       │   └── specs.py
│       └── __tests__/
│           ├── conftest.py
│           ├── factories.py
│           ├── test_models.py
│           ├── test_services.py
│           ├── test_orchestrator.py
│           └── test_dispatcher.py
├── seeds/
│   └── demo.yaml
└── docker-compose.yml                      # Postgres, Jaeger, Langfuse, backend, worker
```

## Phase 1: Project Bootstrap

### 1.1 Repository Setup
- Create `pattern-stack-app/` directory (sibling to `agentic-patterns`)
- `pyproject.toml` from skill template, with deps:
  - `pattern-stack[dev,test]` (backend-patterns)
  - `agentic-patterns` (local editable or git)
  - `claude-agent-sdk` (required by ClaudeCodeRunner/ClaudeAPIRunner)
  - `docker` (Python SDK, for future container dispatch)
- `patterns.yaml` with postgres enabled (no Redis needed — jobs use DatabaseBackend)
- `.env.example` with standard vars + `GITHUB_TOKEN`, `WEBHOOK_SECRET`, `ANTHROPIC_API_KEY`
- `setup.sh` from template
- `CLAUDE.md` with project overview

### 1.2 Database + Alembic
- `alembic init alembic`
- Replace `env.py` with template from skill doc
- Create `app/backend/features/__init__.py` importing all models

### 1.3 App Factory
- `app/backend/organisms/rest/__init__.py` with `create_app()`
- `app/backend/main.py` importing app
- Verify `/health` endpoint

## Phase 2: Feature Models

### 2.1 Job Model (`features/jobs/models.py`)

```python
class Job(EventPattern):
    __tablename__ = "jobs"

    class Pattern:
        entity = "job"
        reference_prefix = "JOB"

        states: ClassVar = {
            "queued":    ["running", "cancelled"],
            "running":   ["gated", "complete", "failed", "cancelled"],
            "gated":     ["running", "cancelled"],  # waiting for human gate
            "complete":  [],
            "failed":    [],
            "cancelled": [],
        }
        initial_state = "queued"

        state_phases = {
            "queued":    StatePhase.INITIAL,
            "running":   StatePhase.ACTIVE,
            "gated":     StatePhase.PENDING,
            "complete":  StatePhase.SUCCESS,
            "failed":    StatePhase.FAILURE,
            "cancelled": StatePhase.FAILURE,
        }

        history = HistoryCapability(
            track_changes=True,
            track_state=True,
            exclude=["updated_at"],
            retention="90d",
            expose_api=True,
        )

    # Fields
    repo_url: str = Field(str, required=True, max_length=500)
    repo_branch: str = Field(str, required=True, max_length=200, default="main")
    issue_number: int | None = Field(int, nullable=True, index=True)
    issue_title: str | None = Field(str, nullable=True, max_length=500)
    issue_body: str | None = Field(str, nullable=True)
    current_phase: str | None = Field(str, nullable=True, max_length=50)
    input_text: str | None = Field(str, nullable=True)
    error_message: str | None = Field(str, nullable=True, max_length=2000)
    artifacts: dict = Field(dict, default=dict, required=True)  # phase -> artifact text
    gate_decisions: list = Field(list, default=list, required=True)  # list of gate records
    job_record_id: UUID | None = Field(UUID, nullable=True)  # FK to pattern_stack job_records
```

### 2.2 AgentRun Model (`features/agent_runs/models.py`)

```python
class AgentRun(EventPattern):
    __tablename__ = "agent_runs"

    class Pattern:
        entity = "agent_run"
        reference_prefix = "RUN"

        states: ClassVar = {
            "pending":   ["running"],
            "running":   ["complete", "failed"],
            "complete":  [],
            "failed":    [],
        }
        initial_state = "pending"

        state_phases = {
            "pending":  StatePhase.INITIAL,
            "running":  StatePhase.ACTIVE,
            "complete": StatePhase.SUCCESS,
            "failed":   StatePhase.FAILURE,
        }

        history = HistoryCapability(
            track_changes=True,
            track_state=True,
            retention="90d",
        )

    # Fields
    job_id: UUID = Field(UUID, required=True, index=True, foreign_key="jobs.id")
    phase: str = Field(str, required=True, max_length=50)  # understand/plan/spec/implement/validate
    runner_type: str = Field(str, required=True, max_length=50)  # "api" or "code"
    model_used: str | None = Field(str, nullable=True, max_length=100)
    input_tokens: int = Field(int, default=0)
    output_tokens: int = Field(int, default=0)
    artifact: str | None = Field(str, nullable=True)  # phase output
    error_message: str | None = Field(str, nullable=True, max_length=2000)
    duration_ms: int | None = Field(int, nullable=True)
    attempt: int = Field(int, default=1)  # retry attempt number
```

### 2.3 Services
Both use `generate_event_service()` for auto-generated CRUD + transition methods:

```python
from pattern_stack.atoms.patterns.event_services import generate_event_service
JobService = generate_event_service(Job)
AgentRunService = generate_event_service(AgentRun)
```

### 2.4 Schemas
Standard Pydantic Create/Update/Response for both models. Response uses `from_attributes = True`.

## Phase 3: Molecules

### 3.1 Runner Pool (`molecules/runner_pool.py`)

Decides which runner to use per phase:

```python
from agentic_patterns.core.systems.runners.claude_api import ClaudeAPIRunner
from agentic_patterns.core.systems.runners.claude_code import ClaudeCodeRunner

class RunnerPool:
    def __init__(self):
        self._api_runner = ClaudeAPIRunner()
        self._code_runner = ClaudeCodeRunner()

    def get_runner(self, phase: str) -> RunnerProtocol:
        if phase == "implement":
            return self._code_runner
        return self._api_runner
```

### 3.2 Gates (`molecules/gates.py`)

Port `GateDecision`, `MockGateHandler` from `pattern_stack/orchestrator/gates.py`.

**Update `GateHandler` protocol signature** — the third parameter changes from `session: SessionState` to `job: Job` since we now use the DB model:

```python
@runtime_checkable
class GateHandler(Protocol):
    async def present_gate(
        self, phase: str, artifact: str, job: Job,
    ) -> tuple[GateDecision, str | None]: ...
```

Add `AutoApproveGateHandler` for fully automated pipeline (no human in loop):

```python
class AutoApproveGateHandler:
    async def present_gate(self, phase, artifact, job):
        return GateDecision.APPROVE, None
```

`WebhookGateHandler` (API-based gates) is **out of scope** for v1 — the async coordination between Worker and REST API needs separate design. Add as a stub that raises `NotImplementedError`.

### 3.3 DevelopWorkflow (`molecules/workflows/develop.py`)

Port `DevelopOrchestrator` from `pattern_stack/orchestrator/develop.py` as `DevelopWorkflow` (per Pattern Stack naming convention for multi-entity workflows). Changes:

1. **Replace `SessionState` with `Job` model** — artifacts and gate decisions stored in Job's JSON fields, persisted to DB instead of filesystem
2. **Create `AgentRun` records** — one per phase execution, tracking tokens/duration/artifacts
3. **Use `RunnerPool`** — instead of separate `reasoning_runner`/`coding_runner` params
4. **DB session integration** — accept `AsyncSession` for persistence
5. **Job state transitions** — call `job.transition_to()` at each lifecycle point

```python
class DevelopWorkflow:
    def __init__(self, db: AsyncSession, runner_pool: RunnerPool, gate_handler: GateHandler | None = None):
        self.db = db
        self.runner_pool = runner_pool
        self.gate_handler = gate_handler
        self.job_service = JobService()
        self.run_service = AgentRunService()

    async def run(self, job: Job) -> Job:
        job.transition_to("running")
        await self.db.flush()
        # ... same phase loop as original DevelopOrchestrator but with DB persistence
```

## Phase 4: Organisms

### 4.1 Dispatcher Facade (`organisms/dispatcher.py`)

Note: Since there is no auth model (internal service), facades are thin pass-throughs to molecule-layer logic. They exist for interface consistency with Pattern Stack conventions. Business logic (webhook parsing, job creation, queue enqueue) lives in `molecules/workflows/develop.py` and the `JobService`.

```python
@dataclass
class Dispatcher:
    db: AsyncSession

    async def dispatch_from_webhook(self, event_type: str, payload: dict) -> JobResponse:
        """Parse webhook payload, create Job via service, enqueue job."""
        ...

    async def dispatch_manual(self, repo_url: str, input_text: str) -> JobResponse:
        """Create Job from manual input via service."""
        ...
```

### 4.2 Task Facade (`organisms/task.py`)

```python
@dataclass
class Task:
    db: AsyncSession

    async def get_job(self, job_id: UUID) -> JobResponse: ...
    async def list_jobs(self, limit: int = 50, offset: int = 0) -> list[JobResponse]: ...
    async def cancel_job(self, job_id: UUID) -> JobResponse: ...
    async def get_runs(self, job_id: UUID) -> list[AgentRunResponse]: ...
    async def approve_gate(self, job_id: UUID, feedback: str | None = None) -> JobResponse: ...
```

### 4.3 REST Routers

**`rest/webhooks.py`** — `POST /webhook/github` (signature validation, dispatch)
**`rest/jobs.py`** — CRUD + cancel + gate approval endpoints
**`rest/dependencies.py`** — simplified DI (no auth initially, just DB session)

### 4.4 CLI Commands

**`pts dispatch <repo-url> --issue <N>`** — manual dispatch
**`pts status`** — list active jobs
**`pts status <job-ref>`** — job detail with phase progress
**`pts logs <job-ref>`** — agent run artifacts for a job
**`pts cancel <job-ref>`** — cancel a running job

## Phase 5: Workers

Uses Pattern Stack's built-in job queue (`pattern_stack.atoms.jobs`) with `DatabaseBackend` (Postgres). No Celery, no Redis.

### 5.1 Job Handler (`workers/handlers.py`)

Register an async handler that the Worker calls when a `develop.run` job is dequeued:

```python
from pattern_stack.atoms.jobs.models import JobRecord

async def handle_develop_run(job_record: JobRecord) -> None:
    """Handler for develop.run jobs. Called by Worker when dequeued."""
    payload = job_record.payload  # {"job_id": "<uuid>"}
    async with get_async_session() as db:
        job = await JobService().get(db, UUID(payload["job_id"]))
        workflow = DevelopWorkflow(db, RunnerPool(), AutoApproveGateHandler())
        await workflow.run(job)
        await db.commit()
    # Return normally = job_record marked COMPLETED
    # Raise exception = job_record marked FAILED/RETRYING/DEAD
```

### 5.2 Worker Startup (`workers/cli.py`)

Separate process from the FastAPI server. Run via `pts worker start`:

```python
from pattern_stack.atoms.jobs import configure_jobs, get_job_queue
from pattern_stack.atoms.jobs.backends.database import DatabaseBackend
from pattern_stack.atoms.jobs.worker import Worker

async def start_worker(max_concurrent: int = 3):
    """Start the job worker (separate process from web server)."""
    backend = DatabaseBackend(database_url=os.getenv("DATABASE_URL"))
    configure_jobs(backend)
    queue = get_job_queue()
    queue.register_handler("develop.run", handle_develop_run)

    worker = Worker(queue, max_concurrent=max_concurrent)
    await worker.start()  # blocks, polls for jobs
```

### 5.3 Enqueueing from Dispatcher

When a webhook or manual dispatch creates a Job, it enqueues a job_record:

```python
queue = get_job_queue()
await queue.enqueue(
    job_type="develop.run",
    payload={"job_id": str(job.id)},
    priority=0,
)
```

### 5.4 Two-Level Job Model

Important distinction between the two "job" concepts:

| Concept | Model | Purpose |
|---------|-------|---------|
| **Job** (EventPattern) | `features/jobs/models.py` | Domain entity with state machine, artifacts, gate decisions. Our business model. |
| **JobRecord** (raw Base) | `pattern_stack.atoms.jobs.models` | Queue infrastructure. Tracks enqueue/dequeue/retry/complete. Framework-provided. |

The `JobRecord.payload` contains `{"job_id": "<uuid>"}` linking the queue record to our domain Job. The handler loads the Job, runs the workflow, and the JobRecord lifecycle is managed automatically by the Worker.

## Phase 6: Infrastructure

### 6.1 docker-compose.yml

Services: postgres, jaeger, langfuse (optional), backend (uvicorn), worker (`pts worker start`)

No Redis needed — DatabaseBackend uses Postgres for the job queue.

### 6.2 Observability

- `ClaudeAPIRunner` and `ClaudeCodeRunner` both emit events via `AgentEventBus`
- Wire `LangfuseExporter` + `OTelExporter` at runner instantiation in `RunnerPool`
- Worker runs in separate process but shares the same Postgres, so OTel context can be propagated via JobRecord metadata

## Implementation Order

| Step | What | Depends On | PR-able? |
|------|------|------------|----------|
| 1 | Project bootstrap (pyproject, alembic, app factory, health endpoint) | — | Yes |
| 2 | Job + AgentRun models, services, schemas, migration | Step 1 | Yes |
| 3 | RunnerPool + Gates (molecules) | Step 2, agentic-patterns ClaudeAPIRunner | Yes |
| 4 | DevelopWorkflow port (molecules/workflows) | Steps 2-3 | Yes |
| 5 | Dispatcher + Task facades (organisms) | Step 4 | Yes |
| 6 | REST routers + webhook endpoint | Step 5 | Yes |
| 7 | CLI commands (pts dispatch/status/logs/cancel) | Step 5 | Yes |
| 8 | Job handler + Worker setup (Pattern Stack jobs) | Steps 4-5 | Yes |
| 9 | docker-compose + observability wiring | Step 8 | Yes |
| 10 | Tests (models, services, orchestrator, dispatcher) | All steps | Incremental |

Steps 1-2 are foundational. Steps 3-5 are the core domain. Steps 6-8 are interfaces. Step 9 is deployment. Tests are written alongside each step.

## What Ports vs What's New

### Ported from `pattern_stack/orchestrator/`
- `DevelopOrchestrator` → `molecules/workflows/develop.py` as `DevelopWorkflow` (adapted for DB persistence)
- `GateHandler` protocol (updated signature: `Job` replaces `SessionState`) + `MockGateHandler` → `molecules/gates.py`
- Agent builders (understander, planner, specifier, implementer, validator) stay in `agentic-patterns/library/coding/`

### New
- `Job` EventPattern model with state machine
- `AgentRun` EventPattern model per-phase tracking
- `RunnerPool` with `ClaudeAPIRunner`/`ClaudeCodeRunner` selection
- `Dispatcher` facade (webhook → job → enqueue)
- `Task` facade (status, cancel, gate approval)
- REST API + CLI
- Job handler + Worker (using Pattern Stack's built-in job queue with DatabaseBackend)
- docker-compose infrastructure

### From agentic-patterns (imported as dependency)
- `ClaudeAPIRunner`, `ClaudeCodeRunner`
- `AgentBuilder`, `RunnerProtocol`
- Coding roles (understander, planner, specifier, implementer, validator)
- `AgentEventBus`, `LangfuseExporter`, `OTelExporter`

### From backend-patterns (pattern-stack, imported as dependency)
- `JobRecord`, `DatabaseBackend`, `Worker`, `JobQueue` protocol (job queue subsystem)
- `BasePattern`, `EventPattern`, `Field`, `BaseService`, `generate_event_service`
- `create_app()` factory, `pts` CLI framework
- Testing fixtures (`BaseServiceTest`, `AsyncFactory`, testcontainers)

## Open Questions

1. **Auth for REST API?** Start without auth (internal service), add API key auth later?
2. **Gate approval via REST?** The `gated` state + `POST /jobs/:id/approve` is designed for this, but the async coordination (Worker blocking on gate) needs design. Options: Worker skips gated jobs (re-enqueue on approval), or store gate state in DB and poll.
3. **Container dispatch?** This spec uses in-process Workers. Docker container dispatch (like the sandbox prototype) is a future enhancement.
