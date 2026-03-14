# EP-001 Orchestration Plan

## Overview

This plan orchestrates the Backend MVP (EP-001) across 7 issues using 2 concurrent Claude Code panels with the builder+validator team pattern. Work is parallelized where the dependency graph allows.

## Agents Used

| Agent | Role | Mode | When |
|-------|------|------|------|
| **builder** (team) | Implements code following issue specs | read/write | Each issue |
| **validator** (team) | Reviews builder's work, runs quality gates | read-only | After each build |

The SDLC agents (understander, planner, specifier) have already done their work — issues and this plan are the output. We go straight to build+validate.

**Note:** The local `team/builder.md` and `team/validator.md` reference TypeScript/Biome conventions. For Python/pattern-stack work, builders should reference the pattern-stack skill docs at `/Users/dug/Projects/backend-patterns/.claude/skills/pattern-stack/` instead. Quality gates are `make ci` (format, lint, typecheck, test), not `bun run check`.

## Prerequisites

Before starting:
- [ ] `docs/epics/ep-001-orchestration-plan.md` committed (this file)
- [ ] `pts` CLI installed (`which pts` returns a path)
- [ ] `stack` CLI installed (`which stack` returns a path)
- [ ] Docker running (for Postgres)
- [ ] `ANTHROPIC_API_KEY` set in environment

## Stacking Strategy

Four stacks, not one. This enables parallel work:

```
sb-bootstrap:     SB-001
sb-conversations: SB-002 → SB-005 → SB-006 → SB-007
sb-agents:        SB-003
sb-execution:     SB-004
```

After SB-001 merges to main, three parallel stacks branch from main.

---

## Phase 1: Foundation (Sequential)

**Panels:** 1 builder, 1 idle (or validator reviewing as builder works)

### Step 1.1 — Create stack and branch

```bash
# Panel A (builder)
stack create sb-bootstrap --description project-scaffold
```

### Step 1.2 — Build SB-001: Project Bootstrap

**Builder reads:** `docs/issues/sb-001-bootstrap.md`
**Builder references:** pattern-stack `project-bootstrap.md` skill doc
**Builder references:** existing `agentic_patterns/app/backend/` for patterns.yaml, docker-compose structure

**Build actions:**
1. Run `pts init backend/` if available, otherwise scaffold manually
2. Create `backend/pyproject.toml` — deps: pattern-stack[dev,test], agentic-patterns, fastapi, uvicorn
3. Create `backend/config/settings.py` — AppSettings extending BaseSettings
4. Create `backend/organisms/api/app.py` — create_app() with health endpoint
5. Create `backend/alembic.ini` + `backend/alembic/env.py`
6. Create `backend/docker-compose.yml` — Postgres 16
7. Create `backend/Makefile` — dev, test, migrate, ci
8. Create `backend/tests/conftest.py` — pattern-stack fixtures
9. Create empty layer dirs: features/, molecules/, organisms/

**Validator checks:**
- `docker compose up -d` starts Postgres
- `make dev` starts uvicorn
- GET /health returns 200
- `make test` passes
- `make ci` passes

### Step 1.3 — Submit, merge SB-001

```bash
# Panel A
stack submit
# Wait for CI / self-review
# Merge to main via GH
stack sync
```

**Gate:** SB-001 merged to main before proceeding to Phase 2.

---

## Phase 2: Feature Models (Parallel — 2 panels)

Three issues can run simultaneously. With 2 panels, we run SB-002 + SB-003 in parallel. SB-004 runs after one finishes (or in a third worktree if available).

### Step 2.0 — Create parallel stacks

```bash
# Panel A
git checkout main && git pull
stack create sb-conversations --description conversation-models

# Panel B (separate worktree)
git checkout main && git pull
stack create sb-agents --description agent-models
```

### Step 2.1a — Panel A: Build SB-002 (Conversations)

**Builder reads:** `docs/issues/sb-002-conversation-models.md`
**Builder references:** pattern-stack `building-features.md`, `patterns-and-fields.md`
**Builder references:** `agentic_patterns/app/db/models/` for field definitions

**Build actions:**
1. Create `features/conversations/models.py` — Conversation(EventPattern) with state machine
2. Create `features/conversations/schemas/{input,output}.py`
3. Create `features/conversations/service.py` — BaseService inherited, no custom queries
4. Create `features/messages/` — Message(BasePattern), same structure
5. Create `features/message_parts/` — MessagePart(BasePattern)
6. Create `features/tool_calls/` — ToolCall(EventPattern) with state machine
7. Update `features/__init__.py` — import all models for alembic
8. Generate alembic migration
9. Write tests: model creation, state machines, inherited CRUD

**Quality gate:** `make ci` passes

### Step 2.1b — Panel B: Build SB-003 (Agents)

**Builder reads:** `docs/issues/sb-003-agent-models.md`
**Builder references:** pattern-stack `building-features.md`
**Builder references:** `agentic_patterns/app/features/{roles,agents}/`

**Build actions:**
1. Create `features/role_templates/models.py` — RoleTemplate(BasePattern)
2. Create `features/role_templates/schemas/` and `service.py`
3. Create `features/agent_definitions/models.py` — AgentDefinition(BasePattern) with FK to role_templates
4. Create `features/agent_definitions/schemas/` and `service.py` — add get_by_name(), list_active()
5. Create `seeds/agents.yaml` — 5 SDLC roles + definitions
6. Update `features/__init__.py`
7. Generate alembic migration
8. Write tests: CRUD, get_by_name, seed loading

**Quality gate:** `make ci` passes

### Step 2.2 — Validate both, submit

```bash
# Panel A: validator reviews SB-002
# Panel B: validator reviews SB-003

# After both pass:
# Panel A
stack submit  # sb-conversations stack (SB-002 PR)

# Panel B
stack submit  # sb-agents stack (SB-003 PR)
```

### Step 2.3 — Build SB-004 (Execution) — Panel B after SB-003 submits

**Builder reads:** `docs/issues/sb-004-execution-models.md`
**Builder references:** `agentic_patterns/app/backend/features/{jobs,agent_runs}/` — near-direct copy

```bash
# Panel B
stack create sb-execution --description execution-models
```

**Build actions:**
1. Copy Job(EventPattern) and AgentRun(EventPattern) from existing, update imports
2. Create schemas and minimal services
3. Generate alembic migration
4. Write tests for state machines

**Quality gate:** `make ci` passes

### Step 2.4 — Merge Phase 2

**Gate:** SB-002 and SB-003 must both be merged to main before Phase 3.
SB-004 can merge independently (not on critical path).

```bash
# After PRs approved and merged
stack sync  # on each stack
```

---

## Phase 3: Molecule Layer (Sequential — both panels on SB-005)

SB-005 is the largest issue and the core of the MVP. Both panels work on it — builder + validator as a tight pair.

### Step 3.0 — Advance conversations stack

```bash
# Panel A (builder)
git checkout main && git pull
# sb-conversations stack already exists, add next branch
git checkout -b dug/sb-conversations/2-conversation-molecule
stack push
```

### Step 3.1 — Build SB-005 (Conversation Molecule + Facade)

**Builder reads:** `docs/issues/sb-005-conversation-molecule.md`
**Builder references:** pattern-stack `building-molecules.md`
**Builder references:** `agentic_patterns/app/api/conversation_service.py`, `features/agents/assembler.py`

**Build actions (ordered):**

1. **Exceptions first** — `molecules/exceptions.py`
   - ConversationNotFoundError, AgentNotFoundError

2. **AgentAssembler** — `molecules/agents/assembler.py`
   - Compose RoleTemplateService + AgentDefinitionService
   - assemble(name) → Agent, list_available() → list[str]
   - Tests with seeded data

3. **Add custom service queries** (back in features — as-needed)
   - MessageService.get_by_conversation()
   - MessagePartService.get_by_message()
   - ToolCallService.get_by_conversation()

4. **ConversationEntity** — `molecules/entities/conversation_entity.py`
   - Compose all 4 conversation services + assembler
   - create_conversation(), send(), send_stream(), get_with_messages()
   - Tests with mocked runners

5. **ConversationAPI facade** — `molecules/apis/conversation_api.py`
   - Wraps entity + assembler
   - Returns Pydantic response schemas
   - Commits in facade (not entity)
   - Tests: verify response types, not ORM objects

**Validator reviews** after each sub-step or after all 5.

**Quality gate:** `make ci` passes

### Step 3.2 — Submit SB-005

```bash
# Panel A
stack submit  # adds SB-005 PR to sb-conversations stack
```

**Gate:** SB-005 merged before Phase 4.

---

## Phase 4: Organisms + Wiring (Sequential — tight pair)

### Step 4.0 — Advance stack

```bash
git checkout -b dug/sb-conversations/3-rest-api
stack push
```

### Step 4.1 — Build SB-006 (REST API)

**Builder reads:** `docs/issues/sb-006-rest-api.md`
**Builder references:** pattern-stack `building-organisms.md`
**Builder references:** `agentic_patterns/app/orchestrator/routers/`

**Build actions:**
1. Create `organisms/api/dependencies.py` — get_db, get_conversation_api (facade DI)
2. Create `organisms/api/routers/conversations.py` — thin handlers calling facade
3. Create `organisms/api/routers/agents.py` — thin handlers calling facade
4. Update `organisms/api/app.py` — register routers
5. Error translation map: molecule exceptions → HTTP status codes
6. Integration tests with httpx AsyncClient

**Key rule:** Every router handler is 3 lines: receive request → call facade → return response.

**Quality gate:** `make ci` passes

### Step 4.2 — Submit SB-006, then build SB-007

```bash
stack submit
# Optionally wait for review, or continue to SB-007

git checkout -b dug/sb-conversations/4-wire-and-run
stack push
```

### Step 4.3 — Build SB-007 (Wire + Run)

**Builder reads:** `docs/issues/sb-007-wire-and-run.md`

**Build actions:**
1. Update `organisms/api/app.py` lifespan — DB init, EventBus, PersistenceExporter
2. Create `seeds/agents.py` — load YAML seed data
3. Add `make seed` target to Makefile
4. Update docker-compose if needed (Jaeger optional)
5. End-to-end test: create conversation → send message → verify in DB

**End-to-end verification:**
```bash
docker compose up -d
make migrate
make seed
make dev
# In another terminal:
curl -X POST http://localhost:8000/api/v1/conversations/ \
  -H 'Content-Type: application/json' \
  -d '{"agent_name": "understander"}'
# → 201 with conversation ID

curl -X POST http://localhost:8000/api/v1/conversations/{id}/send \
  -H 'Content-Type: application/json' \
  -d '{"message": "explain what you do"}'
# → 200 with Claude response
```

### Step 4.4 — Final submit

```bash
stack submit  # SB-006 + SB-007 PRs in the stack
```

---

## Panel Assignment Summary

| Phase | Panel A | Panel B | Duration |
|-------|---------|---------|----------|
| 1 | Builder: SB-001 | Validator: reviews SB-001 | Short |
| 2 | Builder: SB-002 (conversations) | Builder: SB-003 (agents) | Parallel |
| 2+ | Validator: reviews SB-002 | Builder: SB-004 (execution) | Parallel |
| 3 | Builder: SB-005 (molecule) | Validator: reviews SB-005 | Tight pair |
| 4 | Builder: SB-006 → SB-007 | Validator: reviews each | Sequential |

## Worktree Usage

For Phase 2 parallel work:

```bash
# Panel A works in main worktree
cd /Users/dug/Projects/stack-bench

# Panel B works in a separate worktree
git worktree add ../stack-bench-agents dug/sb-agents/1-agent-models
cd /Users/dug/Projects/stack-bench-agents
```

Both panels share the same git repo but work on different branches without interference. The stack CLI handles worktree-aware operations (restack, sync).

## Alembic Migration Strategy

With parallel branches adding migrations, we need to handle conflicts:

- **SB-002, SB-003, SB-004** each generate their own migration
- When merging to main, the second and third migrations may conflict on `down_revision`
- **Resolution:** After merging, run `alembic merge heads -m "merge parallel migrations"` to create a merge migration
- Or: use a single migration branch by having each issue generate migration last, against latest main

**Recommended:** Each builder generates migration as the final step. Before merge, rebase onto latest main and regenerate if needed.

## Error Recovery

| Problem | Action |
|---------|--------|
| `make ci` fails on lint/format | Builder runs `make format`, fixes lint issues |
| Migration conflict | Rebase, regenerate migration from latest main |
| Test failure | Builder diagnoses and fixes; validator re-reviews |
| Merge conflict in stack | `stack restack` to cascade rebases |
| Blocked on dependency | Switch panel to a different parallelizable issue |

## Completion Criteria

EP-001 is done when:
- [ ] All 7 issues merged to main
- [ ] `docker compose up -d && make migrate && make seed && make dev` works
- [ ] Conversation create + send returns Claude response
- [ ] Data persisted in Postgres
- [ ] All stacks synced and cleaned up (`stack sync` on each)
