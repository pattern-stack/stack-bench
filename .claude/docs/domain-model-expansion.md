# Domain Model Expansion — DRAFT

> **This is a working draft for context, not a finalized design.** The entity models, field choices, pattern assignments (EventPattern vs CatalogPattern etc.), and relationship structures below are preliminary — intended to capture the landscape and existing assets so a planning agent can refine the specifics. Don't treat any model definition here as decided.

> Expanding the domain model to support the full vision: conversations, tasks, stacks, reviews, and project management. All models live in the Python backend (pattern-stack). This doc maps what exists, what's new, and how they connect.

## What Already Exists (Python)

### Conversation Domain (agentic_patterns)
- **Conversation** — branching conversation model (role, model, state, exchange_count, tokens, branched_from)
- **Message** — request/response with sequence ordering, run_id for traces
- **MessagePart** — structured content (text, tool_call, etc.)
- **ToolCall** — execution tracking (state machine: pending → completed/failed)

### Agent Domain (agentic_patterns)
- **RoleTemplate** — reusable identity: persona (JSON), judgments, responsibilities, default_model, archetype, source ("library" | "custom"). The "class" of an agent.
- **AgentDefinition** — configured instance: points to a RoleTemplate + mission_objective, mission_constraints, mission_success_criteria, background (JSON), awareness (JSON), model_override. The "configured instance."
- **AgentAssembler** — runtime bridge: loads AgentDefinition from DB → hydrates core atoms (Persona, Mission, Judgment, Background, Awareness) → builds Agent via builder pattern. Capabilities injected at runtime, not stored.
- The old in-memory `AgentRegistry` (name→factory dict) is deprecated in favor of this DB-backed system.

**Location note:** These currently live in `agentic_patterns/app/features/agents/` and `app/features/roles/` — app-level directory, but the code is framework-quality (generic, not SDLC-specific). Intent is to push the machinery (models, assembler, services) down into the framework (`pattern_stack` or `agentic_patterns/core/`) and keep only the specific agent seed data (the 5 SDLC roles/definitions) at the app level. Same pattern as job queue: `DatabaseBackend`/`Worker` = framework, `handle_develop_run` = app.

### Job/Execution Domain (pattern-stack-app)
- **Job(EventPattern)** — state machine (queued → running → gated → complete/failed/cancelled), artifacts, gate_decisions
- **AgentRun(EventPattern)** — per-phase execution record (tokens, duration, attempt)

### Task Protocol (agentic_patterns)
- **Task** — canonical abstraction with WorkPhase (planning/implementation), StatusCategory (todo/in_progress/in_review/done/cancelled), IssueType, Priority
- **TaskProtocol** — CRUD + relations + phase advancement
- **LinearAdapter** — full implementation with status mapping, GraphQL, caching

### Events (agentic_patterns)
- **AgentEvent** hierarchy — message, tool, iteration, LLM, error events with OTEL trace IDs

---

## Proposed Domain Expansion

### 1. Task Management (Local-First)

The canonical Task protocol already exists. What's needed is a **local backend** that implements TaskProtocol — storing tasks in Postgres before (optionally) syncing to GitHub Issues or Linear.

```
┌──────────────────────────────────────────┐
│              TaskProtocol                │
│  create, get, update, list, delete       │
│  advance_phase, add_relation             │
├──────────────┬───────────┬───────────────┤
│ LocalAdapter │ Linear    │ GitHubAdapter │
│ (Postgres)   │ Adapter   │ (new)         │
│              │ (exists)  │               │
└──────────────┴───────────┴───────────────┘
```

**New model: Task(EventPattern)**

Mirrors the canonical Task atom but as a persistent EventPattern:

```
Task
├── title, description, body
├── issue_type: epic | story | task | bug | subtask
├── priority: urgent | high | medium | low | none
├── work_phase: planning | implementation
├── status_category: todo | in_progress | in_review | done | cancelled
├── assignee_id (nullable)
├── project_id → Project (nullable)
├── parent_id → Task (nullable, self-ref for epic→story→task)
├── tags: string[]
│
├── States: draft → open → in_progress → in_review → done / cancelled
│
├── External sync fields:
│   ├── external_id (nullable) — GH issue number or Linear ID
│   ├── external_source: "local" | "github" | "linear"
│   ├── external_url (nullable)
│   └── sync_state: "local" | "synced" | "stale" | "conflict"
│
└── Relationships:
    ├── has_many TaskRelation (blocks, relates_to, parent_of, duplicates)
    ├── belongs_to Project
    ├── has_many Job (agent executions against this task)
    └── has_many Conversation (agent conversations about this task)
```

**Why local-first**: You want to create and manage tasks without requiring GH/Linear connectivity. The sync fields let you push/pull when ready. The existing Linear adapter and a new GitHub adapter would sync via the same TaskProtocol interface.

### 2. Project Management

Light model to group tasks and provide context for agents.

```
Project
├── name, slug, description
├── repo_url (nullable — not all projects are single-repo)
├── default_branch: string
│
├── States: active → archived
│
└── Relationships:
    ├── has_many Task
    ├── has_many Stack
    └── has_many Conversation
```

**Not trying to replicate GitHub Projects.** This is a lightweight local grouping so agents know which repo/context they're operating in.

### 3. Stack Management (PR Stacking)

The stack CLI currently stores state in `~/.claude/stacks/{repo}.json`. The domain model brings this into Postgres so it's queryable, observable, and connected to tasks/conversations.

```
Stack
├── name: string (e.g., "frozen-column")
├── trunk: string (e.g., "main")
├── project_id → Project
│
├── States: active → merged → abandoned
│
└── Relationships:
    ├── belongs_to Project
    └── has_many StackBranch (ordered)

StackBranch
├── stack_id → Stack
├── position: integer (order in stack)
├── branch_name: string
├── tip_sha: string (nullable)
├── pr_number: integer (nullable)
├── pr_state: open | closed | merged | null
│
└── Relationships:
    ├── belongs_to Stack
    ├── has_one Review (local review, nullable)
    └── has_many Task (tasks implemented on this branch)
```

**Migration path**: Stack CLI keeps working against JSON files. A `stack sync-db` command (or background process) mirrors state to Postgres. Eventually the CLI reads from DB directly.

### 4. Local Review (Pre-GitHub)

This is the interesting one. The insight: **review locally before pushing to GitHub**. The model mirrors GitHub's PR review structure but lives locally.

```
Review
├── stack_branch_id → StackBranch
├── status: draft | in_progress | approved | changes_requested
├── reviewer: string (could be agent or human)
│
├── States: draft → in_progress → approved / changes_requested
│
└── Relationships:
    ├── belongs_to StackBranch
    ├── has_many ReviewThread
    └── has_many ReviewComment (top-level, non-threaded)

ReviewThread
├── review_id → Review
├── file_path: string
├── diff_hunk: string (nullable)
├── line_start: integer (nullable)
├── line_end: integer (nullable)
├── resolved: boolean
│
└── Relationships:
    ├── belongs_to Review
    └── has_many ReviewComment

ReviewComment
├── review_id → Review (nullable — top-level)
├── thread_id → ReviewThread (nullable — threaded)
├── author: string
├── body: string
├── author_type: "human" | "agent"
├── conversation_id → Conversation (nullable — if agent-generated, link to the conversation)
│
└── Relationships:
    ├── belongs_to Review
    ├── belongs_to ReviewThread (optional)
    └── belongs_to Conversation (optional)
```

**How this works in practice:**

1. You implement on a stack branch
2. Before `stack submit`, you run a local review (agent or self)
3. Agent reads the diff, creates ReviewThreads with file-specific comments
4. You address feedback, resolve threads
5. When Review is `approved`, `stack submit` pushes + creates GH PR
6. GH review comments can be pulled back into the local model (future)

**The routing question you raised**: It's not extended models or different routing — it's the **same model** used at two stages. A Review can be `source: "local"` (pre-push) or `source: "github"` (post-push). The entity structure is identical. What differs is:
- Local reviews: created by agents/you, stored in Postgres, pre-push
- GitHub reviews: pulled from GH API, stored in same tables, post-push
- Both rendered the same way in the workbench UI

### 5. Agent Domain (Existing — Wire In)

The agent registry already exists in agentic-patterns as DB-backed models. No new models needed — we wire the existing ones into the domain graph.

**RoleTemplate** and **AgentDefinition** are already persistent. What changes:

```
AgentRun (existing, updated)
├── ... existing fields ...
├── agent_definition_id → AgentDefinition (nullable — links to the agent that ran)
│   (runner_type stays as a denormalized convenience field)
```

```
ReviewComment (new, see section 4)
├── ... fields ...
├── agent_definition_id → AgentDefinition (nullable — which agent authored this)
```

```
Conversation (existing, updated)
├── ... existing fields ...
├── agent_definition_id → AgentDefinition (nullable — agent in the conversation)
```

**Pre-shipped agents**: The existing coding roles (understander, planner, specifier, implementer, validator) ship as seed data — RoleTemplate + AgentDefinition rows inserted on first migration. Custom agents can be added via API or CLI.

### 6. Connecting the Domains

```
Project ──────────────────────────────────────────────────
   │                                                      │
   ├── has_many Task                                      │
   │     ├── has_many Job (agent executions)               │
   │     ├── has_many Conversation (agent chats)           │
   │     └── belongs_to StackBranch (implementation)       │
   │                                                      │
   ├── has_many Stack                                     │
   │     └── has_many StackBranch                         │
   │           ├── has_one Review                         │
   │           │     └── has_many ReviewThread/Comment     │
   │           └── has_many Task                          │
   │                                                      │
   └── has_many Conversation (project-level)              │
──────────────────────────────────────────────────────────

AgentDefinition → AgentRun (which agent executed)
AgentDefinition → Conversation (which agent is responding)
AgentDefinition → ReviewComment (which agent authored)
Conversation ←→ Task (agent works on task)
Conversation ←→ ReviewComment (agent generated review)
Job ←→ Task (agent execution for task)
Job ←→ AgentRun (per-phase execution)
RoleTemplate → AgentDefinition (role defines the agent)
```

### 7. Job Model Update

The existing Job model is tightly coupled to the 5-phase SDLC workflow. With tasks in the picture, we link them:

```
Job (existing, updated)
├── ... existing fields ...
├── task_id → Task (nullable — what task triggered this job)
├── stack_branch_id → StackBranch (nullable — where the work lands)
└── conversation_id → Conversation (nullable — the agent conversation)
```

---

## Entity Summary

| Entity | Pattern | Status | Notes |
|--------|---------|--------|-------|
| **Conversation Domain** | | | |
| Conversation | BasePattern | Exists | Add project_id, task_id, agent_definition_id FKs |
| Message | BasePattern | Exists | No changes |
| MessagePart | BasePattern | Exists | No changes |
| ToolCall | BasePattern | Exists | No changes |
| **Agent Domain** | | | |
| RoleTemplate | Base (UUIDMixin) | Exists | Persona, judgments, responsibilities. Pre-ship coding roles as seed data |
| AgentDefinition | Base (UUIDMixin) | Exists | Mission, background, awareness → RoleTemplate. Pre-ship 5 SDLC agents as seed data |
| **Execution Domain** | | | |
| Job | EventPattern | Exists | Add task_id, stack_branch_id, conversation_id |
| AgentRun | EventPattern | Exists | Add agent_definition_id FK |
| **Task Domain** | | | |
| **Project** | CatalogPattern | **New** | Lightweight grouping (repo, tasks, stacks) |
| **Task** | EventPattern | **New** | Local-first, sync to GH/Linear via TaskProtocol |
| **TaskRelation** | RelationalPattern | **New** | blocks, parent_of, relates_to, duplicates |
| **Stack Domain** | | | |
| **Stack** | EventPattern | **New** | Mirrors stack CLI state in Postgres |
| **StackBranch** | BasePattern | **New** | Ordered branches in stack |
| **Review Domain** | | | |
| **Review** | EventPattern | **New** | Local + GitHub reviews, same model both stages |
| **ReviewThread** | BasePattern | **New** | File-specific comment threads |
| **ReviewComment** | BasePattern | **New** | Comments with agent/human attribution, agent_definition_id FK |

**Total: 17 entities (9 existing, 8 new)**

Pre-shipped seed data:
- 5 RoleTemplates: understander, planner, specifier, implementer, validator
- 5 AgentDefinitions: one per role, configured for the SDLC workflow

## Open Questions

1. **GitHubAdapter for TaskProtocol** — Build now or defer? Linear exists, GH Issues is a simpler API. Could be quick.

2. **Stack CLI migration** — Keep JSON state as source of truth with DB as read replica? Or go DB-first and have the CLI read from Postgres?

3. **Review trigger** — Is local review manual (`stack review`) or automatic (agent reviews every branch before submit)?

4. **Conversation↔Task cardinality** — One conversation per task? Or many (each agent interaction is a separate conversation)? Leaning many — a task might have a planning conversation, then implementation, then review.

5. **Where do entities/ YAMLs go?** — They were deleted from stack-bench. Do we create them in the Python project for codegen to consume? Or is codegen only for the TS frontend stores?

6. **Agent seed data delivery** — Alembic data migration, or a `pts seed` CLI command, or both?
