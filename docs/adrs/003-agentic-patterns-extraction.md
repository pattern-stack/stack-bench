# RFC-001: Extract SDLC Platform Code from agentic-patterns

**Status:** Draft
**Date:** 2026-03-14
**Author:** Dug

## Context

`agentic-patterns` is a compositional agent framework (Python). Over time, SDLC-specific platform code grew inside it — orchestrators, coding agent roles, a FastAPI app layer, persistence exporters. This code belongs in the pattern-stack platform, not the framework.

The platform stack is:
- **pattern-stack/backend** — Python API + agent runtime
- **pattern-stack/frontend** — TypeScript workbench UI
- **pattern-stack/cli** — Go CLI (`pts`)
- **backend-patterns** — shared infrastructure (persistence, events, job queue)
- **agentic-patterns** — agent framework (`pip install` dependency)

## Problem

The boundary between framework and platform is blurred. Someone installing `agentic-patterns` to build a customer support bot gets SDLC orchestrators, coding agent roles, and a FastAPI app they don't need. The platform can't evolve independently.

## Proposed Boundary

### agentic-patterns keeps (framework primitives)

| Layer | What |
|-------|------|
| Atoms | Persona, Judgment, Mission, Awareness, protocols (Task, Project, Tag, User) |
| Molecules | Toolbox, Manual, Capability |
| Organisms | RoleBuilder, AgentBuilder |
| Systems | AgentRunner, ClaudeCodeRunner, MockRunner, EventBus, BaseExporter, OTelExporter, LangfuseExporter |
| Workflows | Sequential, Parallel, TaskLoop, Evaluators |
| Rendering | PromptRenderer, section-based composition |
| Stores | InMemoryStore, ConversationStore protocol |
| Library | Generic examples, reusable judgments/responsibilities (non-SDLC) |
| Extensions | Protocol adapters (LinearAdapter), vendor-agnostic toolboxes |
| CLI | `ap run`, `ap config`, `ap session` |

### pattern-stack backend gets (SDLC platform)

| What | Current location in agentic-patterns | Notes |
|------|--------------------------------------|-------|
| DevelopOrchestrator | `agentic_patterns/orchestrator/` | 5-phase SDLC pipeline |
| Gates (GateHandler, GateDecision) | `agentic_patterns/orchestrator/gates.py` | |
| SessionState | `agentic_patterns/orchestrator/session.py` | May be replaced by Job model |
| Coding archetypes | `agentic_patterns/library/coding/archetypes.py` | understander, planner, specifier, implementer, validator |
| Implementer manual | `agentic_patterns/library/coding/manuals/implementer.py` | |
| AgentTaskToolbox | `agentic_patterns/extensions/task_management/agent_toolbox.py` | |
| PersistenceExporter | `agentic_patterns/core/systems/exporters/persistence.py` | Writes to platform-specific DB schema |
| FastAPI app | `agentic_patterns/app/orchestrator/` | Routers, schemas, deps |
| DatabaseStore | `agentic_patterns/app/db/` | Platform persistence |
| ConversationService | `agentic_patterns/app/api/conversation_service.py` | Partially framework, partially platform |

### Already scaffolded in agentic-patterns (transfer to pattern-stack)

The `app/backend/` directory has a complete spec and scaffolding for the platform backend:

- **Job model** (EventPattern) — SDLC state machine (queued → running → gated → complete/failed)
- **AgentRun model** (EventPattern) — per-phase execution tracking
- **DevelopWorkflow** — ported orchestrator using DB persistence instead of filesystem
- **RunnerPool** — phase-based runner selection (ClaudeAPIRunner for reasoning, ClaudeCodeRunner for implementation)
- **Dispatcher** — webhook → job → enqueue
- **Task facade** — status, cancel, gate approval
- **REST routers** — webhooks, jobs CRUD
- **CLI commands** — `pts dispatch`, `pts status`, `pts logs`, `pts cancel`
- **Workers** — Postgres-backed job queue via backend-patterns DatabaseBackend
- **Alembic migration** — initial tables
- **Spec:** `app/backend/docs/SPEC.md` (10-step implementation plan)

## Gray Areas (needs decision)

### ConversationService
Currently in `agentic_patterns/app/api/`. The *concept* of managing conversations is framework-level, but the current implementation has platform-specific wiring (DatabaseStore, PersistenceExporter). **Option A:** Keep a thin ConversationService protocol in framework, implement in platform. **Option B:** Keep as-is in framework since any agent app needs conversations.

### Linear adapter
The Task/Project/Tag *protocols* are framework. The LinearAdapter is an implementation. Other apps might use Linear too, so it could stay in the framework as a reference adapter. The SDLC-specific `AgentTaskToolbox` that wraps it is definitely platform.

### library/coding/ vs library/
The `library/` concept (reusable roles, judgments, responsibilities) is a good framework feature. The specific *coding* archetypes are platform. Could keep `library/` with generic examples and move `library/coding/` to platform.

### Sandbox
`pattern_stack/sandbox/` (Docker compose, dispatcher, entrypoint) is clearly platform infrastructure. No question — this moves.

### .claude/ agents, commands, skills
The SDLC agent definitions (`understander.md`, `planner.md`, etc.) and commands (`/develop`, `/implement`, `/design`) are platform. The `pattern-stack` skill and `skill-authoring` skill could stay with the framework or move. **Probably move** — they're about building pattern-stack apps specifically.

## Integration Point

Postgres is the integration surface between Python runtime and TS frontend:

```
agentic-patterns (framework)
    ↓ pip install
pattern-stack/backend (Python)
    ↓ PersistenceExporter writes events
    ↓ Job/AgentRun models write state
Postgres
    ↑ Drizzle reads
pattern-stack/frontend (TypeScript)
    ↑ Electric SQL real-time sync
```

No cross-language API bridge needed. The Python side writes, the TypeScript side reads, Electric handles reactivity.

## Migration Strategy

**Not decided yet.** Options:

1. **Big bang** — Move everything at once into pattern-stack backend, wire up imports
2. **Incremental** — Move one piece at a time, keeping backwards compat in agentic-patterns via re-exports
3. **Copy then delete** — Copy into pattern-stack, get it working, then remove from agentic-patterns

Option 3 is probably safest given we're still discovering the boundary.

## Open Questions

- [ ] Does pattern-stack backend import agentic-patterns as a dependency, or vendor specific modules?
- [ ] Where do the `.claude/` agent definitions live — in the platform repo or alongside the framework?
- [ ] Should agentic-patterns ship with *any* pre-built roles, or is the library purely a user concern?
- [ ] How does the Go CLI communicate with the Python backend? gRPC? REST? Subprocess?
- [ ] Does the frontend need its own API (Hono/Express) or does it talk directly to the Python FastAPI backend?

## References

- `agentic-patterns/app/backend/docs/SPEC.md` — Full implementation spec for platform backend
- `agentic-patterns/pattern_stack/.claude/docs/specs/2026-03-13-conversation-api-electric.md` — Conversation API spec
- `agentic-patterns/CLAUDE.md` — Framework architecture
- `pattern-stack/docs/PLAN-python-data-platform.md` — Earlier platform planning
