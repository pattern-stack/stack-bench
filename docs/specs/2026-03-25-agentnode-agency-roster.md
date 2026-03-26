---
title: "AgentNode, Agency & Roster — Reactive Multi-Agent Primitives"
date: 2026-03-25
status: draft
branch:
depends_on: [docs/specs/2026-03-14-agent-node-extraction.md]
adrs: []
repo: pattern-stack/agentic-patterns
epic: "#7"
issues: ["#8", "#9", "#10", "#11", "#12"]
---

# AgentNode, Agency & Roster

## Goal

Promote AgentNode from demo to framework primitive. Introduce Agency (packaged agent group with coordinator) and Roster (deployment manifest combining agencies). Together these form the reactive multi-agent execution model that powers stack-bench workspace agents.

This is the **framework layer** in agentic-patterns. Stack Bench EP-011 covers the **infrastructure layer** (Cloud Run, GCS). Integration point: Stack Bench's WorkspaceManager deploys rosters into workspaces via `sandbox-run --roster`.

## Domain Model

```
AgentNode (core/systems/core/)
  = Agent + Runner + SandboxEventBus + MessagingToolbox + Lifecycle
  Reactive: bus → queue → batch → runner.run() → tools → bus

Agency (core/atoms/datatypes/)
  = coordinator AgentSpec + specialist AgentSpec[] + TransportConfig
  Self-contained group — external access through coordinator only

Roster (core/atoms/datatypes/)
  = AgencyDeployment[] + inter-agency TransportConfig
  Deployment manifest — coordinators wire together for inter-agency comms

AgencyRuntime (core/systems/runtime/)
  = Agency → AgentNode[] with transport wiring + lifecycle management

RosterRuntime (core/systems/runtime/)
  = Roster → AgencyRuntime[] with coordinator cross-wiring
```

## Implementation Phases

| Phase | Issue | What | Depends On |
|-------|-------|------|------------|
| 1 | AP-001 (#8) | Promote AgentNode to framework | — |
| 2 | AP-002 (#9) | Agency & Roster atoms | — |
| 3 | AP-003 (#10) | AgencyRuntime | Phase 1, 2 |
| 4 | AP-004 (#11) | RosterRuntime | Phase 3 |
| 5 | AP-005 (#12) | sandbox-run entrypoint update | Phase 4 |

Phases 1 and 2 can run in parallel.

## Phase Details

### Phase 1: Promote AgentNode to framework (AP-001)

**Source:** `scripts/demo_multi_agent.py` lines 94–233 (~140 lines, proven with 4-agent LLM collaboration)

**Target:** `agentic_patterns/core/systems/core/agent_node.py`

**Extract as-is, then improve:**

1. Move to `core/systems/core/agent_node.py`
2. Proper typing — replace `Any` with `Agent`, `SandboxEventBus`, `AgentAddress`, `RunnerProtocol`, `MessagingToolbox`
3. Configurable timeouts — `idle_timeout`, `global_timeout`, `max_turns` as constructor params with defaults (10s, 120s, 20)
4. Lifecycle events — emit on bus: `node.started`, `node.stopped`, `node.message_received`, `node.response_sent`
5. Runner as param — accept any `RunnerProtocol`, not just `AgentRunner`
6. Bus ownership — each node creates/owns its own `SandboxEventBus` instance wired to a shared transport (one bus per agent = agent sovereignty; transport is shared across agency)
7. Export from `core/systems/core/__init__.py`; also export `SandboxEventBus`, `SandboxEvents`, `AgentAddress`

**Do NOT change:**
- Core architecture (bus → queue → worker → LLM → bus)
- Message batching behavior (drain queue with 0.1s window)
- Turn limit / timeout mechanics (startup vs idle distinction)
- The `inject()` method for seeding messages
- The `_should_handle()` filtering logic

**Key design — timeout model:**
- Startup phase (`turns_taken == 0`): wait up to `global_timeout` (120s). Other agents may be in long LLM calls.
- Active phase (`turns_taken > 0`): wait up to `idle_timeout` (10s). If no messages, conversation wound down.

**Key design — message batching:**
```
While you were working, 2 messages arrived:

[PM]: "The auth module needs OAuth2 support"
[Reviewer]: "Make sure to handle token refresh"
```

**Tests:**
- Unit: start/stop lifecycle, message routing, batching, timeout behavior
- Integration: 2-node communication (mirrors demo but as a test)
- Update `scripts/demo_multi_agent.py` to import from framework

**Files:**
- New: `agentic_patterns/core/systems/core/agent_node.py`
- Edit: `agentic_patterns/core/systems/core/__init__.py` (exports)
- Edit: `scripts/demo_multi_agent.py` (import from framework)
- New: `tests/core/systems/core/test_agent_node.py`

---

### Phase 2: Agency & Roster atoms (AP-002)

**Target:** `agentic_patterns/core/atoms/datatypes/agency.py` and `roster.py`

Both are frozen Pydantic models extending `AgenticModel` (the atoms base class).

#### Agency

```python
class AgentSpec(AgenticModel):
    """One agent within an agency."""
    role: str                              # "coder", "reviewer"
    agent_definition_id: str | None = None # reference to stored definition
    persona: Persona | None = None         # or inline definition
    judgment: Judgment | None = None
    model: str = "anthropic/claude-sonnet-4-20250514"
    max_turns: int = 10
    capabilities: list[str] = []           # capability names to attach
    is_coordinator: bool = False

class TransportConfig(AgenticModel):
    """How agents communicate."""
    type: str = "in_process"               # "in_process" | "nats"
    nats_url: str = "nats://localhost:4222"

class Agency(AgenticModel):
    """Self-contained group of agents with a coordinator."""
    name: str
    description: str = ""
    agents: list[AgentSpec]
    transport: TransportConfig = TransportConfig()
    env_vars: dict[str, str] = {}

    @property
    def coordinator(self) -> AgentSpec | None: ...
    @property
    def internal_agents(self) -> list[AgentSpec]: ...
    def to_prompt(self) -> str: ...
```

**Validation rules:**
- Exactly one agent with `is_coordinator=True` per agency
- Agent roles unique within agency

#### Roster

```python
class AgencyDeployment(AgenticModel):
    """How to deploy one agency within a roster."""
    agency: Agency
    isolated: bool = False              # each agent gets own container
    resource_profile: str = "standard"  # light | standard | heavy

class Roster(AgenticModel):
    """Deployment manifest combining agencies."""
    name: str
    agencies: list[AgencyDeployment]
    workspace_id: str | None = None
    inter_agency_transport: TransportConfig = TransportConfig(type="nats")

    @property
    def all_agents(self) -> list[AgentSpec]: ...
    @property
    def coordinators(self) -> list[AgentSpec]: ...
    def to_prompt(self) -> str: ...
```

**Validation rules:**
- Agency names unique within roster

#### TOML Serialization

Agencies and Rosters load from TOML for the `sandbox-run` entrypoint:

```toml
# coding-agency.toml
name = "coding-agency"
description = "Code implementation and review"

[transport]
type = "in_process"

[[agents]]
role = "coordinator"
is_coordinator = true
model = "anthropic/claude-sonnet-4-20250514"
max_turns = 15

[[agents]]
role = "coder"
model = "anthropic/claude-sonnet-4-20250514"
max_turns = 10
```

```toml
# full-team.roster.toml
name = "full-dev-team"

[inter_agency_transport]
type = "nats"
nats_url = "nats://nats.internal:4222"

[[agencies]]
resource_profile = "standard"
agency = "coding-agency.toml"
```

**Files:**
- New: `agentic_patterns/core/atoms/datatypes/agency.py`
- New: `agentic_patterns/core/atoms/datatypes/roster.py`
- Edit: `agentic_patterns/core/atoms/datatypes/__init__.py`
- New: `agentic_patterns/core/atoms/loaders/toml_loader.py`
- New: `tests/core/atoms/datatypes/test_agency.py`
- New: `tests/core/atoms/datatypes/test_roster.py`

---

### Phase 3: AgencyRuntime (AP-003)

**Target:** `agentic_patterns/core/systems/runtime/agency_runtime.py`

Takes an `Agency` atom and produces a running system of `AgentNode` instances.

**Core responsibilities:**
1. Create transport from `TransportConfig` (InProcess or NATS)
2. Build `AgentNode` per `AgentSpec` — resolve agent definitions, create bus + address + toolbox
3. Start all nodes (subscribe to bus, spawn workers)
4. Coordinator routing: special subscriptions for inter-agency messages
5. Health monitoring: track node liveness, detect crashes
6. Lifecycle events: `AgentJoinEvent`/`AgentLeaveEvent` per node

**Key API:**
```python
class AgencyRuntime:
    async def start(self) -> None
    async def stop(self) -> None
    async def inject(self, role: str, content: str) -> None
    async def inject_coordinator(self, content: str) -> None
    @property
    def coordinator_address(self) -> AgentAddress | None
    def status(self) -> dict[str, str]  # role → state
```

**Agent building per AgentSpec:**
1. Resolve agent definition (from `agent_definition_id` or inline `persona`/`judgment`)
2. Create `AgentAddress` with agency context
3. Create `SandboxEventBus` with shared transport
4. Create `MessagingToolbox` with agency-scoped roster
5. Build `AgentNode` with all wiring

**Bus subject hierarchy:**
```
agency.{agency_id}.run.{run_id}.agent.{agent_id}   # Direct to agent
agency.{agency_id}.run.{run_id}._broadcast          # Broadcast within agency
roster.{roster_id}.agency.{agency_id}               # Inter-agency (coordinator only)
```

**Files:**
- New: `agentic_patterns/core/systems/runtime/__init__.py`
- New: `agentic_patterns/core/systems/runtime/agency_runtime.py`
- New: `tests/core/systems/runtime/test_agency_runtime.py`

---

### Phase 4: RosterRuntime (AP-004)

**Target:** `agentic_patterns/core/systems/runtime/roster_runtime.py`

Deploys multiple `AgencyRuntime` instances and wires their coordinators together.

**Core responsibilities:**
1. Create inter-agency transport from `Roster.inter_agency_transport`
2. Start each `AgencyRuntime`
3. Wire coordinators — inject roster context (available agencies), subscribe to cross-agency subjects
4. `run_to_completion()` — wait for all nodes to idle or timeout

**Key API:**
```python
class RosterRuntime:
    async def start(self) -> None
    async def stop(self) -> None
    async def inject(self, agency_name: str, content: str) -> None
    async def inject_all(self, content: str) -> None
    async def run_to_completion(self, timeout: float = 300) -> RosterResult
```

**Coordinator discovery (distributed mode):**
- Each coordinator publishes to `roster.{roster_id}.directory`
- `CoordinatorJoinEvent(agency_name, address)` for discovery
- In-process: direct wiring (shared transport). Distributed: NATS subjects.

**This issue covers in-process deployment only.** Distributed deployment (separate Cloud Run jobs per agency) lives in stack-bench WorkspaceManager.

**Files:**
- New: `agentic_patterns/core/systems/runtime/roster_runtime.py`
- New: `agentic_patterns/core/systems/runtime/roster_result.py`
- New: `tests/core/systems/runtime/test_roster_runtime.py`

---

### Phase 5: sandbox-run entrypoint update (AP-005)

**Target:** `pattern_stack/sandbox/entrypoint.py`

Three execution modes:

```bash
# Mode 1: Single agent (existing — unchanged)
sandbox-run --role coder --task "fix the auth bug"

# Mode 2: Single agency (new)
sandbox-run --agency coding-agency.toml --task "implement the login feature"

# Mode 3: Roster of agencies (new)
sandbox-run --roster full-team.roster.toml --task "build the deployment API"
```

**Changes:**
- Add `--agency` and `--roster` CLI arguments (mutually exclusive with `--role`)
- TOML loading for Agency and Roster configs
- Agency mode: create `AgencyRuntime`, inject task to coordinator, wait for completion
- Roster mode: create `RosterRuntime`, inject task to all coordinators, wait for completion
- Real-time output: print agent turns as they happen
- Transcript summary on completion (turns per agent, total tokens)
- Transport override via `--transport` flag
- Environment variable fallbacks: `SANDBOX_AGENCY`, `SANDBOX_ROSTER`

**Example TOML files:**
- New: `examples/agencies/coding-agency.toml`
- New: `examples/agencies/pm-agency.toml`
- New: `examples/agencies/full-team.roster.toml`

**Files:**
- Edit: `pattern_stack/sandbox/entrypoint.py`
- New: `examples/agencies/*.toml`
- New: `tests/sandbox/test_entrypoint_modes.py`

## Deployment Flexibility Matrix

Same Agency definition deploys multiple ways — only transport constructor changes:

| Scenario | Cloud Run | Transport |
|----------|-----------|-----------|
| Solo agency, co-located | 1 job, N AgentNodes | InProcess |
| Solo agency, isolated | N jobs, 1 AgentNode each | NATS |
| Roster of 3 agencies | 3 jobs (1 per agency) | InProcess within, NATS between |
| Roster, fully isolated | N jobs (1 per agent) | All NATS |

## Open Questions

1. **Agent definition resolution in AgencyRuntime** — `AgentSpec.agent_definition_id` references stored definitions. Should the runtime resolve from a database/registry, or require all definitions inline for MVP? Recommendation: inline-only for MVP, registry lookup in a follow-up.

2. **TOML agency references in rosters** — `agency = "coding-agency.toml"` requires resolving file paths. Should we support inline agency definitions in roster TOML too? Recommendation: both — file reference and inline.

3. **RosterResult aggregation** — what does the aggregated result look like? Per-agency results? Per-agent transcripts? Recommendation: per-agency with optional per-agent drill-down.

## References

- Prior spec: `docs/specs/2026-03-14-agent-node-extraction.md`
- Demo: `agentic-patterns/scripts/demo_multi_agent.py`
- AgentNode concept: `agentic-patterns/docs/concepts/agent-nodes.md`
- Agency concept: `agentic-patterns/docs/concepts/agencies.md`
- Sandbox architecture: `agentic-patterns/docs/sandbox-architecture.md`
- GCP sandbox provider: agentic-patterns PR #6
