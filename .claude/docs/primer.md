# Stack-Bench Platform Primer

> Use this document to bootstrap a new Claude Code session. It captures the full landscape, prior decisions, and the key question to resolve before building the MVP.

## What Is This

A personal dev tooling platform for orchestrating AI agents, managing conversations, and stacking PRs. Built by Dug, who also leads a 4-person eng team at work (dealbrain, TypeScript/React). The platform started in Python (agentic-patterns) and is being considered for a full or partial port to TypeScript.

## Origin Story

Late night session on 2026-03-13 (agentic-patterns session `bd8183e7`). Key discussion:

1. **Goal**: Build a conversation CLI for delegating tasks to agents (locally via worktrees, remotely via APIs)
2. **UX-first principle**: "I want to prioritize UX over anything else"
3. **Ink considered and challenged**: Claude Code uses Ink (React for CLI), but Dug noted visual bugs — Claude confirmed these are fundamental terminal/React mismatches (flickering, scroll clobbering)
4. **Hybrid pattern chosen**: CLI launches, browser renders (like `jupyter notebook`, `vite dev`)
5. **Monorepo scaffolded**: Bun + TypeScript + Hono + Vite + React → `stack-bench` repo
6. **Stack CLI included**: `dugshub/stacks` integrated as a package

**This was a late-night vibe session. The TypeScript decision needs revisiting with clear eyes.**

## The Decision To Make

**Keep Python backend (pattern-stack/FastAPI) or port to TypeScript?**

### Arguments for keeping Python

- **pattern-stack is done**: Full framework with BasePattern, EventPattern, Field system, state machines, EventBus, Gates, BaseService, HistoryCapability, job queues — all working
- **agentic-patterns is done**: 5-layer agent system (atoms→molecules→organisms→systems→workflows), DevelopOrchestrator with 5-phase SDLC, ClaudeCodeRunner, multi-agent teams, ~2400 LOC API layer with tests
- **Conversation API already exists**: FastAPI routers for conversations, agents, run — with persistence, event bus, gates
- **Zero porting effort**: Can use immediately
- **Python is native for AI/ML**: Better ecosystem for agent tooling

### Arguments for porting to TypeScript

- **Team alignment**: 4-person eng team at work uses TypeScript/React — porting shows them the pattern-stack dev style (Pattern class, EventPattern, etc.) in a language they know
- **Unified stack**: Frontend (React) + backend (Hono/Bun) + CLI all in one language, one runtime
- **Bun is fast**: No build step, runs .ts directly, faster startup than Python
- **Codegen already targets TS**: The codegen package generates NestJS/Drizzle/React code — eating your own dogfood
- **Electric SQL synergy**: If you go full TypeScript + Drizzle + Electric, the real-time sync story is much cleaner
- **Simpler deployment**: Single runtime, no Python virtualenvs

### Hybrid option

- Keep agentic-patterns (Python) as the agent execution engine
- Use stack-bench (TypeScript) for the conversation UI, API layer, and CLI
- Connect via HTTP/events — Python runs agents, TS handles UX

## What Already Exists

### stack-bench (TypeScript — this repo)

```
apps/api/          Hono REST API (conversations, messages, tool-calls). Drizzle + PostgreSQL.
apps/workbench/    React 19 + Vite frontend (dark theme scaffold, port 3200)
packages/codegen/  YAML entity → full-stack code generation (parser → analyzer → Hygen templates)
packages/stack/    Git stacking CLI (Clipanion). create/status/nav/push/submit/restack/sync.
entities/          conversation.yaml, message.yaml, tool_call.yaml
```

**API status**: Routes for CRUD conversations/messages exist. BaseService pattern. No auth, no agents, no events yet.

**Stack CLI status**: Fully functional. Branch naming (`user/stack/index-desc`), PR lifecycle, restack with conflict handling, sync with merge detection.

**Codegen status**: Full pipeline. YAML → parse → analyze → generate. Supports NestJS/Drizzle/React targets. Scanner auto-detects project architecture. 40+ CLI commands.

### agentic-patterns (Python)

```
core/atoms/        Frozen Pydantic models (Persona, Mission, Judgment, etc.)
core/molecules/    Toolboxes (protocol introspection → LLM tools + MCP + CLI)
core/organisms/    RoleBuilder, AgentBuilder
core/systems/      Runners, AgentEventBus, Gates (safety/rate-limit/approval/audit), Exporters
core/workflows/    Sequential, Parallel, TaskLoop orchestration
core/rendering/    PromptRenderer (section-based composition)
```

**Key infrastructure**:
- `AgentEventBus` with gate chain (SAFETY → RATE_LIMIT → APPROVAL → AUDIT)
- Event hierarchy: message, tool, iteration, LLM, error events — each with `as_ux()` and `as_span()`
- `DevelopOrchestrator`: 5-phase SDLC (understand → plan → spec → implement → validate) with human gates
- Session persistence (YAML for CLI, DB for API)
- Runner pool: ClaudeCodeRunner (has file/bash) vs ClaudeAPIRunner (reasoning only)

### pattern-stack (Python framework, in backend-patterns)

```
atoms/patterns/    BasePattern, EventPattern (state machines, Field system, auto-audit)
atoms/shared/      EventStore, EventBus, EventSystem (3-layer events)
atoms/capabilities/ HistoryCapability, SyncCapability, IntegrationCapability
atoms/data/        SQLAlchemy async, UUIDMixin, session management
atoms/jobs/        Database-backed job queue with Worker
```

**What would need porting**:
1. BasePattern → TypeScript class with Drizzle (already have base-schema.ts as a start)
2. EventPattern → State machine + Field system (Zod replaces Pydantic)
3. EventBus → Could use EventEmitter or custom pub/sub
4. Gate chain → Middleware pattern (Hono has this natively)
5. HistoryCapability → Drizzle hooks or triggers
6. BaseService → Already have base-service.ts as a start
7. Protocol/ABC introspection → Decorator-based metadata (harder in TS, but doable)

## What To Build For MVP

Regardless of language choice, the MVP is:

1. **Conversation CLI** — Start a conversation, send messages, see streaming responses
2. **Agent execution** — At minimum, wrap Claude API calls with tool use
3. **Conversation persistence** — Save/resume conversations (the API layer)
4. **Workbench UI** — Browser-based conversation viewer (launched from CLI)

The Stack CLI and Codegen are done — they're tools, not the product.

## Dev Commands

```bash
bun install                                    # install all deps
bun --filter @stack-bench/api dev              # API on :3100
bun --filter @stack-bench/workbench dev        # Workbench on :3200
bun run packages/stack/src/cli.ts <command>    # Stack CLI
bun run packages/codegen/cli.ts <command>      # Codegen CLI
```

## Current Branch

`dugshub/conversation-cli/1-ink-scaffold` — first branch in the `conversation-cli` stack. No PR yet.
