---
title: Stack Bench Domain Model
date: 2026-03-14
status: draft
branch:
depends_on: []
adrs: [001, 002, 003]
---

# Stack Bench Domain Model

## Goal

Define the core domain entities, ownership hierarchy, lifecycles, and relationships across the Stack Bench platform. This model spans three codebases (Go CLI, Python backend, agentic-patterns framework) and must reconcile the TUI's display model with the backend's persistence model. Derived from the CLI TUI prototype and backend feature layer.

## Domain Hierarchy

```
User (implicit, single-user for MVP)
│
├── Project                              ← TUI only, no backend equivalent yet
│   ├── Stack                            ← TUI + stack CLI, no backend model
│   │   ├── Branch                       ← git + stack CLI
│   │   │   ├── Commit                   ← git
│   │   │   └── PR (implied)             ← GitHub, not modeled
│   │   └── deps → other Stacks          ← diamond dependencies
│   └── Timeline (day/totalDays)
│
├── TaskSession                          ← TUI: taskSession / Backend: Job
│   ├── Phase (pipeline stage)           ← TUI: taskPhase / Backend: Job.current_phase
│   ├── Agent (executor per phase)       ← TUI: taskAgent / Backend: AgentRun
│   │   ├── Message                      ← TUI: agentMsg / Backend: Message + MessagePart
│   │   │   └── ToolCall                 ← TUI: toolCall / Backend: ToolCall (EventPattern)
│   │   │       └── DiffLines            ← TUI only, derived from Edit tool results
│   │   └── FileDiff                     ← TUI only, aggregated from ToolCall results
│   └── Aggregate stats
│
├── Terminal                             ← NEW, not yet modeled
│   ├── Shell session (pty)
│   ├── WorkTree binding                 ← git worktree path
│   ├── ListenerAgent                    ← NEW agent type, observes terminal
│   └── Context binding (view → terminal mapping)
│
├── Chat                                 ← TUI: chatByContext / Backend: Conversation
│   ├── CoordinatorAgent ("sb")          ← NEW agent role, project-scoped
│   └── ChatMessage                      ← TUI: chatMsg / Backend: Message
│
└── Agent Infrastructure (backend)
    ├── RoleTemplate                     ← backend: seeds/agents.yaml
    ├── AgentDefinition                  ← backend: agent features
    └── Conversation                     ← backend: EventPattern
```

## Entity Catalog

### Project
- **Definition:** A named body of work spanning multiple days, grouping related stacks.
- **Owner:** User (implicit).
- **Lifecycle:** Created when work begins. Active while day < totalDays. Archives when all stacks merge.
- **Backend mapping:** None. The backend has no Project model. Open question whether this is a real persistent entity or a TUI display grouping.

### Stack
- **Definition:** A group of dependent branches delivering a feature. Named, colored, archivable.
- **Owner:** Project.
- **Lifecycle:** Active while branches remain unmerged. Archived once all branches merge (doneDay set). No explicit create event.
- **Backend mapping:** None. Stacks are a git/stack-CLI concept. State lives in `~/.claude/stacks/`.
- **Relationships:** Contains 1..N Branches. May depend on other Stacks (deps). Maps to the stack CLI's branch naming convention.

### Branch
- **Definition:** A single unit of work within a stack. 1:1 with a git branch and (eventually) a PR.
- **Owner:** Stack.
- **Lifecycle:** Queued → Active → Merged, with Blocked reachable from Active. Submit/publish sub-lifecycle.
- **State machine:**
  ```
  Queued ──[deps clear]──→ Active ──[work done]──→ Merged
                              │
                              └──[dep blocks]──→ Blocked ──[unblocked]──→ Active
  ```
- **Backend mapping:** None directly. Job has a `branch` field (string).

### TaskSession / Job
- **Definition:** An execution session where AI agents work on a task through a phased pipeline.
- **TUI representation:** `taskSession` — id, title, branch, loopName, phases, agents, stats.
- **Backend representation:** `Job` — EventPattern with states (queued/running/gated/complete/failed/cancelled), phases, gate_decisions, artifacts.
- **Lifecycle (backend):** Queued → Running → [Gated →] Complete | Failed | Cancelled.
- **TENSION:** TUI taskSession has no explicit state — derived from child phases/agents. Backend Job has a full state machine. These must be reconciled.
- **Relationships:** Contains Phases and Agents. References a Branch by string. The string reference is the only link between the Stacks and Streams hierarchies.

### Phase
- **Definition:** A named stage in a task's pipeline.
- **TUI:** `taskPhase` with name and status (done/active/waiting).
- **Backend:** `Job.current_phase` (string) + `AgentRun.phase` (string).
- **Lifecycle:** Waiting → Active → Done. Sequential.
- **TENSION:** Phase is a first-class entity in the TUI but just a string field in the backend.

### Agent (Task) / AgentRun
- **Definition:** An agent instance performing work within a task session.
- **TUI:** `taskAgent` — name, model, status, messages, files.
- **Backend:** `AgentRun` — EventPattern (pending/running/complete/failed), job_id, phase, model, tokens, duration.
- **Lifecycle:** Waiting → Active → Done.
- **TENSION:** TUI agent is 1:1 with phase (implicit, not enforced). Backend AgentRun is linked to Job by job_id but phase mapping is a string field.

### Message / MessagePart
- **TUI:** `agentMsg` with role ("thought"/"response") and content + tool calls inline.
- **Backend:** `Message` (BasePattern) + `MessagePart` (BasePattern) — structured content blocks (text, tool_use, tool_result).
- **The backend is richer:** MessagePart separates structured content; TUI flattens everything.

### ToolCall
- **TUI:** `toolCall` with kind (Read/Edit/Bash/Grep), target, result, duration, diffLines.
- **Backend:** `ToolCall` — EventPattern (pending/executed/failed) with tool_name, input, output, request/response part linkage.
- **The backend is richer:** EventPattern state machine, linked to MessageParts.

### Chat / Conversation
- **TUI:** `chatByContext` — map of view context → messages. "sb" is the AI persona.
- **Backend:** `Conversation` — EventPattern (created/active/completed/failed) per agent.
- **TENSION:** TUI chat is view-scoped (changes by tab). Backend conversation is agent-scoped. Neither is entity-scoped (which is the user's mental model — "I'm chatting about SB-042").

## Lifecycle Map

```
Project ─────────────────────────────────────────────────────────────►
  Stack ──────────────────────────────────────────► [archived]
    Branch ─── Queued ── Active ── Merged
                           │
                     TaskSession ── Phase1 ── Phase2 ── Phase3 ── [complete]
                                    Agent1    Agent2    Agent3
                                      │
                                    Messages + ToolCalls + FileDiffs
```

## Key Tensions

1. **Two disconnected trees.** Stacks (git topology) and Streams (agent execution) share only a branch name string. No navigable link, no foreign key, no shared parent.

2. **Chat is view-scoped, not entity-scoped.** Messages keyed by UI tab, not by what the user is discussing. Should be scoped to entities (task, agent, branch).

3. **TaskSession has no lifecycle state.** Backend Job has a state machine. TUI taskSession derives state from children. Must reconcile.

4. **Phase ↔ Agent is coincidental.** Fake data has 1:1 mapping. Nothing enforces it. The domain should define whether phases and agents are formally linked.

5. **"sb" is undefined.** The chat AI persona is not a modeled entity. It should be a CoordinatorAgent with explicit scope and capabilities.

6. **Project doesn't exist in backend.** Is it a real entity or a display grouping? Needs ADR.

## Open Questions

1. Does TaskSession belong to a Branch, or is it top-level with a branch reference?
2. Can multiple TaskSessions work on the same Branch simultaneously?
3. Where does gate approval surface in the TUI? Chat? Modal? Key binding?
4. Should LoopType ("/plan_w_team", "/develop") be a first-class entity defining phase templates?
5. How does the Go CLI discover task sessions? Poll REST API? SSE stream? WebSocket?
6. Is FileDiff a derived entity (from ToolCalls) or independently tracked?
