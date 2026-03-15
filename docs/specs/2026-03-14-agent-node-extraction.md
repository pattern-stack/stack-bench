---
title: AgentNode Extraction — Promote demo pattern to framework primitive
date: 2026-03-14
status: draft
branch:
depends_on: [docs/specs/2026-03-14-conversation-runtime.md]
adrs: [003, 004]
---

# AgentNode Extraction

## Goal

Promote the `AgentNode` pattern from `agentic-patterns/scripts/demo_multi_agent.py` into a first-class framework primitive. AgentNode is the missing piece between the existing multi-agent infrastructure (SandboxEventBus, Transport, MessagingToolbox) and the stack-bench runtime (ConversationRunner, coordinator/listener/specialist agents). The infrastructure is production-ready; the integration pattern is demo code.

## Current State

### In framework (`agentic_patterns/core/systems/`)

| Component | Location | Status | Exported |
|-----------|----------|--------|----------|
| SandboxEventBus | `core/sandbox_event_bus.py` | Production | No (in framework, not in `__all__`) |
| SandboxEvents | `core/sandbox_events.py` | Production | No |
| AgentAddress | `core/sandbox_events.py` | Production | No |
| Transport (protocol) | `transport/protocol.py` | Production | Yes |
| InProcessTransport | `transport/in_process.py` | Production | Yes |
| NATSTransport | `transport/nats_transport.py` | Production | Yes |
| MessagingToolbox | `transport/messaging_toolbox.py` | Production | Yes |

### In demo only (`scripts/demo_multi_agent.py`)

| Component | Lines | What It Does |
|-----------|-------|-------------|
| AgentNode | 91-233 | Event-driven agent wrapper: Bus → Queue → Worker → LLM → Tools → Bus |

### What AgentNode does (from the demo)

```python
@dataclass
class AgentNode:
    agent: Agent
    bus: SandboxEventBus
    address: AgentAddress
    runner: BaseRunner
    tool_executor: ToolExecutor

    # Internal state
    _queue: asyncio.Queue       # incoming messages
    _worker: asyncio.Task       # async processing loop
    _history: list              # conversation continuity
    _turn_count: int            # turn limiting
    _max_turns: int
    _idle_timeout: float
    _global_timeout: float
```

**Lifecycle**: `start()` → subscribes to bus, spawns worker → `inject()` seeds initial messages → worker drains queue, calls LLM, executes tools, publishes responses → `stop()` cancels worker

**Key behaviors:**
- Subscribes to both direct messages and broadcasts on the SandboxEventBus
- Maintains conversation history across turns for continuity
- Batches queued messages before LLM call (doesn't call per-message)
- Configurable turn limits and timeouts (idle + global)
- Uses MessagingToolbox for agent-to-agent communication as LLM tools

## What Needs to Happen

### Phase 1: Promote AgentNode to framework

Move AgentNode from `scripts/demo_multi_agent.py` into the framework proper:

**Target location**: `agentic_patterns/core/systems/core/agent_node.py`

**Changes from demo version:**
- Extract from demo script into standalone module
- Add to `__init__.py` exports (alongside SandboxEventBus, SandboxEvents)
- Also export SandboxEventBus and SandboxEvents (currently in framework but not in `__all__`)
- Add proper docstrings and type hints
- Make runner selection configurable (currently hardcoded in demo)
- Add event emission for node lifecycle (start, stop, message received, response sent)
- Add optional PersistenceExporter integration for automatic DB writes

**Do NOT change:**
- The core architecture (bus → queue → worker → LLM → bus)
- The message batching behavior
- The turn limit / timeout mechanics
- The AgentAddress addressing scheme

### Phase 2: AgentNode variants for stack-bench roles

Three node types needed for ADR-004's agent taxonomy:

**ConversationNode** (for interactive chat)
- Single agent, long-lived, user-facing
- Receives user messages via API, responds via SSE
- This is what ConversationRunner (from conversation-runtime spec) wraps
- History persisted to Conversation/Message/MessagePart tables

**ListenerNode** (for terminal observation)
- Passive mode — accumulates context but doesn't generate output
- Subscribes to terminal event subjects on the bus
- Two-tier detection: heuristic (instant) then LLM (async)
- Emits knock events when triggered
- Lightweight — no full LLM call unless tier 2 confirms

**OrchestratorNode** (for multi-phase pipelines)
- Manages a sequence of agents (architect → reviewer → builder → validator)
- Creates child AgentNodes per phase, routes artifacts between them
- Gate integration for human approval between phases
- Maps to DevelopOrchestrator but using AgentNode infrastructure
- This replaces the existing DevelopOrchestrator with a node-based approach

### Phase 3: Wire into stack-bench

**ConversationRunner** (from conversation-runtime spec) becomes:
1. Create a ConversationNode from the agent config
2. Attach PersistenceExporter for DB writes
3. Inject user message
4. Yield events as SSE

**Coordinator ("sb")** becomes:
1. A long-lived ConversationNode with project-scoped awareness
2. Subscribed to all listener knock events
3. Routes to specialist nodes when needed
4. Persists as a single Conversation across the TUI session

**Listener agents** become:
1. ListenerNodes attached to terminal contexts
2. Subscribed to terminal event subjects: `terminal.{context_id}.output`
3. Knock = publish `AgentMessageEvent` to coordinator's subject

## Domain Model

```
AgentNode (framework primitive)
├── ConversationNode              ← interactive chat, user-facing
│   └── wraps: Agent + Runner + Bus + PersistenceExporter
├── ListenerNode                  ← passive observation, knock-capable
│   └── wraps: Agent + Bus + detection heuristics
└── OrchestratorNode              ← multi-phase pipeline
    └── wraps: Agent + Bus + child AgentNodes + gates

Communication:
AgentNode ──publish──→ SandboxEventBus ──subscribe──→ AgentNode
                            │
                      Transport layer
                      (InProcess or NATS)
```

## Key Design Decisions

### Why AgentNode and not just "call the runner"?

The runner (AgentRunner, ClaudeCodeRunner) handles one LLM interaction: prompt in, response out, tool loop. AgentNode adds:
- **Identity** — addressed by AgentAddress, discoverable via `list_team()`
- **Communication** — can send/receive messages to/from other agents
- **Continuity** — maintains conversation history across turns
- **Lifecycle** — start/stop, turn limits, timeouts
- **Queuing** — decouples message receipt from processing

For a single chat, a runner suffices. For multi-agent (coordinator + listeners + specialists), you need nodes.

### InProcess vs NATS for MVP?

InProcessTransport. Single process, zero dependencies. NATS when we need distributed agents (multiple worktrees, remote execution).

### Where does AgentNode live long-term?

In agentic-patterns framework (per ADR-003 boundary). It's a framework primitive, not platform-specific. Any app using agentic-patterns should be able to create agent nodes. The stack-bench-specific variants (ConversationNode, ListenerNode) live in the stack-bench backend molecules layer.

## Implementation Phases

| Phase | What | Where | Depends On |
|-------|------|-------|------------|
| 1 | Promote AgentNode to framework | agentic-patterns | — |
| 2 | Export SandboxEventBus + SandboxEvents | agentic-patterns | Phase 1 |
| 3 | ConversationNode variant | stack-bench backend | Phase 1 |
| 4 | Wire ConversationRunner to use ConversationNode | stack-bench backend | Phase 3 |
| 5 | ListenerNode variant | stack-bench backend | Phase 1 |
| 6 | OrchestratorNode variant | stack-bench backend | Phase 1 |

Phases 1-2 are agentic-patterns work. Phases 3-6 are stack-bench work. Phase 4 connects to the conversation-runtime spec.

## Resolved Decisions

These were open questions, now resolved after reviewing the progressive demo examples (`demo_tracing` → `test_sdk_bridge_e2e` → `demo_multi_agent` → `spanish_tutor`):

### 1. Compose, not subclass
AgentNode **composes** with Agent. Agent is a config object (role, mission, tools); AgentNode is a runtime wrapper (queue, worker, bus). Different lifecycles — same Agent config can run in multiple nodes. Confirmed by `demo_multi_agent.py` where `agent` is a field on the node.

### 2. Queue drain works naturally for all cases
The demo's batch behavior (drain queue with 0.1s window, single LLM call) handles both multi-agent and interactive chat without a flag. Single message in queue = single processing. No `batch_mode` config needed.

### 3. ListenerNode detection: regex rules, no LLM for MVP
Configurable `detection_rules: list[DetectionRule]` per listener where `DetectionRule = (pattern: regex, severity: str, context_lines: int)`. Examples:
- Test listener: `FAIL`, `Error`, non-zero exit codes, stack traces
- Build listener: `error:`, compilation failures
- Git listener: merge conflicts, push failures

Tier 2 (LLM-based filtering to reduce false positives) deferred until noise becomes a problem. MVP is regex → knock.

### 4. OrchestratorNode creates child nodes dynamically
The orchestrator holds `phase_config: list[PhaseSpec]` and creates child `AgentNode` instances per phase on demand, tears them down after. Sequential pipeline doesn't need idle nodes. Children inherit the orchestrator's bus for inter-phase communication. Contrast with `demo_multi_agent.py` which creates all nodes upfront — that's for flat swarms, not sequential pipelines.

### 5. Reconstruct-on-request for ConversationNode
No long-lived nodes for interactive chat. `POST /send` → create ConversationNode → load history from DB → process message → stream response → node dies. State lives in Postgres.

Long-lived nodes are reserved for multi-agent sessions (OrchestratorNode running a pipeline, ListenerNodes watching terminals). Those will need a `NodeManager` as `asyncio.Task` within a session scope — but not for Phase 1.

Validated by `spanish_tutor` example which creates agents on-demand per turn with no long-lived state.

### 6. ConversationNode reconstructs from DB between messages
Cost of rebuilding: one joined query (conversation + messages + parts) + rebuild message list + create runner. Milliseconds. Not worth holding a live process for hours between user messages.

## Design Note: Two Patterns, Not One

The demos reveal two distinct orchestration patterns we should support:

| Pattern | Example | Use In Stack Bench |
|---------|---------|-------------------|
| **Session Manager** | `spanish_tutor` — create agents on demand, sequential turns, structured output | ConversationNode (interactive chat) |
| **Agent Swarm** | `demo_multi_agent` — long-lived nodes, async queues, bus-driven communication | OrchestratorNode + ListenerNodes (multi-agent pipelines) |

ConversationNode is closer to the session manager pattern. AgentNode swarm is for when we wire up coordinator + listeners + specialists. Both patterns compose from the same primitives (Agent, Runner, Bus) but have different lifecycle semantics.

## References

- Demo implementation: `agentic-patterns/scripts/demo_multi_agent.py` (lines 91-233)
- Framework infrastructure: `agentic_patterns/core/systems/core/sandbox_event_bus.py`
- Framework events: `agentic_patterns/core/systems/core/sandbox_events.py`
- Transport: `agentic_patterns/core/systems/transport/`
- Conversation runtime spec: `docs/specs/2026-03-14-conversation-runtime.md`
- Terminal + agent ADR: `docs/adrs/004-terminal-agent-layer.md`
- Framework extraction ADR: `docs/adrs/003-agentic-patterns-extraction.md`
