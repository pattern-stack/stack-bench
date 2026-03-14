# ADR-002: Backend Language — Python (Pattern Stack)

**Date:** 2026-03-14
**Status:** Accepted
**Deciders:** Dug
**Related:** ADR-001 (CLI Framework)

## Context

With the CLI decided as a thin Go/Bubble Tea client (ADR-001), we need to choose the backend language and framework. The backend handles: REST API, database persistence, job queue, webhook ingestion, agent orchestration (DevelopWorkflow), and the agent runtime (agentic-patterns).

Two candidates existed:

1. **Python** — pattern-stack (FastAPI + SQLAlchemy + built-in jobs subsystem + Electric codegen) plus agentic-patterns (agent framework with runners, roles, gates, event bus)
2. **TypeScript** — stack-bench's Hono + Drizzle app, with codegen-patterns (untested) for entity scaffolding, calling the Python agent runtime over a process boundary

A partial TS implementation already existed in `stack-bench` (apps/api with conversation/message/tool-call entities).

## Decision

**Python with pattern-stack and agentic-patterns.**

The TS backend is removed. The React frontend (apps/workbench) remains — it doesn't care what language the backend is. Electric syncs Postgres tables regardless of what wrote to them.

## Why

### Agent runtime is Python, and separation is premature

The agent runtime (`agentic-patterns`) is a substantial Python framework: roles, runners (ClaudeCodeRunner, AgentRunner), capabilities, toolboxes, manuals, rendering pipeline, event bus, gates, conversation stores, exporters. The Claude Agent SDK bridge is Python. Rebuilding this in TS would take months to reach parity with no functional gain.

A TS backend would require a process boundary (subprocess/HTTP/queue) for every agent invocation. With a Python backend, DevelopWorkflow calls RunnerPool calls ClaudeCodeRunner directly — no serialization, no boundary, no failure mode to manage.

Long-term, the agent runtime should become a separate service regardless of language — different scaling profile, different deployment concerns. But that split happens when needed, not now. When it does, the app backend language still doesn't matter — it's HTTP either way.

### Pattern-stack is proven, codegen-patterns is not

Pattern-stack has battle-tested patterns: EventPattern (state machines), ActorPattern, RelationalPattern, CatalogPattern. Built-in jobs subsystem with DatabaseBackend (`SELECT FOR UPDATE SKIP LOCKED`). Introspective codegen that generates TypeScript entity stores from Python models via Jinja2. The Python→TS bridge is already solved.

Codegen-patterns (TS) is an untested sideproject. Building stack-bench on it would mean developing framework and product simultaneously.

### The TS backend was duplicating solved problems

The stack-bench TS app (Hono + Drizzle) recreated conversation/message/tool-call CRUD that pattern-stack's BaseService already provides. Adding Job/AgentRun models with state machines would mean rebuilding EventPattern in TS — reimplementing what exists and works in Python.

### Three languages regardless

Both options result in three languages: Go (CLI) + Python (agent runtime) + TS (frontend). The TS backend didn't eliminate Python — it just added a boundary between the app layer and agent runtime. Each language is now in its strongest domain:

- **Go** — single-binary CLI with best-in-class TUI rendering
- **Python** — agent orchestration, LLM tool use, backend API, pattern framework
- **TypeScript/React** — browser UI, Electric real-time sync

### No framework demonstration goal

One argument for TS was proving out EventPattern/ActorPattern concepts in TypeScript for future use at DealBrain. But stack-bench's backend is mostly thin CRUD and job dispatch — not complex enough to meaningfully exercise those patterns. DealBrain itself, with its full business domain, is a better proving ground if/when TS patterns are needed.

### If the agent runtime ever needs to be language-agnostic

It can sit behind a gateway API. Any TS, Go, or other client calls it over HTTP. This works whether the agent runtime is Python or anything else. The architecture doesn't change — just the deployment topology.

## Consequences

- **stack-bench TS backend removed:** `apps/api` entities and routes are deleted. The workbench React app (`apps/workbench`) remains and points at the Python API.
- **Pattern-stack codegen generates frontend stores:** Python model introspection → Jinja2 → TypeScript Electric collections + entity stores. No manual TS entity definitions needed.
- **Single backend process:** API + agent runtime + worker in one Python process initially. Split into separate services when scale requires it.
- **stack-bench becomes a monorepo for:** Go CLI (`packages/stack`), React workbench (`apps/workbench`), and any shared TS frontend utilities. The Python backend lives in `agentic-patterns` (or a dedicated `pattern-stack-app` repo).
