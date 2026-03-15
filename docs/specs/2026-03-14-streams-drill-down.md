---
title: Streams View 3-Level Drill-Down
date: 2026-03-14
status: draft
branch: dugshub/sb-ep001/7-wire-and-run
depends_on: []
adrs: [ADR-001]
---

# Streams View 3-Level Drill-Down

**Date:** 2026-03-14
**File:** `cli/main.go` (single-file, hackathon style)

## Goal

Expand the Streams tab from a flat list of agent statuses into a 3-level drill-down that mirrors a live terminal session. Level 1 shows parallel task sessions with phase pipelines. Level 2 shows agent roster and file activity within a task. Level 3 shows an agent's message history, tool calls, and file diffs. All data is hardcoded fake data for demo purposes.

## Data Model (Go Types)

### Enums and Constants

```go
// Task loop types
type loopType int
const (
    loopPlanWithTeam loopType = iota  // /plan_w_team
    loopDevelop                       // /develop
)

// Phase status within a pipeline
type phaseStatus int
const (
    phaseDone phaseStatus = iota
    phaseActive
    phaseWaiting
)

// Agent status within a task
type agentStatus int
const (
    agentDone agentStatus = iota
    agentActive
    agentWaiting
)

// Tool call types
type toolKind int
const (
    toolRead toolKind = iota
    toolEdit
    toolBash
    toolGrep
)
```

### Core Types

```go
type toolCall struct {
    name     toolKind
    params   string    // e.g. "file_path: /src/api/session.go"
    result   string    // summary, not full output
    duration string    // e.g. "120ms"
}

type agentMessage struct {
    role    string    // "thought" or "response"
    content string
    tools   []toolCall
}

type fileDiff struct {
    path    string
    added   int
    removed int
    hunks   []string  // pre-formatted diff lines with +/- prefixes
}

type taskAgent struct {
    name     string       // e.g. "Architect", "Builder"
    status   agentStatus
    model    string       // e.g. "opus-4", "sonnet-4"
    tokens   string       // e.g. "4.2k"
    duration string
    messages []agentMessage
    files    []fileDiff
    summary  string       // one-line summary of work done
}

type taskPhase struct {
    name   string       // e.g. "architect", "review", "build", "validate"
    status phaseStatus
}

type taskSession struct {
    id       string       // e.g. "SB-042"
    title    string       // e.g. "Session API"
    loop     loopType
    branch   string       // e.g. "session-mgmt/3-session-api"
    phases   []taskPhase
    agents   []taskAgent
    files    []string     // all files touched across agents
    tokens   string       // aggregate
    elapsed  string       // total elapsed
}
```

### Model Additions

```go
type streamLevel int
const (
    levelOverview streamLevel = iota  // Level 1: task list
    levelTask                         // Level 2: task detail
    levelAgent                        // Level 3: agent detail
)

// New fields on model struct:
type model struct {
    // ... existing fields ...

    // Streams drill-down state
    streamLevel  streamLevel
    tasks        []taskSession
    taskCur      int    // cursor within task list (L1)
    agentCur     int    // cursor within agent list (L2)
    msgScroll    int    // scroll offset in message view (L3)
    agentPane    int    // 0=messages, 1=files (L3)
    toolExpanded int    // index of expanded tool call, -1=none (L3)
    diffExpanded int    // index of expanded diff, -1=none (L3)
}
```

## Navigation State Machine

```
  Level 1 (Overview)         Level 2 (Task)           Level 3 (Agent)
 ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
 │  Task list         │     │  Agent roster      │     │  Messages | Files │
 │  j/k = move cursor │────>│  j/k = move cursor │────>│  j/k = scroll     │
 │  enter = drill in  │enter│  enter = drill in  │enter│  tab = switch pane│
 │  q = quit          │     │  esc = back to L1  │     │  esc = back to L2 │
 │  1-9 = jump task   │     │  1-9 = jump agent  │     │  enter = expand   │
 └───────────────────┘     └───────────────────┘     │    tool/diff       │
                                                      └───────────────────┘
```

Transitions:
- `enter` at L1 sets `streamLevel = levelTask`, `agentCur = 0`
- `enter` at L2 sets `streamLevel = levelAgent`, `msgScroll = 0`, `agentPane = 0`
- `esc` at L2 sets `streamLevel = levelOverview`
- `esc` at L3 sets `streamLevel = levelTask`
- `esc` at L1 does nothing (use `q` to quit)
- `tab` at L3 toggles `agentPane` between 0 and 1
- `enter` at L3 toggles `toolExpanded` or `diffExpanded` depending on pane

## View Rendering

### Level 1: Streams Overview

```
 Stacks   Streams   Chat
══════════════════════════════════════════════════════════════════════════════
 STREAMS                                                    2 active  1 idle
 ═══════════════════════════════════════════════════════════════════════════

 > ● SB-042 Session API                    session-mgmt/3-session-api
   ──────────────────────────────────────────────────────────────────────
   /plan_w_team   architect ✓ → review ✓ → build ● → validate ○
   Active: Builder (opus-4)                 7 files  8.1k tok  4m 22s

   ○ SB-043 Token Refresh                  jwt-middleware/2-auth-middleware
   ──────────────────────────────────────────────────────────────────────
   /develop        understand ✓ → plan ✓ → implement ● → test ○
   Active: Implementer (sonnet-4)           3 files  2.4k tok  1m 50s

   · Reviewer                                                       idle
─────────────────────────────────────────────────────────────────────────────
 j/k:navigate  enter:drill-in  1-2:jump task  q:quit
```

Key rendering decisions:
- Phase pipeline uses `✓` (done), `●` (active), `○` (waiting)
- Active agent name and model shown inline
- Aggregate stats (files, tokens, elapsed) right-aligned
- Idle streams shown minimally at bottom

### Level 2: Task Stream Detail

```
 Stacks   Streams   Chat
══════════════════════════════════════════════════════════════════════════════
 SB-042 Session API                                     /plan_w_team  4m 22s
 branch: session-mgmt/3-session-api                          8.1k tokens
 ═══════════════════════════════════════════════════════════════════════════

 architect ✓ ────── review ✓ ────── build ● ────── validate ○

 AGENTS
   ✓ Architect       opus-4     1.2k tok   45s    Designed session validation flow
   ✓ Reviewer         opus-4     2.1k tok   1m 12s  Approved with minor feedback
 > ● Builder          opus-4     4.2k tok   2m 15s  Implementing endpoints (3/4 done)
   ○ Validator        sonnet-4   —          —       Waiting

 FILES TOUCHED (7)
   features/sessions/models.py          +42  -3
   features/sessions/service.py         +18  -0
   molecules/session_workflow.py        +65  -12
   organisms/rest/sessions.py           +38  -0
   organisms/rest/dependencies.py       +5   -1
   tests/test_session_api.py            +72  -0
   alembic/versions/003_sessions.py     +25  -0

 SUMMARY
   Builder is implementing the session CRUD endpoints. 3 of 4 endpoints
   complete (create, get, list). Refresh endpoint in progress.
─────────────────────────────────────────────────────────────────────────────
 j/k:navigate  enter:drill-in  esc:back  1-4:jump agent
```

Key rendering decisions:
- Phase pipeline rendered as horizontal bar with connectors
- Agent roster is a table with status icon, name, model, tokens, duration, summary
- Active agent highlighted with bold + accent color
- File tree shows aggregate adds/removes
- Summary section at bottom

### Level 3: Agent Detail (Two-Pane)

#### Messages Pane (agentPane=0)

```
 Stacks   Streams   Chat
══════════════════════════════════════════════════════════════════════════════
 SB-042 > Builder (opus-4)                              4.2k tok  2m 15s
 ═══════════════════════════════════════════════════════════════════════════

 [Messages]  Files                                            3/4 endpoints
 ──────────────────────────────────────────────────────────────────────────

 THOUGHT
 │ I need to implement the session CRUD endpoints. Let me start by
 │ reading the existing models to understand the Session pattern.

   ▸ Read  features/sessions/models.py                            85ms
     (Session EventPattern with 6 fields, state machine: active/expired)

   ▸ Read  features/sessions/service.py                           62ms
     (SessionService with create, get, list, transition methods)

 RESPONSE
 │ I'll create the REST router with 4 endpoints: create, get, list,
 │ and refresh. Starting with the router boilerplate.

   ▾ Edit  organisms/rest/sessions.py                            210ms
     ┌──────────────────────────────────────────────────────────┐
     │ + from fastapi import APIRouter, Depends               │
     │ + from ..dependencies import get_db                     │
     │ + router = APIRouter(prefix="/sessions", tags=["..."])  │
     │ +                                                       │
     │ + @router.post("/")                                     │
     │ + async def create_session(                             │
     │ +     data: SessionCreate,                              │
     │ +     db: AsyncSession = Depends(get_db),               │
     │ + ):                                                    │
     └──────────────────────────────────────────────────────────┘

   ▸ Bash  just test -- -k test_session                          1.2s
     (3 passed, 0 failed)

 THOUGHT
 │ Create, get, and list endpoints pass. Now implementing refresh.
─────────────────────────────────────────────────────────────────────────────
 j/k:scroll  tab:files pane  enter:expand tool  esc:back
```

#### Files Pane (agentPane=1)

```
 Stacks   Streams   Chat
══════════════════════════════════════════════════════════════════════════════
 SB-042 > Builder (opus-4)                              4.2k tok  2m 15s
 ═══════════════════════════════════════════════════════════════════════════

  Messages  [Files]                                           3/4 endpoints
 ──────────────────────────────────────────────────────────────────────────

 > organisms/rest/sessions.py                            +38  -0
   features/sessions/models.py                            +2  -1
   molecules/session_workflow.py                         +15  -4
   tests/test_session_api.py                             +72  -0

 ─── organisms/rest/sessions.py ────────────────────────────────────────
 │ + from fastapi import APIRouter, Depends, HTTPException
 │ + from ..dependencies import get_db
 │ +
 │ + router = APIRouter(prefix="/sessions", tags=["sessions"])
 │ +
 │ + @router.post("/", response_model=SessionResponse)
 │ + async def create_session(
 │ +     data: SessionCreate,
 │ +     db: AsyncSession = Depends(get_db),
 │ + ):
 │ +     service = SessionService()
 │ +     session = await service.create(db, data)
 │ +     return session
 │ - # placeholder
─────────────────────────────────────────────────────────────────────────────
 j/k:navigate  enter:expand/collapse diff  tab:messages pane  esc:back
```

Key rendering decisions:
- Two-pane toggle via `tab`, active pane indicated by `[brackets]`
- Tool calls show `▸` collapsed, `▾` expanded
- Collapsed tool calls show: icon, name, params summary, duration on one line, result summary on next
- Expanded tool calls show full diff with green `+` / red `-` lines in a box
- Messages alternate between THOUGHT and RESPONSE headers
- File pane: top half is file list with cursor, bottom half shows diff of selected file

## Fake Data Structure

### Task 1: SB-042 Session API (/plan_w_team, BUILD phase)

```
Phases: architect(done) -> review(done) -> build(active) -> validate(waiting)

Architect (done, opus-4, 1.2k tok, 45s):
  - Designed session validation flow
  - Messages: 2 thoughts, 1 response
  - Tools: 3x Read (models, service, existing router)
  - Files read: 3

Reviewer (done, opus-4, 2.1k tok, 1m 12s):
  - Approved architecture with minor feedback on error handling
  - Messages: 1 thought, 1 response
  - Tools: 2x Read, 1x Grep
  - Files read: 3

Builder (active, opus-4, 4.2k tok, 2m 15s):
  - Implementing endpoints, 3/4 complete
  - Messages: 3 thoughts, 2 responses (scrollable)
  - Tools: 2x Read, 3x Edit, 1x Bash (test run)
  - Files: sessions.py(+38), models.py(+2,-1), workflow.py(+15,-4), test.py(+72)

Validator (waiting, sonnet-4):
  - No messages yet
```

### Task 2: SB-043 Token Refresh (/develop, IMPLEMENT phase)

```
Phases: understand(done) -> plan(done) -> implement(active) -> test(waiting)

Understander (done, sonnet-4, 800 tok, 30s):
  - Read existing token refresh logic
  - Messages: 1 thought, 1 response
  - Tools: 2x Read, 1x Grep
  - Files: 2

Planner (done, opus-4, 1.1k tok, 40s):
  - Planned refresh token rotation strategy
  - Messages: 1 thought, 1 response
  - Tools: 1x Read
  - Files: 1

Implementer (active, sonnet-4, 500 tok, 40s):
  - Adding token rotation to refresh endpoint
  - Messages: 2 thoughts, 1 response
  - Tools: 1x Read, 1x Edit
  - Files: token_service.py(+22,-8), test_tokens.py(+15)

Tester (waiting, sonnet-4):
  - No messages yet
```

## Keyboard Mappings

| Key | Level 1 | Level 2 | Level 3 |
|-----|---------|---------|---------|
| `j`/`down` | Next task | Next agent | Scroll down |
| `k`/`up` | Prev task | Prev agent | Scroll up |
| `enter` | Drill into task | Drill into agent | Expand/collapse tool or diff |
| `esc` | No-op | Back to L1 | Back to L2 |
| `tab` | Next main tab | Next main tab | Toggle messages/files pane |
| `shift+tab` | Prev main tab | Prev main tab | Prev main tab |
| `1`-`9` | Jump to task N | Jump to agent N | Jump to section N |
| `q` | Quit | Quit | Quit |
| `ctrl+c` | Quit | Quit | Quit |

Note: `tab` behavior changes at L3. At L1/L2, `tab` switches the main tab bar (Stacks/Streams/Chat). At L3, `tab` switches the sub-pane (messages/files). `shift+tab` always switches the main tab bar.

## --dump Flag Support

Extend the existing `--dump` flag to support level suffixes:

```
--dump streams          # Level 1: task overview (default)
--dump streams:task     # Level 2: first active task detail
--dump streams:agent    # Level 3: first active agent detail
--dump streams:agent:1  # Level 3: specific agent by index
```

Implementation: parse the colon-separated value after "streams", set `streamLevel` accordingly, and call the appropriate view function.

## Integration Plan

### What Changes

1. **`stream` type** -- Replaced by `taskSession` and its children. The existing `stream` struct, `fakeStreams()`, `stStatus`, and all related constants are removed.

2. **`model` struct** -- Remove `streams []stream`, `streamCur int`, `streamExp int`. Add `tasks []taskSession`, `streamLevel streamLevel`, `taskCur int`, `agentCur int`, `msgScroll int`, `agentPane int`, `toolExpanded int`, `diffExpanded int`.

3. **`initialModel()`** -- Replace `streams: fakeStreams()` with `tasks: fakeTasks()`. Initialize new cursor/scroll fields.

4. **`updateStreams(k string)`** -- Complete rewrite. Becomes a switch on `m.streamLevel` dispatching to `updateStreamsL1`, `updateStreamsL2`, `updateStreamsL3`.

5. **`viewStreams(h int)`** -- Complete rewrite. Becomes a switch on `m.streamLevel` dispatching to `viewStreamsL1`, `viewStreamsL2`, `viewStreamsL3`.

6. **`renderStatus()`** -- Update the `tabStreams` hint string based on `m.streamLevel`.

7. **`main()` dump handling** -- Add parsing for `streams:task`, `streams:agent` variants.

### What Stays

- All color definitions (`colorAccent`, etc.) and style vars (`dimS`, `fgS`, etc.)
- Tab system (`tabID`, `tabNames`, `renderTabs()`)
- Stacks view (`viewStacks`, `updateStacks`, all stack/branch types)
- Chat view (`viewChat`)
- Helper functions (`branchShort`, `progressBar`, `padR`, `minI`, `maxI`)
- `fakeProject()` -- unchanged
- Main Bubble Tea loop (`Init`, `Update`, `View`)

### New Functions (approximate)

| Function | Purpose |
|----------|---------|
| `fakeTasks()` | Build hardcoded task session data |
| `updateStreamsL1(k) model` | Key handling for task overview |
| `updateStreamsL2(k) model` | Key handling for task detail |
| `updateStreamsL3(k) model` | Key handling for agent detail |
| `viewStreamsL1(h) string` | Render task overview |
| `viewStreamsL2(h) string` | Render task detail |
| `viewStreamsL3(h) string` | Render agent detail (dispatches to pane) |
| `renderPhasePipeline(phases, width) string` | Horizontal phase bar with connectors |
| `renderAgentRoster(agents, cursor, width) []string` | Agent table rows |
| `renderFileTree(files, cursor, width) []string` | File list with +/- counts |
| `renderMessageStream(msgs, scroll, h, w) []string` | Scrollable message view |
| `renderToolCall(tc, expanded, w) []string` | Single tool call (collapsed/expanded) |
| `renderDiffBox(diff, w) []string` | Diff hunk in a box with +/- coloring |

### New Styles Needed

```go
colorYellow = lipgloss.AdaptiveColor{Light: "#F57F17", Dark: "#F1FA8C"}  // for waiting/pending
yellowS     = lipgloss.NewStyle().Foreground(colorYellow)
```

No other new colors needed -- done uses `greenS`, active uses `accentS`, waiting uses `dimS`, errors use `redS`.

## Implementation Order

| Step | What | Depends On |
|------|------|------------|
| 1 | Define new types (`taskSession`, `taskAgent`, `toolCall`, etc.) and enums | -- |
| 2 | Build `fakeTasks()` with full fake data for both task sessions | Step 1 |
| 3 | Update `model` struct, remove old stream fields, add new ones | Step 1 |
| 4 | Implement `viewStreamsL1` + `updateStreamsL1` (phase pipeline rendering) | Steps 2-3 |
| 5 | Implement `viewStreamsL2` + `updateStreamsL2` (agent roster, file tree) | Steps 2-3 |
| 6 | Implement `viewStreamsL3` + `updateStreamsL3` (message stream, tool calls, diffs) | Steps 2-3 |
| 7 | Wire `updateStreams`/`viewStreams` dispatchers, update `renderStatus` hints | Steps 4-6 |
| 8 | Update `--dump` flag parsing for level suffixes | Step 7 |
| 9 | Test all three levels at various terminal widths (80, 120, 160) | Step 8 |

All steps modify `cli/main.go` only. Steps 4-6 can be done in parallel.

## Open Questions

1. **Real-time updates.** This spec is static fake data. When wiring to a real backend, should L3 auto-scroll as new messages arrive, or require manual scroll? Suggest auto-scroll with a "pinned to bottom" indicator that disengages when user scrolls up.

2. **Terminal width breakpoints.** At widths below 80, the phase pipeline and agent roster get cramped. Should we collapse to a vertical layout, or just truncate? Suggest vertical layout below 90 columns.

3. **Color for phase pipeline connectors.** The `──────` between phases could be colored (green for done segments, dim for pending). Worth the visual complexity? Suggest yes -- it reinforces progress at a glance.
