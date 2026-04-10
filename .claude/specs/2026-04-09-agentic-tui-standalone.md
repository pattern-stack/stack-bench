---
title: agentic-tui — Standalone Package from PR #198
date: 2026-04-09
status: draft
branch: null
depends_on: [2026-04-08-agentic-tui-package.md, 2026-03-22-message-parts.md]
adrs: []
---

# agentic-tui — Standalone Package from PR #198

## CRITICAL CONSTRAINT: PR #198 IS THE VISUAL TRUTH

**DO NOT simplify, rewrite, or "improve" any rendering code from PR #198.**
The files under `app/cli/internal/chat/`, `app/cli/internal/ui/`, and
`app/cli/internal/app/` on the PR #198 branch are the canonical visual
implementation. Copy them. Restructure import paths. Do not change rendering
logic, component output, spacing, colors, spinner behavior, diff formatting,
or markdown rendering. If the output of the standalone package differs
visually from PR #198's demo mode, that is a bug.

A prior attempt (PR #196) tried to extract the TUI and lost visual fidelity
— spinner presets gone, diff rendering simplified, theme auto-detect dropped,
dual spinners reduced to single. That regression is why this constraint
exists. The rendering code is proven and polished. Treat it as frozen.

## Goal

Build a production-ready, language-agnostic terminal chat UI for any AI agent
backend. Start from PR #198's code (the frozen visual implementation) and add
main's infrastructure (public API, JSON-RPC stdio, contract tests, examples)
around it — never touching the rendering pipeline.

## Why Start from PR #198, Not Main

PR #196's extraction onto main simplified the rendering to get it working.
Main is missing spinner presets, dual spinners, graduated escalation,
structured diff parsing, syntax-highlighted diffs, theme auto-detect, and
demo infrastructure. Porting those visual details forward proved lossy last
time — **this already failed once and we are not repeating it**. PR #198 has
the exact UX we want — starting from it means fidelity by definition.

Main's additions over PR #198 are **structural, not visual**:
- Public API wrapper (~200 lines, zero rendering interaction)
- JSON-RPC stdio client (~570 lines, self-contained transport)
- EndpointConfig for custom API paths (~40 lines)
- Contract tests (~450 lines, standalone package)
- Examples (~150 lines across 6 dirs)
- ExecService refactor (minor rename from LocalService)
- Type duplication + adapter boilerplate (to be eliminated, not ported)

These are additive layers that wrap around rendering code without modifying
it. Porting them into PR #198's codebase is mechanical and testable.

## Current State

### PR #198 branch (`dugshub/message-parts/2-part-aware-chat`)

The visual truth. 14 commits of polished TUI at `app/cli/internal/*`:

**Rendering pipeline (preserve exactly)**:
- Part-aware `Message{Role, Parts []MessagePart}` model
- Per-part dispatch: text → markdown, thinking → summary + spinner, tool_call → display-type, error → error block
- Blank-line spacing between parts of different types
- `indentBody` removed — tool bodies flush with header

**Components (preserve exactly)**:
- `DiffBlock` with structured `[]DiffHunk`, `ParseUnifiedDiff`, chroma syntax hl on added lines, muted blue/red palette, line numbers in marker color
- `CodeBlock` with `│` gutter aligned to DiffBlock, filename header, chroma auto-detect
- `ToolCallBlock` with state icons, display-type body dispatch
- Custom goldmark renderer: hanging indent lists, table routing, code block highlighting
- All atoms: badge, codeblock, highlight, icon, inlinecode, separator, spinner, table, textblock

**Spinners (preserve exactly)**:
- 14 frame presets (Dense, Sparse, Pulse, Heartbeat, Star, etc.)
- Dual spinners: `toolSpinner` (SparseCenter) + `thinkingSpinner` (Star)
- Graduated escalation: SparseCenter (< 5s) → Pulse (5-15s) → Heartbeat (> 15s)
- StatusBar heartbeat colored by health state

**Theme (preserve exactly)**:
- Dark + light themes with design tokens
- Auto-detect via `lipgloss.HasDarkBackground` (OSC 11)
- `--theme` flag + env var override

**Demo (preserve exactly)**:
- `DemoClient` with structured `DemoPart` format
- 4-exchange fixture: Q&A, multi-tool recovery, long run, tool rejection
- `--demo`, `--demo-script`, `--demo-gallery`, `--demo-spinners` modes

**Streaming**:
- `StreamChunk` with structured tool fields
- `ChunkFromSSE` SSE parser for the event vocabulary
- `HTTPClient` and `StubClient` implementations

### Main branch additions (port into PR #198)

**Public API layer** (`packages/agent-tui/*.go`):
- `tui.Client` interface (5 methods): `ListAgents`, `CreateConversation`, `SendMessage`, `ListConversations`, `GetConversation`
- `tui.Config` struct: `AppName`, `AssistantLabel`, `BackendURL`, `BackendService`, `BackendStdio`, `EnvOverride`, `Theme`, `Commands`, `Endpoints`
- `tui.App` with `New(Config)` + `Run()` — resolves backend, builds registry, starts Bubble Tea
- `tui.EndpointConfig` for customizable API paths
- `tui.CommandDef` for consumer-registered slash commands
- `tui.NewHTTPClient()`, `tui.NewStdioClient()`, `tui.NewStubClient()` factories

**JSON-RPC stdio client** (`packages/agent-tui/internal/stdioclient/`):
- `client.go` (~424 lines): spawns subprocess, stdin/stdout pipes, `readLoop` goroutine
- `jsonrpc.go` (~144 lines): JSON-RPC 2.0 wire types (Request, Response, Notification)
- Methods: `listAgents`, `createConversation`, `sendMessage` (streaming via `stream.event` notifications), `listConversations`, `getConversation`
- Graceful shutdown: SIGTERM → 5s grace → SIGKILL
- Pending request tracking with `map[id]chan *Response`

**HTTP client enhancements** (`packages/agent-tui/internal/httpclient/`):
- `EndpointConfig` for overriding default API paths
- Backward-compatible event name aliases (`message.delta` / `agent.message.chunk`)
- Graceful `ListAgents` fallback: tries `[]AgentSummary`, falls back to `[]string`

**Service lifecycle** (`packages/agent-tui/internal/service/`):
- `ExecService` (renamed from `LocalService`): spawn + health-check any backend process
- `ServiceManager`: multi-service orchestration, `StartAll`/`StopAll`/`HealthSummary`
- `ServiceHealthTick` → Bubble Tea command for periodic health polling

**Contract tests** (`packages/agent-tui/contracttest/`):
- `ValidateBackend()` — validates HTTP/SSE backend contract
- `ValidateStdioBackend()` — validates JSON-RPC backend contract
- Both check: listAgents, createConversation, sendMessage streaming

**Examples** (`packages/agent-tui/_examples/`):
- `minimal/` — 24-line HTTP integration
- `stdio-python/` — JSON-RPC subprocess (Python backend)
- `stdio-typescript/` — JSON-RPC subprocess (TypeScript backend)
- `custom-commands/` — adding slash commands
- `custom-theme/` — custom theme
- `demo/` and `gallery/` — demo modes

## Architecture (Target)

```
github.com/dugshub/agentic-tui/
├── go.mod                        # standalone module
├── tui.go                        # App, New(), Run() — public entry point
├── client.go                     # Client interface + factories
├── config.go                     # Config, EndpointConfig, CommandDef
├── types.go                      # StreamChunk, AgentSummary, etc. (SINGLE source)
├── service.go                    # ServiceNode alias
├── stdio.go                      # StdioConfig
├── demo.go                       # RunGallery, RunDemo (public)
├── PROTOCOL.md                   # Universal backend contract
├── LICENSE                       # MIT
│
├── internal/
│   ├── app/                      # Top-level Bubble Tea model
│   │   ├── model.go              # Phases: agent-select → chat
│   │   ├── demo.go               # Demo runner
│   │   ├── gallery.go            # Component showcase
│   │   └── spinners.go           # Spinner gallery
│   │
│   ├── chat/                     # Chat engine (FROM PR #198)
│   │   ├── model.go              # Part-aware messages, dual spinners, streaming
│   │   ├── view.go               # Per-part rendering, graduation, display-type dispatch
│   │   └── input.go              # Keystroke handling
│   │
│   ├── sse/                      # SSE parsing + event types
│   │   ├── parse.go              # ParseSSE, ChunkFromSSE
│   │   └── events.go             # Event constants, type aliases to root types
│   │
│   ├── httpclient/               # HTTP/SSE transport (FROM MAIN)
│   │   ├── client.go             # HTTPClient with EndpointConfig
│   │   └── stub.go               # StubClient
│   │
│   ├── stdioclient/              # JSON-RPC transport (FROM MAIN — new)
│   │   ├── client.go             # StdioClient
│   │   └── jsonrpc.go            # Wire types
│   │
│   ├── service/                  # Process lifecycle
│   │   ├── node.go               # ServiceNode interface
│   │   ├── local.go              # ExecService
│   │   └── manager.go            # ServiceManager
│   │
│   ├── command/                  # Slash command system
│   │   ├── registry.go           # Registry with fuzzy matching
│   │   ├── commands.go           # Built-in: /help, /clear, /agents, /quit
│   │   └── parse.go              # Slash command parser
│   │
│   └── ui/                       # Component library (FROM PR #198)
│       ├── markdown.go           # Streaming markdown renderer
│       ├── goldmark.go           # Custom goldmark → terminal
│       ├── theme/                # Tokens, dark/light, auto-detect, registry
│       ├── autocomplete/         # Slash command autocomplete
│       └── components/
│           ├── atoms/            # badge, codeblock, highlight, icon, spinner, etc.
│           └── molecules/        # diffblock, diffparser, toolcallblock, etc.
│
├── contracttest/                 # Backend validation (FROM MAIN)
│   ├── validate.go
│   └── validate_stdio.go
│
├── _examples/                    # Reference integrations (FROM MAIN)
│   ├── minimal/
│   ├── stdio-python/
│   ├── stdio-typescript/
│   ├── custom-commands/
│   └── custom-theme/
│
└── demo/                         # Demo fixtures (FROM PR #198)
    └── fixtures/
        ├── demo.json
        └── demo-parts.json
```

### How rendering stays untouched

The rendering pipeline lives entirely within `internal/chat/` and
`internal/ui/`. The additions from main live in separate packages that don't
import from these:

```
Rendering (PR #198, frozen):     Infrastructure (main, added):
  internal/chat/view.go            tui.go, client.go, config.go
  internal/chat/model.go           internal/httpclient/
  internal/ui/components/          internal/stdioclient/   ← NEW
  internal/ui/theme/               internal/service/
  internal/ui/markdown.go          contracttest/
  internal/ui/goldmark.go          _examples/
```

The only connection point is the `Client` interface and `StreamChunk` type —
both are data contracts, not rendering code.

## Protocol Specification

### SSE Event Vocabulary (HTTP transport)

| Event | Legacy Aliases | Data | Purpose |
|-------|---------------|------|---------|
| `message.delta` | `agent.message.chunk` | `{"delta": "..."}` | Streaming text |
| `message.complete` | `agent.message.complete` | `{"content": "...", "input_tokens": N, "output_tokens": N}` | Message done |
| `thinking` | `agent.reasoning` | `{"content": "..."}` | Reasoning/thinking |
| `tool.start` | `agent.tool.start`, `tool_start` | `{"tool_call_id", "tool_name", "display_type", "arguments"}` | Tool begins |
| `tool.end` | `agent.tool.end`, `tool_end` | `{"tool_call_id", "result", "error", "duration_ms", "display_type"}` | Tool ends |
| `tool.rejected` | `agent.tool.rejected` | `{"tool_name", "reason"}` | Safety gate |
| `error` | `agent.error` | `{"error_type", "message"}` | Fatal error |
| `done` | — | `{}` | Stream complete |

**Display types**: `generic` (default), `diff`, `code`, `bash`

### JSON-RPC Methods (Stdio transport)

| Method | Params | Result | Required |
|--------|--------|--------|----------|
| `listAgents` | `{}` | `[{id, name, role, model}]` | Yes |
| `createConversation` | `{agent_id}` | `{id}` | Yes |
| `sendMessage` | `{conversation_id, content}` | Streams via `stream.event` notifications | Yes |
| `listConversations` | `{agent_name}` | `[{id, agent_id, state, ...}]` | No |
| `getConversation` | `{id}` | `{id, messages, ...}` | No |

### HTTP Endpoints (configurable via EndpointConfig)

| Method | Default Path | Purpose |
|--------|-------------|---------|
| GET | `/agents` | List agents |
| POST | `/conversations` | Create conversation |
| POST | `/conversations/{id}/send` | Send message (SSE) |
| GET | `/conversations` | List conversations (optional) |
| GET | `/conversations/{id}` | Get conversation (optional) |
| GET | `/health` | Health check |

## Source Access (for ultra-plan)

All source code lives in this repo across two branches. No external repos
needed.

**PR #198 files** (visual truth — rendering, components, spinners, demo):
```
git show origin/dugshub/message-parts/2-part-aware-chat:<path>
```
Example: `git show origin/dugshub/message-parts/2-part-aware-chat:app/cli/internal/chat/view.go`

80 files under `app/cli/` on this branch.

**Main files** (infrastructure — public API, stdio, contract tests):
```
Direct reads from packages/agent-tui/
```
68 Go files under `packages/agent-tui/`.

**Work directory**: Build the standalone package at `packages/agentic-tui/`
within this repo. Repo extraction to a separate GitHub repo is a manual
final step outside the plan.

### go.mod dependencies (merged from both branches)

PR #198 has the superset of direct deps:
```
charm.land/bubbles/v2 v2.0.0
charm.land/bubbletea/v2 v2.0.2
charm.land/lipgloss/v2 v2.0.2
github.com/alecthomas/chroma/v2 v2.23.1
github.com/yuin/goldmark v1.7.17
gopkg.in/yaml.v3 v3.0.1
```
Main's agent-tui only has `bubbletea` + `lipgloss` as direct deps (the
others are imported transitively). The new module needs all six as direct.

### SSE parser differences (Phase 5 merge guide)

Main added these backward-compatible event name aliases that PR #198 lacks:
- `message.delta` → ChunkText
- `message.complete` → ChunkText (done)
- `tool.start` → ChunkToolStart
- `tool.end` → ChunkToolEnd

PR #198 has richer payload parsing that main dropped:
- `SSEToolStartData.Arguments` (map[string]any) — main only has `Input` (string)
- `SSEToolEndData.Result` (any) — main only has `Output` (string)
- Fallback logic: `Result` if `Output` is empty, `Input` as name fallback

**Merge strategy**: Take PR #198's parser as the base (richer payloads),
add main's four new event name aliases to the switch statement. ~10 lines.

### App model wiring differences (Phase 3 reconciliation)

**PR #198 constructor**: `app.New(client api.Client, mgr *service.ServiceManager) Model`
- Creates registry internally: `command.DefaultRegistry()`
- Has demo fields: `demo bool`, `demoRunner *DemoRunner`, `gallery bool`
- Has `statusSpinner` for health heartbeat
- Chat init: `chat.New(client, agentName, registry)`
- Chat height: `m.height - 5` (accounts for status bar + header)

**Main constructor**: `app.New(client sse.Client, mgr *service.ServiceManager, reg *command.Registry, cfg Config) Model`
- Registry passed in from caller (enables consumer-registered commands)
- Config has `AppName`, `AssistantLabel`
- No demo/gallery fields (handled elsewhere)
- Chat init: `chat.New(client, agentName, registry, cfg.AssistantLabel)`
- Chat height: `m.height - 2`

**Reconciliation**: Take PR #198's model (has demo/gallery/spinners), adopt
main's signature pattern (pass registry + config in). Add `Config` struct.
Keep PR #198's height calculation (it accounts for the richer chrome).

## Implementation Phases

| Issue | What | Depends On | Parallel? |
|-------|------|------------|-----------|
| SB-058 | Scaffold standalone package from PR #198 | -- | No (foundation) |
| SB-059 | Unify types into single `internal/types` package | SB-058 | No (enables rest) |
| SB-060 | Port public API layer from main | SB-059 | Yes (with 061-063) |
| SB-061 | Port JSON-RPC stdio client from main | SB-059 | Yes (with 060,062,063) |
| SB-062 | Port HTTP client enhancements from main | SB-059 | Yes (with 060,061,063) |
| SB-063 | Port service lifecycle from main | SB-059 | Yes (with 060-062) |
| SB-064 | Contract tests, examples, PROTOCOL.md | SB-061, SB-062 | No (capstone) |

```
SB-058 (scaffold) → SB-059 (unify types) → ┬─ SB-060 (public API)      ─┐
                                             ├─ SB-061 (stdio client)     ├─ SB-064 (tests+examples+protocol)
                                             ├─ SB-062 (HTTP enhancements)┘
                                             └─ SB-063 (service lifecycle)
```

## Phase Details

### Phase 1: Restructure PR #198 into standalone package layout

Take PR #198's `app/cli/` code and reorganize into the target layout. This
is a **pure file-move + import-path rewrite** — no logic changes, no
"improvements", no simplifications. Every .go file from the PR #198 branch
that contains rendering, components, theme, chat model, or markdown code
must be copied verbatim (modulo import paths). If `go build` fails after
the restructure, fix imports — do not change the code itself.

**Source → Target mapping**:
```
app/cli/internal/api/client.go    → internal/httpclient/client.go
app/cli/internal/api/types.go     → types.go (root package)
app/cli/internal/api/sse.go       → internal/sse/parse.go
app/cli/internal/app/model.go     → internal/app/model.go
app/cli/internal/app/demo.go      → internal/app/demo.go
app/cli/internal/app/gallery.go   → internal/app/gallery.go
app/cli/internal/app/spinners.go  → internal/app/spinners.go
app/cli/internal/chat/model.go    → internal/chat/model.go
app/cli/internal/chat/view.go     → internal/chat/view.go
app/cli/internal/command/         → internal/command/
app/cli/internal/service/         → internal/service/
app/cli/internal/ui/              → internal/ui/
app/cli/fixtures/                 → demo/fixtures/
app/cli/main.go                   → (becomes example, not part of library)
```

**Import path rewrite**:
```
github.com/dugshub/stack-bench/app/cli/internal/api
  → github.com/dugshub/agentic-tui/internal/httpclient  (client parts)
  → github.com/dugshub/agentic-tui/internal/sse         (SSE parts)

github.com/dugshub/stack-bench/app/cli/internal/*
  → github.com/dugshub/agentic-tui/internal/*
```

**New go.mod**:
```
module github.com/dugshub/agentic-tui

go 1.23

require (
    charm.land/bubbles/v2 v2.0.0
    charm.land/bubbletea/v2 v2.0.2
    charm.land/lipgloss/v2 v2.0.2
    github.com/alecthomas/chroma/v2 v2.x.x
    github.com/yuin/goldmark v1.7.17
)
```

**Verification**: `go build ./...` and `go test ./...` must pass after
restructure. The demo mode should render identically.

### Phase 2: Unify types

PR #198 has types scattered across `api/types.go` and `api/sse.go`. Main
duplicated them between `tui` root and `internal/sse`. We fix this now.

**Create `internal/types/` as single source**:
```go
// internal/types/types.go
package types

type AgentSummary struct { ... }
type Conversation struct { ... }
type ConversationDetail struct { ... }
type ConversationMessage struct { ... }
type MessagePart struct { ... }
type ChunkType string
type StreamChunk struct { ... }
```

**Root package re-exports via aliases**:
```go
// types.go (root)
package tui
import "github.com/dugshub/agentic-tui/internal/types"
type StreamChunk = types.StreamChunk
type AgentSummary = types.AgentSummary
// etc.
```

**All internal packages import `internal/types`** — no cycles, no adapters,
no conversion boilerplate.

### Phase 3: Port public API layer from main

Take main's `packages/agent-tui/{tui.go,client.go,config.go,command.go,
service.go,stdio.go,theme.go}` and adapt to the new type-unified layout.

**Key simplification**: No `publicClientAdapter` or `internalClientAdapter`.
Transport implementations return `types.StreamChunk` directly. The `Client`
interface uses `types.StreamChunk`. Zero conversion.

**Files to create**:
- `tui.go` — `App` struct, `New()`, `Run()`, `RunGallery()`
- `client.go` — `Client` interface, `NewHTTPClient()`, `NewStdioClient()`, `NewStubClient()`
- `config.go` — `Config`, `EndpointConfig`, `CommandDef`
- `service.go` — `ServiceNode` type alias
- `stdio.go` — `StdioConfig`
- `theme.go` — `Theme` type alias

**Adaptation needed**: Main's `App.resolveBackend()` and `App.Run()` work
as-is once the type adapters are removed. Main's `buildRegistry()` for
consumer commands works as-is.

### Phase 4: Port JSON-RPC stdio client from main

Copy `packages/agent-tui/internal/stdioclient/` directly. This is a
self-contained package that depends only on `internal/types` (after
phase 2 unification).

**Files**:
- `internal/stdioclient/client.go` (~424 lines)
- `internal/stdioclient/jsonrpc.go` (~144 lines)

**Changes**: Replace `internal/sse` type imports with `internal/types`.
The `convertStreamEvent()` function maps JSON-RPC stream notifications to
`types.StreamChunk` — same logic, just importing from a different package.

**Test**: Port `client_test.go` from main.

### Phase 5: Port HTTP client enhancements from main

PR #198's `HTTPClient` is functional but doesn't have main's improvements:

**EndpointConfig**: Configurable API paths instead of hardcoded strings.
Take from `packages/agent-tui/internal/httpclient/client.go`.

**Event name aliases**: Main added backward-compatible aliases
(`message.delta` / `agent.message.chunk`) in the SSE parser. Merge these
into the `ChunkFromSSE` function.

**ListAgents fallback**: Try `[]AgentSummary`, fall back to `[]string`.
This handles backends that return simple name arrays.

**StubClient**: Enhanced version from main with proper `StubClient` struct.

### Phase 6: Port service lifecycle from main

Copy `packages/agent-tui/internal/service/` — it's almost identical to
PR #198's `service/` but with `ExecService` (renamed from `LocalService`)
and a few polish fixes.

- `node.go` — `ServiceNode` interface (same)
- `local.go` — `ExecService` (renamed, same logic)
- `manager.go` — `ServiceManager` (same)

### Phase 7 (SB-064): Contract tests, examples, PROTOCOL.md

**Contract tests** — copy `packages/agent-tui/contracttest/`:
- `validate.go` — HTTP backend contract validation
- `validate_stdio.go` — JSON-RPC backend contract validation
- Update imports to new module path

**Examples** — copy `packages/agent-tui/_examples/`:
- `minimal/main.go` — 24-line HTTP example
- `stdio-python/` — Python JSON-RPC backend
- `stdio-typescript/` — TypeScript JSON-RPC backend
- `custom-commands/main.go` — registering custom slash commands
- `custom-theme/main.go` — custom theme
- Update imports to new module path

**PROTOCOL.md** — stable reference for backend implementors:
1. SSE event vocabulary with full JSON schemas
2. JSON-RPC method definitions (params, results, error codes)
3. HTTP endpoint conventions (paths, headers, SSE wire format)
4. Display type registry and rendering behavior
5. Streaming lifecycle (connect → stream → done/error)
6. Backward compatibility guarantees
7. "Implementing a backend in 30 minutes" quick-start

## Risk Analysis

**Low risk** (file moves + import rewrites):
- SB-058 (scaffold) — mechanical, verified by `go build`
- SB-059 (unify types) — well-understood Go pattern
- SB-061, SB-063 (stdio, service) — copying self-contained packages

**Medium risk**:
- SB-060 (public API) — adapting main's wrapper to PR #198's internals.
  Main's `app.Config` vs PR #198's `app.New()` signature differ. Reconciliation
  documented in the SSE parser and app model sections above.
- SB-062 (HTTP enhancements) — merging main's SSE parser improvements into
  PR #198's parser. Strategy: PR #198 base + main's 4 aliases (~10 lines).

**Zero risk to visual fidelity**: No issue modifies rendering logic in
`internal/chat/view.go`, `internal/ui/components/`, `internal/ui/theme/`,
or `internal/ui/markdown.go`. These are the rendering pipeline and they
stay frozen. The ONLY acceptable changes to these files are import path
rewrites (e.g., `github.com/dugshub/stack-bench/app/cli/internal/ui` →
`github.com/dugshub/agentic-tui/internal/ui`). Any other change to rendering
files is a bug in the plan execution, not an improvement.

## Resolved Decisions

1. **Module path**: `github.com/dugshub/agentic-tui` — matches brand, can transfer org later.
2. **Bubble Tea v2**: Pin `charm.land/bubbletea/v2 v2.0.2` (pre-1.0, document in go.mod).
3. **Legacy event aliases**: Keep in v0.x for backward compat, revisit for v1.0.
4. **BranchConversation**: Dropped from Client interface (stack-bench-specific).
5. **Theme system**: Keep PR #198's YAML-loaded themes (`themes/dark.yml`, `themes/light.yml`, `embed.go`).
6. **Chat model**: Keep PR #198's `PartType string` constants and struct-based `ToolCallPart` (richer than main's iota pattern).
7. **SSE parser**: PR #198 base + main's 4 canonical aliases (~10 lines added).
8. **Stdio protocol**: JSON-RPC 2.0 (already shipped on main, more capable than spec's simpler SSE-over-stdin).
9. **Work directory**: Build at `packages/agentic-tui/` in this repo. Repo extraction is a post-epic ship task.

## What's NOT in This Epic

- CI/CD pipelines, GitHub Release workflow, README.md (post-epic ship tasks)
- Stack Bench integration (post-epic: update `app/cli/go.mod`, delete `packages/agent-tui/`)
- Python SDK wrapper / wheel bundling
- Homebrew/apt distribution
- Expandable/interactive parts (#199)
- Word-level diff highlights (#200)
- Tool approval protocol
- Custom display type plugins
- Multi-TUI theme isolation

## Epic & Issues

This spec is implemented via **EP-017** with 7 issues (SB-058 through SB-064).
See `docs/epics/ep-017-agentic-tui-standalone.md` for the full issue table
and dependency graph.

## Reference: Source Files

### From PR #198 (the visual truth — keep as-is)

```
app/cli/internal/chat/model.go     — Part-aware messages, dual spinners, streaming
app/cli/internal/chat/view.go      — Per-part rendering, graduation, display-type
app/cli/internal/ui/               — All components, theme, markdown
app/cli/internal/app/              — App model, demo, gallery, spinners
app/cli/internal/command/          — Slash command registry
app/cli/internal/api/sse.go        — SSE parser
app/cli/internal/api/types.go      — StreamChunk, DTOs
app/cli/internal/api/client.go     — HTTPClient, StubClient
app/cli/internal/service/          — LocalService, ServiceManager
app/cli/fixtures/                  — Demo fixtures
```

### From main (infrastructure to add)

```
packages/agent-tui/tui.go           — App, New(), Run()
packages/agent-tui/client.go        — Client interface, factories, adapters (simplify)
packages/agent-tui/config.go        — Config, EndpointConfig
packages/agent-tui/types.go         — Public type re-exports (merge with PR #198 types)
packages/agent-tui/command.go       — CommandDef
packages/agent-tui/service.go       — ServiceNode alias
packages/agent-tui/stdio.go         — StdioConfig
packages/agent-tui/theme.go         — Theme alias
packages/agent-tui/internal/stdioclient/  — JSON-RPC client (NEW, doesn't exist in PR #198)
packages/agent-tui/internal/httpclient/   — Enhanced HTTP client (merge improvements)
packages/agent-tui/contracttest/          — Backend validation (NEW)
packages/agent-tui/_examples/             — Reference integrations (NEW)
```
