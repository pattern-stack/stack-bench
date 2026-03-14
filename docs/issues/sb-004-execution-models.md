---
id: SB-004
title: Execution domain features
status: draft
epic: EP-001
depends_on: [SB-001]
branch:
pr:
stack:
stack_index:
created: 2026-03-14
parallel_with: [SB-002, SB-003]
---

# Execution Domain Features

## Summary

Two pattern-stack features for job execution: Job and AgentRun. Near-direct copies from agentic_patterns/app/backend/features/ — already built with proper EventPattern and Field(). Not on the critical path for conversation MVP but establishes the execution domain for later.

**Parallel:** Can be developed in a worktree alongside SB-002 and SB-003 after SB-001 merges. Independent of both — merges whenever ready.

## Scope

What's in:
- Job(EventPattern) — states: queued → running → gated → complete/failed/cancelled
- AgentRun(EventPattern) — states: pending → running → complete/failed
- Minimal services: inherited CRUD only (custom queries deferred until execution molecule)
- Pydantic schemas
- Alembic migration for 2 tables
- Tests: model state machines, basic CRUD

What's out:
- Custom service queries like get_active(), get_by_repo() (added when execution molecule needs them)
- DevelopWorkflow, RunnerPool, Gates (deferred — not MVP)
- Dispatcher, Task facades (deferred)
- Job REST endpoints, webhook router (deferred)
- Workers (deferred)

## Implementation

```
features/
├── jobs/
│   ├── __init__.py
│   ├── models.py           # Job(EventPattern) — copy from existing
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── input.py
│   │   └── output.py
│   └── service.py          # JobService(BaseService) — inherited CRUD only
└── agent_runs/
    ├── __init__.py
    ├── models.py           # AgentRun(EventPattern) — copy from existing
    ├── schemas/
    │   ├── __init__.py
    │   ├── input.py
    │   └── output.py
    └── service.py          # AgentRunService(BaseService) — inherited CRUD only
```

## Verification

- [ ] Migration creates 2 tables
- [ ] Job state machine enforces valid transitions (queued→running OK, queued→complete blocked)
- [ ] Job.artifacts stores/retrieves JSON correctly
- [ ] AgentRun state machine works (pending→running→complete)
- [ ] Tests pass

## Notes

Source: `agentic_patterns/app/backend/features/{jobs,agent_runs}/`
Already pattern-stack compliant. Copy with import path changes only.
Not on MVP critical path (SB-001→002→005→006→007) but good parallel work and validates the execution domain model.
