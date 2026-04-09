---
title: agentic-tui — Standalone Go Terminal UI Package
date: 2026-04-08
status: draft
branch: dugshub/message-parts/2-part-aware-chat
depends_on: [2026-03-22-message-parts.md]
adrs: []
---

# agentic-tui — Standalone Go Terminal UI Package

## Goal

Extract all of the chat TUI work from this branch into a **standalone Go
package** that any agent framework can import. Mask it behind language SDKs
(Python, Go) that live in `agentic-patterns`, so end users never touch Go
directly — they write `tui.run_chat(agent=...)` in Python and get a polished
terminal chat experience. Stack Bench stops maintaining its own CLI internals
and imports the package as a thin wrapper around its REST API.

This spec exists because:

1. **PR #198 is stranded.** It was built against `app/cli/internal/*` in
   stack-bench, but main has since merged PR #196 which extracted the CLI
   into `packages/agent-tui/` — a rushed extraction the team doesn't stand
   behind. Every commit on this branch conflicts with the new path. Porting
   the changes would bake the rushed extraction in.
2. **The TUI is a general-purpose artifact.** Nothing about the rendering,
   streaming, or part-aware chat model is stack-bench specific. Other
   agent frameworks (LangChain, Anthropic SDK, custom frameworks) should be
   able to adopt it without taking a dependency on stack-bench.
3. **Clean-slate design is fastest.** PR #198's commits become the feature
   spec for the new package; every polish item is captured in
   `git log origin/main..dugshub/message-parts/2-part-aware-chat`.

## Context — what PR #198 contains

Five months of iteration on a part-aware chat TUI. Each of these is a
feature the new package must preserve:

**Rendering pipeline:**
- Part-aware Message model: `text | thinking | tool_call | error` parts
- Per-part render dispatch with blank-line spacing between type changes
- Custom goldmark renderer (MIT)
  - Hanging indent for bullet and numbered lists
  - Table rendering routed to our Table atom
  - Code blocks with chroma syntax highlighting per-token
  - Inline styles (bold, italic, code) mapped to theme tokens
- `CodeBlock` atom with `│` gutter, filename header, chroma syntax via
  `lexers.Match` (filename-based language detection, ~250 languages)
- `DiffBlock` molecule with structured `[]DiffHunk` input, `ParseUnifiedDiff`
  helper, green/red line numbers, syntax highlighting on added lines,
  muted blue/red palette, gutter aligned with CodeBlock
- `ToolCallBlock`, `ErrorBlock`, `MessageBlock`, `StatusBar`, `Header`,
  `ConfirmPrompt`, `RadioSelect`, `Table`, `Separator`, `Icon`, `Badge`,
  `TextBlock`, `Spinner`

**Streaming:**
- `StreamChunk` with structured tool fields (ID, name, display_type,
  arguments, result, error, duration)
- SSE parser (`ChunkFromSSE`) for agentic-patterns' event vocabulary
- Client interface with HTTPClient and StubClient

**Spinners (new in this branch):**
- 14 exported frame presets: Dense, Sparse, SparseLow, SparseCenter,
  Pulse, Heartbeat, Twinkle, Bounce, Pong, Orbit, Arc, HalfCircle, Star,
  Arrow, Triangle, PulseBar, BlockFade, Classic
- Per-instance `Frames` and `Interval` fields
- Dual spinners in chat: `toolSpinner` (SparseCenter) for tool calls,
  `thinkingSpinner` (Star) for active thinking; tick routing by ID
- Graduated tool call spinner: SparseCenter (< 5s) → Pulse (5-15s) →
  Heartbeat (> 15s) based on `ToolCallPart.StartedAt`
- `StatusBar` with optional heartbeat spinner colored by health state
- `--demo-spinners` gallery showing every preset side-by-side

**Theming:**
- Dark + light themes loaded from embedded YAML
- Auto-detection via `lipgloss.HasDarkBackground` (OSC 11 terminal query)
- `--theme` flag and `SB_THEME` env var overrides

**Demo infrastructure:**
- `DemoClient` replays scripted SSE fixtures with realistic timing
- Four-exchange `demo-parts.json`: pure Q&A, multi-tool recovery,
  long-running test (18s, graduates spinner), tool rejection (safety gate)
- `--demo`, `--demo-script`, `--demo-gallery`, `--demo-spinners` modes

**Issues tracked for future work:**
- #199 — Expandable/interactive parts (click to toggle full content)
- #200 — Word-level diff highlights (attempted with diff-match-patch,
  reverted, captured for redesign)

## Why not monorepo in agentic-patterns

The original thinking was a polyglot monorepo. On reflection, separate
repos are cleaner because:

1. **Go tooling doesn't love living inside non-Go repos.** `go.mod`
   placement becomes fragile, `go get` paths get ugly, `go test ./...`
   runs over Python files.
2. **Python build tools aren't set up for Go.** Tools like `maturin` and
   `setuptools-rust` exist for Python+Rust; Python+Go has fewer
   established workflows. We'd be building tooling where library tooling
   exists for the separate-repo case.
3. **Contributor cognitive load.** Python devs working on the SDK
   shouldn't need Go installed. Go devs working on the TUI shouldn't
   need Python.
4. **Reusability.** A standalone Go package is consumable by anyone
   building an agent client (LangChain, Anthropic SDK, custom), not just
   agentic-patterns users.
5. **Release cadence independence.** The TUI and the SDKs can evolve at
   different speeds without gating each other.
6. **Masking doesn't require monorepo.** The user-facing experience
   remains `pip install agentic-patterns` + `from agentic_patterns.tui
   import run_chat`. The Python wheel bundles the Go binary at build
   time (exactly how `ruff` and `uv` ship Rust binaries inside Python
   wheels). The Go source lives in a separate repo; the binary is
   fetched from GH Releases during wheel builds.

The one tradeoff — coordinated protocol changes across repos — is
manageable via protocol versioning (see stdio protocol section below).

## Architecture

```
┌─ github.com/ORG/agentic-tui (Go, MIT) ──────────────────┐
│  - Terminal chat rendering + streaming                  │
│  - Two driver modes:                                    │
│    • HTTP mode (connects to remote backend)             │
│    • Stdio mode (reads SSE from stdin, writes JSON      │
│      user events to stdout) ← NEW                       │
│  - Exports a Client interface; ships HTTPClient,        │
│    StdioClient, StubClient, DemoClient                  │
│  - Releases: GitHub Releases with per-platform binaries │
│    (darwin-arm64, darwin-amd64, linux-amd64,            │
│     linux-arm64, windows-amd64)                         │
└─────────────────────────────────────────────────────────┘
          ▲                                   ▲
          │ stdio protocol                    │ Go import or HTTP
          │                                   │
┌─────────┴──────────────┐          ┌─────────┴─────────────┐
│  agentic-patterns      │          │  stack-bench          │
│  (Python)              │          │  (Go)                 │
│                        │          │                       │
│  agentic_patterns.tui. │          │  Imports              │
│    run_chat(agent=...) │          │  github.com/ORG/      │
│                        │          │  agentic-tui          │
│  - Ships the binary    │          │                       │
│    inside the wheel    │          │  Uses HTTPClient      │
│    (build hook fetches │          │  mode against its     │
│    from GH Releases)   │          │  own REST backend     │
│  - Spawns binary,      │          │                       │
│    pipes SSE via stdin │          │                       │
│  - Reads user input    │          │                       │
│    events via stdout   │          │                       │
└────────────────────────┘          └───────────────────────┘
```

## Package structure

```
agentic-tui/
├── go.mod
├── README.md
├── LICENSE (MIT)
├── PROTOCOL.md              # stdio protocol specification
├── main.go                  # CLI entry: modes, flag parsing
├── chat/                    # top-level chat program
│   ├── app.go               # tea.Model, phases, agent selection
│   ├── model.go             # chat state (messages, streaming, spinners)
│   ├── view.go              # render pipeline, per-part dispatch
│   ├── message.go           # Message, MessagePart, ToolCallPart types
│   └── config.go            # Config struct for consumers
├── client/                  # Client interface + implementations
│   ├── client.go            # interface definition
│   ├── http.go              # HTTPClient — connects to a remote backend
│   ├── stdio.go             # StdioClient — SSE over stdin/stdout ← NEW
│   ├── stub.go              # StubClient — static responses
│   └── demo.go              # DemoClient — fixture replay
├── sse/                     # SSE types and parser
│   ├── events.go            # StreamChunk, ChunkType, event shapes
│   ├── parser.go            # ParseSSE, ChunkFromSSE
│   └── display_type.go      # DisplayType enum (generic/diff/code/bash)
├── components/
│   ├── atoms/               # TextBlock, Badge, CodeBlock, Spinner, ...
│   ├── molecules/           # DiffBlock, ToolCallBlock, StatusBar, ...
│   └── theme/               # Theme, dark/light, auto-detect
├── markdown/                # Custom goldmark renderer
├── spinners/                # Frame presets (re-exported from atoms)
├── demo/                    # Demo fixtures (optional subpackage)
│   └── fixtures/
│       ├── demo.json
│       ├── demo-parts.json
│       └── ...
└── _examples/
    ├── minimal/             # 10-line HTTP mode integration
    ├── stdio/               # stdio mode integration for SDK writers
    └── custom-backend/      # implementing the Client interface
```

## Core concepts

### Client interface

The single seam consumers bind to. A new implementation is all it takes
to drive the TUI from a different source (HTTP, stdio, gRPC, mocked).

```go
package client

type Client interface {
    ListAgents(ctx context.Context) ([]AgentSummary, error)
    CreateConversation(ctx context.Context, agentID string) (string, error)
    SendMessage(ctx context.Context, conversationID, content string) (<-chan sse.StreamChunk, error)
    ListConversations(ctx context.Context, agentName string) ([]Conversation, error)
    GetConversation(ctx context.Context, id string) (*ConversationDetail, error)
    BranchConversation(ctx context.Context, conversationID string, atSequence int) (*Conversation, error)
}
```

Any backend that emits the standard SSE event vocabulary can be wrapped
by implementing this interface. HTTP and stdio are the two modes we ship.

### The stdio protocol (new)

This is the critical new design artifact. The TUI becomes a pure
terminal frontend that can be driven over stdio by any SDK.

**Inbound (stdin → TUI): SSE frames, one event per frame.**

Standard SSE wire format:
```
event: agent.message.chunk
data: {"delta": "Hello"}

event: agent.tool.start
data: {"tool_call_id": "call_1", "tool_name": "read_file", "display_type": "code", "arguments": {"path": "main.go"}}

event: done
data: {}
```

**Outbound (TUI → stdout): JSON lines, one event per line.**

```
{"type": "user_message", "content": "fix the bug"}
{"type": "abort"}
{"type": "tool_approval", "tool_call_id": "call_1", "approved": true}
{"type": "exit"}
```

**Protocol handshake on startup:**

```
TUI prints to stdout on start:
{"type": "hello", "protocol_version": 1, "tui_version": "0.1.0"}

SDK replies to stdin:
{"type": "start", "agent_name": "...", "title": "...", "theme": "auto"}
```

**Protocol versioning:** The TUI reports `protocol_version` on startup.
SDKs pin a range and fail fast with a clear message if the binary is
incompatible. This is how we handle protocol evolution without coupling
release cycles.

**Events supported inbound:**
- `agent.message.start` — new message begins
- `agent.message.chunk` — streaming text delta
- `agent.message.complete` — message done + token counts
- `agent.reasoning` — thinking content
- `agent.tool.start` — tool call started (includes display_type)
- `agent.tool.end` — tool call finished (result or error)
- `agent.tool.rejected` — tool blocked by safety gate
- `agent.iteration.start` / `agent.iteration.end` — iteration markers
- `agent.error` — fatal agent error
- `done` — stream finished, ready for next user input

**Events supported outbound:**
- `user_message` — new message submitted
- `abort` — user pressed ctrl+c during streaming
- `exit` — user quit the TUI
- Future: `tool_approval`, `follow_up_action`, `file_attach`

### Display types

Stable enum that backends emit on tool events and the TUI uses for
dispatch. Keeping this defined in the package gives backends a
compile-target for valid values (rather than raw strings).

```go
package sse

type DisplayType string

const (
    DisplayGeneric DisplayType = "generic"
    DisplayDiff    DisplayType = "diff"
    DisplayCode    DisplayType = "code"
    DisplayBash    DisplayType = "bash"
)
```

Additional types can be added (`markdown`, `json`, `html`, etc.) as
renderers are built.

### Theme auto-detect

Queries the terminal via OSC 11 at startup. Unchanged from PR #198.

## Consumer experience

**Python (via SDK in agentic-patterns):**

```python
from agentic_patterns import tui

async def my_agent(message: str):
    yield {"type": "thinking", "content": "let me think..."}
    yield {"type": "text", "content": "The answer is 42"}

tui.run_chat(
    agent=my_agent,
    title="My Agent",
    theme="auto",
)
```

**Go (direct import of agentic-tui):**

```go
import "github.com/ORG/agentic-tui/chat"
import "github.com/ORG/agentic-tui/client"

func main() {
    cfg := chat.Config{
        Client: client.NewHTTPClient(os.Getenv("BACKEND_URL")),
        Theme:  chat.ThemeAuto,
    }
    model := chat.NewApp(cfg)
    tea.NewProgram(model).Run()
}
```

**Stack Bench (already has an HTTP backend):**

```go
import "github.com/ORG/agentic-tui/chat"
import "github.com/ORG/agentic-tui/client"

func main() {
    cli := client.NewHTTPClient(backendURL)
    model := chat.NewApp(chat.Config{Client: cli})
    tea.NewProgram(model).Run()
}
```

Stack-bench's `app/cli/main.go` becomes ~30 lines of wiring. All of
`app/cli/internal/*` is deleted. `packages/agent-tui/` is deleted.

## Implementation phases

| Phase | What | Depends On |
|-------|------|------------|
| 0 | Decide repo name and GitHub org | -- |
| 1 | Bootstrap agentic-tui repo (go.mod, CI, README, LICENSE) | 0 |
| 2 | Port foundation: atoms, theme, markdown renderer, SSE types | 1 |
| 3 | Port molecules and chat: DiffBlock, ToolCallBlock, chat model | 2 |
| 4 | Port spinners and polish: dual spinners, graduation, status bar | 3 |
| 5 | Implement stdio protocol: StdioClient, protocol handshake | 4 |
| 6 | Write PROTOCOL.md specification | 5 |
| 7 | Tag v0.1.0, publish GitHub Release with platform binaries | 6 |
| 8 | Python SDK in agentic-patterns: `tui.run_chat` wrapper | 7 |
| 9 | Python wheel build hook: fetch binary from GH Releases | 8 |
| 10 | Stack-bench integration: delete internal, import package | 7 |
| 11 | Close PR #198, move issues #199/#200 to agentic-tui | 10 |

## Phase details

### Phase 1: Bootstrap

- `go mod init github.com/ORG/agentic-tui`
- GitHub Actions: `go test ./...`, `go vet ./...`, `go build ./...` on
  pushes and PRs
- Release workflow on tag push: build for 5 platforms, upload binaries
  to GH Releases
- README with the minimal integration example
- MIT LICENSE

### Phases 2–4: Code port

Use PR #198 as the source. For each commit on the branch, port the
relevant files into the new layout. Rename imports from
`github.com/dugshub/stack-bench/app/cli/internal/*` to the new package
paths. Tests come along for the ride.

Files to port (grouped):

**atoms:** `textblock.go`, `badge.go`, `icon.go`, `separator.go`,
`codeblock.go`, `highlight.go`, `spinner.go`, `confirmprompt.go`,
`radioselect.go`

**molecules:** `messageblock.go`, `toolcallblock.go`, `diffblock.go`,
`diffparser.go`, `errorblock.go`, `statusbar.go`, `header.go`,
`table.go`

**theme:** `theme.go`, `themes.go`, `registry.go`, `loader.go` + embed

**markdown:** `goldmark.go` (custom renderer)

**chat:** `model.go`, `view.go`, `input.go` (keystroke handlers)

**sse:** merged from `api/sse.go` and `api/client.go` DTOs

**client:** refactored from `api/client.go` — split HTTPClient from
StubClient from the interface

### Phase 5: Stdio client

~200 lines. Reads SSE from stdin with the existing `ParseSSE` parser,
writes `{"type":"user_message",...}` JSON lines to stdout. No
networking code.

The handshake: on Init, TUI writes `{"type":"hello",...}` to stdout and
waits for `{"type":"start",...}` on stdin. Once the SDK confirms the
protocol version, normal streaming begins.

### Phase 6: PROTOCOL.md

A stable reference document committed alongside the code. Versioned in
sync with the TUI binary version. SDK authors bind to this, not to the
Go source.

### Phase 7: Release v0.1.0

GitHub Release workflow builds static binaries for:
- darwin-arm64, darwin-amd64
- linux-amd64, linux-arm64
- windows-amd64

Tag `v0.1.0`. Binaries attached to the release. README points users to
the release page for direct downloads.

### Phases 8–9: Python SDK

In `agentic-patterns`, add a `tui` subpackage:

```
agentic_patterns/tui/
├── __init__.py
├── runner.py       # tui.run_chat implementation
├── protocol.py     # SSE event builders, JSON line decoder
└── _binary.py      # locates the bundled agentic-tui binary
```

Wheel build hook (in `pyproject.toml` or `setup.py`) fetches the binary
from `https://github.com/ORG/agentic-tui/releases/download/v0.1.0/...`
at build time, bundles it into the platform-specific wheel. Users do
`pip install agentic-patterns` — wheel includes the right binary for
their platform.

### Phase 10: Stack-bench integration

In stack-bench:
- Add `github.com/ORG/agentic-tui` to `app/cli/go.mod`
- Replace `app/cli/main.go` with a ~30-line wrapper that constructs an
  `HTTPClient` pointing at stack-bench's backend and starts the TUI
- `git rm -rf app/cli/internal/` — all of it, no survivors
- `git rm -rf packages/agent-tui/` — the rushed extraction
- Verify `just demo` and `just run` still work

### Phase 11: Close out

- PR #198 closed with a comment linking to the new repo and this spec
- Issue #199 (interactive parts) cloned into agentic-tui's issue tracker
- Issue #200 (word-level diff) cloned into agentic-tui's issue tracker
- This spec moved to `docs/specs/archive/` in stack-bench, marked
  `status: implemented`
- `docs/specs/2026-03-22-message-parts.md` updated with a note that the
  implementation lives in `agentic-tui` now

## Migration notes for stack-bench

Stack-bench's cli remains a Go binary. It just imports instead of
implementing. The contract with the backend doesn't change —
stack-bench's REST API still emits the same SSE events, the TUI
consumes them via its `HTTPClient`. Nothing about agentic-patterns'
event vocabulary changes.

The one behavioral shift: stack-bench CLI gets new features (stdio
mode, etc.) automatically as agentic-tui evolves. Stack-bench pins a
specific version in its `go.mod` and bumps when ready.

## Open questions

1. **Repo name.** Candidates: `agentic-tui`, `pattern-tui`,
   `chat-tui`, `bubble-agent`, `termchat`. My lean is `agentic-tui`
   for brand consistency with agentic-patterns.

2. **GitHub org.** `dugshub`? `pattern-stack`? New org? Decides the
   import path.

3. **License.** MIT matches lipgloss/bubbletea/goldmark. Confirm.

4. **Protocol version 1 cut line.** Should the v1 protocol include
   `tool_approval` and follow-up action events, or ship without them
   and add in v2? Ship v1 minimal is my vote — approval can follow.

5. **Demo mode in the stdio protocol.** Should the TUI be able to
   replay a demo fixture over stdio for testing? Probably yes — SDK
   authors want end-to-end tests without real agents.

6. **Binary distribution.** Should we also publish to Homebrew and
   apt? Nice to have, not v1-blocking.

7. **Python wheel build tool.** `hatch-binary-bundle` doesn't exist.
   Options:
   - Custom `hatch_build.py` that downloads from GH Releases
   - Fork or adapt an existing Python+Rust tool (`maturin`) for Go
   - Use `cibuildwheel` with a pre-install hook
   This needs prototyping.

8. **Display type extensibility.** Should backends be able to declare
   custom display types that map to renderers registered at runtime,
   or is the enum locked to the built-in set? Locked v1, pluggable v2.

9. **Bubbletea v2 stability.** We're pinning `charm.land/bubbletea/v2`
   which is still pre-v1.0. Risk of breaking changes upstream. Pin
   carefully.

## Reference: PR #198 commits (the feature spec)

```
4a029f6 feat(cli): dual spinners, graduated tool calls, generic status bar
424343d feat(cli): spinner presets, gallery, and theme auto-detect
6016f48 feat(cli): polish chat rendering — alignment, colors, spinner
8065c0a refactor(cli): structured diff input for DiffBlock
88c67df revert(cli): roll back word-level diff highlights
1a4d896 feat(cli): word-level diff highlights via diff-match-patch
1a4043d feat(cli): syntax-highlight code tool results via chroma lexer match
aba3580 feat(cli): animated spinner, display-type dispatch, structured demo
d209a07 test(cli): add part-aware message model tests
9755a52 feat(cli): part-aware message model and per-part rendering
02f800e feat(backend): enrich tool SSE events with display_type hint
e6e50eb feat(cli): enrich StreamChunk with structured tool data
d0f5ebc docs: add message parts spec (EP-008)
```

Each commit maps to one or more items in the feature inventory. When
porting in phases 2–4, work commit by commit rather than file by file.
