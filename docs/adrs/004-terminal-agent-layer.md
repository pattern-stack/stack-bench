# ADR-004: Terminal + Agent Interaction Layer

**Date:** 2026-03-14
**Status:** Draft
**Deciders:** Dug

## Context

The Stack Bench TUI (Go/Bubble Tea) has three tabs: Stacks (git topology), Streams (agent execution), and Chat (conversation). The TUI shows WHAT agents are doing but not WHERE — there is no representation of the execution environment (worktrees, shells, file systems). The user cannot interact with agent environments, run commands, or observe live terminal output.

Additionally, the chat system uses a single "sb" persona with no defined identity. Agents in the Streams view (Architect, Builder, etc.) are isolated to their task sessions. There is no concept of agents that passively observe the user's work and proactively offer help.

No existing tool combines multiplexed contextual terminals with multi-agent AI observation:
- **tmux**: multiplexed terminals, no AI
- **Claude Code**: AI in terminal, single agent, no multiplexing, no dashboard
- **Cursor**: AI in editor, no terminal multiplexing, no agent diversity
- **Warp**: AI-augmented terminal, no project awareness, no agent orchestration

## Decision

Add a **Terminal Layer** to the TUI with an **Agent Observation Model**. The terminal is a layer (not a tab), agents passively observe terminals and proactively "knock" when they detect something relevant, and the user seamlessly switches between doing, watching, and directing.

### 1. Terminal as a Layer

The terminal is not a tab — it is a **slide-up panel** that coexists with the current view.

- `cmd+j` toggles the terminal (takes ~40% of screen, main view compresses above)
- `cmd+shift+j` **pins** the terminal — it stays visible when navigating away
- `cmd+tab` cycles between pinned terminals (max 4)
- Chat bar **moves with the terminal** — bound to environment, not view
- `!` drops to a full-screen shell via `tea.ExecProcess` (simple fallback)
- `o` opens the current file in the user's IDE (link-out, complementary)

Layout when terminal is visible:
```
┌──────────────────────────────────────────────────────────┐
│  Stacks   Streams   Chat                          tab bar│
├──────────────────────────────────────────────────────────┤
│              MAIN VIEW (compressed, ~60%)                │
├── terminal: session-mgmt/3-session-api ──── [ctx] ──────┤
│  $ just test -- -k test_session                          │
│  3 passed in 1.2s                              ~40%      │
│  $ _                                                     │
├──────────────────────────────────────────────────────────┤
│  *knock*  test-runner noticed a failure         knock    │
│   sb: those tests look clean                    chat     │
│  you: _                                                  │
├──────────────────────────────────────────────────────────┤
│  cmd+j:hide  cmd+shift+j:pin  /:chat           help     │
└──────────────────────────────────────────────────────────┘
```

### 2. Context Binding

Each view maps to a terminal environment:

| View | Terminal CWD | Shell | Notes |
|------|-------------|-------|-------|
| Stacks tab | Project root | User's shell | Current git branch |
| Streams L1 | Project root | User's shell | Same as Stacks |
| Streams L2 (task) | Task's worktree | User's shell | If worktree exists |
| Streams L3 (agent) | Task's worktree | **Read-only mirror** of agent's PTY | Shows live agent execution |

L3 is special: the terminal shows the agent's actual shell session. The user observes, not operates. `cmd+t` takes control (pauses the agent). `cmd+t` again releases.

Terminals are **created lazily**, persist in a pool (`map[terminalContext]*terminal`), and survive navigation. Background processes keep running. Scrollback is preserved.

### 3. Agent Taxonomy

Three agent roles, building on the existing backend infrastructure:

**Coordinator ("sb")**
- The main chat persona. Project-scoped. Always present.
- Knows about all stacks, tasks, agents, and terminal contexts.
- Routes to specialists when the user's intent implies a specific domain.
- Maps to a new `AgentDefinition` with archetype "Coordinator" and a long-lived `Conversation`.
- This is the existing "sb" in the chat bar, now with explicit identity and terminal awareness.

**Listener**
- Attached to every terminal. Passive by default. Accumulates context.
- Observes terminal output via command boundary detection (prompt hooks).
- For task terminals: the listener IS the phase agent (Builder watching its own terminal = no separate listener needed).
- For user terminals: a generic "Project Listener" agent.
- Listeners are client-side (Go process) for MVP — no backend persistence until a knock triggers an interaction.

**Specialist**
- Activated by a knock or summoned by the coordinator.
- NOT a new category — uses existing `RoleTemplate` + `AgentDefinition` entities.
- The coordinator routes: test failure → reviewer agent, build error → implementer, merge conflict → planner.
- Introduces itself in chat, acts in the terminal with approval, then dismisses.

Agent hierarchy:
```
Coordinator ("sb")                  ← project-wide, always present
├── Listener (stacks terminal)      ← project-level observer
├── Listener (SB-042 task)          ← IS the Builder agent in observation mode
├── Listener (SB-043 task)          ← IS the Implementer agent in observation mode
└── Specialist (activated)          ← test-runner, reviewer, git agent (temporary)
```

### 4. The Knock Protocol

```
Trigger → Detection → Classification → Knock → [Decay] → Ack → Introduction → Interaction → Dismissal
```

**Detection** is two-tier:
- Tier 1 (heuristic, instant): pattern match for `FAILED`, `CONFLICT`, non-zero exit codes, `error:` prefixes. Produces a candidate.
- Tier 2 (LLM, async): confirms relevance and composes the introduction. Runs after the knock indicator is already shown (so knock feels instant).

**Knock priority**: urgent (test failure, merge conflict) > notable (single failure, deprecation) > informational (context match, suggestion).

**Knock visual**: a single line between terminal and chat:
```
│  *knock*  test-runner wants to help with the test failure    │
```

**Acknowledgment**: Enter on knock line, or `ctrl+k` to cycle pending knocks.
**Dismissal**: Esc or `/dismiss`. Agent returns to listening. Won't re-knock for same trigger.
**Decay**: unacknowledged knocks dim after 60s, max 3 queued, oldest drops silently.

### 5. Three Interaction Modes

**Mode A — Direct terminal use**: User types commands. Listener observes silently. Zero AI interference.

**Mode B — Chat about terminal**: User types in chat bar (`/` to focus). Message automatically includes terminal context (last 5 commands + output, CWD, visible buffer). Coordinator responds with awareness: "The test failed because test_refresh expects 200 but refresh returns 201."

**Mode C — Agent-initiated**: Listener detects trigger → knocks → user acknowledges → specialist introduces itself → can write commands to terminal with approval.

Agent-written commands are visually distinguished:
```
│  $ sed -i 's/200/201/' tests/test_session_api.py  [test-runner]│
```

**Trust levels** (per-agent, per-session, not persisted):

| Level | Behavior | Examples |
|-------|----------|---------|
| Ask always | Agent proposes, user confirms | Default |
| Auto-read | Read-only commands auto-execute | `cat`, `ls`, `git status` |
| Auto-test | Test commands auto-execute | `pytest`, `just test` |
| Auto-all | Everything auto-executes | Explicit user escalation only |

### 6. Pinning and Portaling

When pinned (`cmd+shift+j`), a terminal stays visible across navigation:
- Terminal header shows pin tab strip: `[1: SB-042 task]  2: stacks`
- Chat follows the pinned terminal's context, not the main view's context
- This creates intentional split-brain: top shows one context, bottom shows another
- `cmd+tab` cycles pinned terminals
- `cmd+shift+j` again unpins

Portaled terminals are useful for: running a test suite while reviewing PRs, watching agent output while checking git topology, keeping a build terminal visible during any activity.

## Options Considered

### Option A: Terminal layer with agent observation — Selected
- Novel: ambient AI that raises its hand (the knock pattern)
- Seamless mode switching between doing, watching, and directing
- Terminal pinning creates multiplexed environment
- Chat bound to environment, not view
- Builds on existing backend agent infrastructure

### Option B: Link-out to IDE only
- Simple: press `o` to open file in VS Code/Cursor
- **Rejected as primary because:** Breaks flow. No agent observation. No terminal context. Kept as complementary feature.

### Option C: Embedded terminal without agent observation
- Standard terminal multiplexer (tmux-like)
- **Rejected because:** tmux already exists. The value is in the agent observation, not the terminal itself.

### Option D: Full IDE embed
- Be Cursor/VS Code inside the terminal
- **Rejected because:** Scope explosion. TUI is a dashboard and command center, not an editor.

## Consequences

### Technical

- **PTY management**: Requires `creack/pty` + `charmbracelet/x/vt` for embedded terminal emulation. Well-trodden but requires careful buffer management.
- **Command boundary detection**: Shell prompt hooks (`PROMPT_COMMAND` / `precmd`) signal command start/end to the observer. Works for 95% of cases.
- **Backend streaming**: Terminal events flow Go → HTTP → Python backend for listener classification. Knocks flow back via SSE.
- **Memory**: Each terminal = PTY process (~minimal) + scrollback buffer (~1MB) + listener context (~2K tokens). 25 terminals ≈ 25MB + 50K tokens. Manageable.

### Architectural

- **New agent lifecycle**: Listeners are long-running (session-scoped), unlike task agents (phase-scoped). Backend must support both.
- **Chat identity becomes multi-agent**: Chat messages now carry agent name. The coordinator yields chat to specialists and reclaims it.
- **Trust model is new surface area**: Agent command approval needs the Gate system (safety → rate-limit → approval → audit).

### Implementation Order

| Phase | What | Dependencies |
|-------|------|-------------|
| 1 | Terminal mechanics (slide-up, PTY, focus, cmd+j) | Go only |
| 2 | Context binding (terminal per view, CWD mapping) | Go only |
| 3 | Chat terminal context (include output in messages) | Go only |
| 4 | Pinning and portaling (cmd+shift+j, cmd+tab) | Go only |
| 5 | Terminal observer (command boundary, event emission) | Go + backend |
| 6 | Listener agent (trigger detection, knock generation) | Backend |
| 7 | Knock UI (knock line, ack, dismiss) | Go + backend |
| 8 | Agent introduction + command approval | Go + backend |
| 9 | L3 agent shell mirroring | Go + backend |

Phases 1–4 are pure Go/TUI — compelling standalone (contextual terminals with pinning). Phases 5–9 add the AI layer.

## Open Questions

- [ ] Can Bubble Tea embed a live PTY, or must we use `tea.ExecProcess`? (`charmbracelet/x/vt` suggests yes)
- [ ] How does L3 agent shell mirroring work? Backend captures ClaudeCodeRunner PTY and streams to TUI?
- [ ] What happens when the user takes control of an agent's terminal? Agent pauses — how does it resume cleanly?
- [ ] Should the Chat tab evolve into "conversation history" or be removed now that chat is everywhere?
- [ ] Per-user knock sensitivity calibration — how does the system learn what's worth knocking about?

## The One-Line Pitch

**Stack Bench: a multiplexed development environment where every terminal has an AI co-pilot that watches, listens, and knocks when it can help.**

## References

- TUI prototype: `cli/main.go`
- Domain model: `docs/specs/2026-03-14-domain-model.md`
- Streams drill-down: `docs/specs/2026-03-14-streams-drill-down.md`
- CLI framework: `docs/adrs/001-cli-framework.md`
- Agent infrastructure: `backend/features/agents/`, `backend/seeds/agents.yaml`
- Framework primitives: agentic-patterns (AgentBuilder, RoleBuilder, EventBus, Gates)
