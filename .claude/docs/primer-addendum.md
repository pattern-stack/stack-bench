# Primer Addendum — ADR Decisions (2026-03-14)

> Layered on top of `primer.md`. The open questions in that doc have been answered by ADRs.

## Decisions Made

### CLI: Bubble Tea v2 (Go) — ADR-001

Ink was rejected. The fundamental problem is Ink's full-tree re-render (`eraseLines + rewrite`) which causes visual glitches that can't be engineered away. Bubble Tea v2's "Cursed Renderer" (ncurses-based, synchronized output) eliminates tearing/flicker.

The CLI is a **thin HTTP client** that manages the Python backend lifecycle. It does not share code with the backend. Users interact with the Go binary; the Python daemon runs behind it.

**One gap to build**: Streaming markdown renderer on top of Lip Gloss/goldmark (Glamour does full re-render, not incremental). Estimated days, not weeks.

### Backend: Python (pattern-stack) — ADR-002

TypeScript backend is removed. The TS `apps/api` (Hono + Drizzle conversations/messages/tool-calls) was duplicating what pattern-stack's BaseService/EventPattern already provides.

**Key reasoning:**
- Agent runtime (agentic-patterns) is Python — putting a TS backend in front adds a process boundary for every agent call with no benefit
- Pattern-stack is battle-tested (EventPattern state machines, job queue with DatabaseBackend, introspective codegen)
- Codegen-patterns (TS) is untested
- Three languages regardless: Go (CLI) + Python (backend + agents) + TS (React frontend)
- The TS framework demonstration goal is better served by DealBrain's full business domain, not stack-bench's thin CRUD

### Frontend: React (TypeScript) — unchanged

`apps/workbench` stays. Electric syncs Postgres tables regardless of what wrote to them. Pattern-stack codegen generates TypeScript entity stores from Python models via Jinja2.

## Revised Architecture

```
User
  │
  ▼
┌─────────────────────────────┐
│  CLI Binary (Go/Bubble Tea) │  ← Single binary, manages backend lifecycle
│  - TUI rendering            │
│  - HTTP client              │
│  - Backend daemon mgmt      │
└──────────┬──────────────────┘
           │ HTTP
           ▼
┌─────────────────────────────┐
│  Backend (Python/FastAPI)   │  ← pattern-stack + agentic-patterns
│  - ConversationService      │
│  - DevelopWorkflow (5-phase)│
│  - AgentEventBus + Gates    │
│  - Job queue (DatabaseBackend)
│  - Runners (ClaudeCode/API) │
└──────────┬──────────────────┘
           │ Electric / Postgres
           ▼
┌─────────────────────────────┐
│  Workbench (React/Vite)     │  ← TS frontend, Electric real-time sync
│  - Conversation viewer      │
│  - Entity stores (codegen'd)│
└─────────────────────────────┘
```

## What Stays in stack-bench

- `packages/stack/` — Stack CLI (TypeScript/Clipanion) — independent tool, keeps working
- `packages/codegen/` — Entity codegen (TypeScript) — generates TS frontend stores from YAML
- `apps/workbench/` — React frontend — points at Python API
- `docs/adrs/` — Architecture decisions

## What Gets Removed / Moved

- `apps/api/` — TS backend (Hono + Drizzle) — replaced by Python pattern-stack-app
- `entities/` — YAML entity defs may move to the Python project or stay as codegen input

## What Gets Built (see 2026-03-07-pattern-stack-app.md)

The full implementation spec is in the root: `2026-03-07-pattern-stack-app.md`. It defines:

1. **Project bootstrap**: pattern-stack-app repo with FastAPI, Alembic, patterns.yaml
2. **Models**: Job(EventPattern) + AgentRun(EventPattern) with state machines
3. **Molecules**: RunnerPool, Gates, DevelopWorkflow (ported from orchestrator)
4. **Organisms**: Dispatcher + Task facades, REST routers, CLI commands (pts)
5. **Workers**: Job handler + Worker using DatabaseBackend (no Redis)
6. **Infrastructure**: docker-compose (Postgres, Jaeger, Langfuse, backend, worker)

## References

- `docs/adrs/001-cli-framework.md` — Full CLI framework comparison
- `docs/adrs/002-backend-language.md` — Python vs TypeScript analysis
- `2026-03-07-pattern-stack-app.md` — Backend implementation spec
- `primer.md` — Original landscape doc (context on all projects)
