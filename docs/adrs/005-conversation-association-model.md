# ADR-005: Conversation Association Model

**Date:** 2026-04-05
**Status:** Accepted
**Deciders:** Doug, Claude

## Context

Stack Bench needs conversations at multiple levels of the product:

1. **Planning conversations** — Human + AI ideating on features, breaking work into epics/tasks. Connected to a project and external tools (Linear, Notion). The conversation *produces* tasks. No task exists yet when the conversation starts.

2. **Execution conversations** — Agent working on a task through sequential phases (architect → builder → validator). The conversation *consumes* a task. Human can interrupt or redirect.

3. **Review conversations** — Discussion about a stack/PR. Comments, approvals, change requests. The conversation *evaluates* code output.

The Conversation model already exists (`EventPattern` with state machine, agent_name, token tracking, `branched_from_id`). The question is how to link conversations to the entities they operate on — tasks, projects, epics, stacks, branches — without rigid foreign keys that break when new conversation types emerge.

A direct `task_id` FK on Conversation fails because:
- Planning conversations don't have a task (they create tasks)
- Review conversations relate to stacks, not tasks
- A planning conversation may produce multiple tasks
- A task may have multiple conversations (execution, then retry, then follow-up)

## Decision

**Use pattern-stack's `RelationalPattern` for polymorphic conversation-entity associations. Keep a single `Conversation` model — no polymorphic subclasses.**

### Association Model

`RelationalPattern` provides:
- `entity_a_type` / `entity_a_id` — one side of the relationship
- `entity_b_type` / `entity_b_id` — other side
- `relationship_type` — nature of the link
- `relationship_metadata` — arbitrary context (dict)
- `is_active`, `started_at`, `ended_at` — lifecycle
- Built-in queries: `get_relations_for_entity()`, `get_active_relations()`

### Relationship Types

| relationship_type | entity_a | entity_b | Meaning |
|---|---|---|---|
| `planning` | conversation | project | This conversation is a planning session for this project |
| `produced` | conversation | task | This planning conversation created this task |
| `produced` | conversation | epic | This planning conversation created this epic |
| `execution` | conversation | task | This conversation is the agent execution for this task |
| `execution` | conversation | job | This conversation is tied to this job run |
| `review` | conversation | stack | This conversation is a review of this stack |
| `review` | conversation | branch | This conversation is a review of this branch |

### Conversation Lifecycle

```
Planning conversation (project-level)
  RelationalPattern: conversation → project, type="planning"
  ↓ human + AI discuss, break down work
  ↓ "create tasks" action
  RelationalPattern: conversation → task_1, type="produced"
  RelationalPattern: conversation → task_2, type="produced"

Task execution conversation (task-level, separate from planning)
  RelationalPattern: conversation → task_1, type="execution"
  branched_from_id → planning conversation (lineage)
  ↓ architect → builder → validator (AgentRun phases on Job)
  ↓ produces code changes

Stack review conversation (stack-level, separate)
  RelationalPattern: conversation → stack, type="review"
```

### Key Design Decisions

1. **One Conversation model, not polymorphic subclasses.** Different conversation types share the same message schema (text, thinking, toolCall, error parts). Behavioral differences (available tools, UI rendering) are runtime/frontend concerns, not schema.

2. **`conversation_type` field on Conversation** — Added for quick filtering: `"planning"`, `"execution"`, `"review"`. This is denormalized from the relationship for convenience but the relationship is the source of truth.

3. **Phases are AgentRun records, not separate conversations.** Within a task execution, the architect → builder → validator phases are sequential agent runs on a Job. The conversation is a single thread showing all phases. Phase dividers in the UI are derived from AgentRun boundaries.

4. **No conversation hierarchy for orchestration.** The user doesn't need to see the orchestration tree. Planning generates tasks. Each task runs independently. Epic completion = all child tasks done (query on task states). The `branched_from_id` field tracks lineage without requiring a tree.

5. **Existing `project_id` FK stays** as a convenience shortcut for the common case. RelationalPattern handles the polymorphic cases.

## Options Considered

### Option A — RelationalPattern associations (Selected)
- Polymorphic links via existing pattern-stack infrastructure
- No schema changes to Conversation model (just add `conversation_type` field)
- Flexible: any entity can be linked to any conversation
- Queryable: "give me all execution conversations for this task"
- **Selected because:** Handles all three conversation types without schema rigidity. Uses existing framework patterns. Allows new relationship types without migrations.

### Option B — Direct FKs on Conversation (task_id, stack_id, epic_id)
- Simple, explicit
- **Rejected because:** Doesn't handle planning conversations (no task yet). Would need nullable FKs for every entity type. New entity types require migrations. A conversation linked to multiple tasks needs a join table anyway — which is just RelationalPattern with extra steps.

### Option C — Polymorphic Conversation subclasses (PlanningConversation, ExecutionConversation)
- Type-safe, separate tables per variant
- **Rejected because:** The core shape (messages + parts) is identical. Different behavior is a runtime concern. Adds table complexity and forces choosing a type at creation time, when conversations may evolve (a planning conversation that becomes a task kickoff).

## Consequences

**Easier:**
- Adding new conversation contexts (e.g., "onboarding conversation", "debugging conversation") requires no schema changes
- Querying "all conversations related to this project" works across types
- Planning → execution lineage is tracked via `branched_from_id` + `produced` relationships
- Frontend can render the same ChatMessageRow/ChatRoom for all conversation types

**Harder:**
- Querying requires joining through RelationalPattern instead of a direct FK
- Need to ensure consistency (e.g., a task should have exactly one active execution conversation)
- RelationalPattern entries need cleanup when entities are deleted
