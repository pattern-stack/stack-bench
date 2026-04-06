---
title: "Extract agent-tui: A Generic Go Package for Agent TUI Applications"
date: 2026-04-04
status: draft
branch:
depends_on: []
adrs: [ADR-001]
---

# Extract agent-tui: A Generic Go Package for Agent TUI Applications

## Goal

Extract the Stack Bench Go CLI into a reusable, importable Go package called `agent-tui` (packaged within the agentic-patterns monorepo) that any developer can use to build a terminal-based agent interface for their Python, TypeScript, Go, or any-language backend. The backend communicates over **two supported transports**: HTTP/SSE (for backends with a web server) and JSON-RPC over stdio (for scripts and CLIs with no server). Consumers `go get` the package, write ~50 lines of configuration, and get a production-quality agent TUI with streaming chat, slash commands, markdown rendering, theming, and optional local service management.

## Problem Statement

The Stack Bench CLI at `app/cli/` contains approximately 5,400 lines of Go code (including tests). Of this, roughly 98% is generic agent TUI infrastructure: SSE parsing, streaming chat with multipart messages (text, thinking, tool calls), a slash command system with autocomplete, a theme/design-token system, markdown-to-terminal rendering, service lifecycle management, and a component library (atoms + molecules) with comprehensive tests. Only 2% is Stack-Bench-specific: the backend directory discovery heuristic, the `"STACK BENCH"` branding, the `SB_BACKEND_URL` environment variable name, and the `"sb:"` assistant label.

This package extraction enables:

1. **The `agent-tui` package** (built in stack-bench, relocatable to agentic-patterns or standalone later) -- anyone building an AI agent with any backend can get a polished TUI in minutes.
2. **Stack Bench itself becomes a thin consumer** -- `app/cli/main.go` shrinks to configuration only.
3. **Other projects at dugshub** (pattern-stack dev tools, agentic-patterns demos) can reuse the same TUI.
4. **Two transport options** -- HTTP/SSE for web-server-backed agents, JSON-RPC over stdio for scripts and CLIs with no server.

## Analysis: What Is Generic vs. What Is Stack-Bench-Specific

### Generic (moves to `agent-tui` package)

| Package | Files | Lines | What It Does |
|---------|-------|-------|-------------|
| `api/` | `client.go`, `types.go`, `sse.go`, `sse_test.go` | ~905 | HTTP client interface, SSE parser, stream chunk types |
| `chat/` | `model.go`, `view.go`, `input.go`, `picker.go`, `model_test.go` | ~1,216 | Chat model with multipart messages, streaming, conversation picker |
| `command/` | `registry.go`, `commands.go`, `parse.go` | ~338 | Slash command registry, parser with quoted strings, fuzzy suggest |
| `service/` | `manager.go`, `node.go`, `local.go` | ~317 | Service lifecycle management (start, stop, health check) |
| `ui/` | `markdown.go`, `markdown_test.go` | ~378 | Streaming markdown renderer |
| `ui/autocomplete/` | `autocomplete.go` | ~167 | Autocomplete dropdown for slash commands |
| `ui/theme/` | `theme.go`, `themes.go`, `tokens.go`, `registry.go` | ~229 | Design token system, theme registry |
| `ui/components/atoms/` | 16 files (8 source + 8 test) | ~880 | TextBlock, CodeBlock, Badge, Icon, Separator, Spinner, InlineCode |
| `ui/components/molecules/` | 7 files (4 source + 3 test) | ~750 | StatusBlock, ToolCallBlock, DiffBlock |
| `app/` | `model.go` | ~292 | Top-level Bubble Tea model with phases |

**Total generic: ~5,472 lines (including tests), ~3,250 source-only**

### Stack-Bench-Specific (stays in `app/cli/`)

| Code | What | How It Becomes Generic |
|------|------|----------------------|
| `main.go` `findBackendDir()` | Locates `../backend` relative to executable | Consumer provides their own `ServiceNode` or just a URL |
| `main.go` `SB_BACKEND_URL` env var | Environment variable name | Consumer configures the env var name (or hardcodes a URL) |
| `"STACK BENCH"` in `model.go` | App title branding | Consumer sets `Config.AppName` |
| `"sb:"` prefix in `chat/view.go` | Assistant message prefix | Consumer sets `Config.AssistantLabel` |
| `NewLocalService` uvicorn command | `uv run uvicorn organisms.api.app:app` | Consumer provides their own `ServiceNode` implementation |
| Default commands (`/agents`, `/clear`, `/help`, `/quit`) | Built-in command set | Package provides these as defaults; consumer can override |

## HTTP/SSE Backend Contract

This is the critical interface that makes `agent-tui` language-agnostic. Any backend that implements these endpoints works with the TUI. The contract is intentionally minimal -- five endpoints, two of which are optional.

### Required Endpoints

#### 1. List Agents

```
GET /agents
Accept: application/json

Response 200:
[
  {
    "id": "architect",
    "name": "Architect",
    "role": "Plans and designs systems",
    "model": "claude-sonnet-4-20250514"     // optional
  }
]
```

Returns the list of available agents. The `id` field is used as the agent identifier in subsequent API calls. The `name` field is the human-readable display name. The `role` field is a short description shown in the agent picker. The `model` field is optional metadata.

If the backend does not have an agent concept, it can return a single agent:

```json
[{"id": "default", "name": "Assistant", "role": "General purpose assistant"}]
```

#### 2. Create Conversation

```
POST /conversations
Content-Type: application/json
Accept: application/json

Request:
{
  "agent_id": "architect",
  "model": "claude-sonnet-4-20250514"       // optional override
}

Response 201:
{
  "id": "conv-abc123",
  "agent_id": "architect",
  "created_at": "2026-04-04T12:00:00Z"
}
```

Creates a new conversation session. The returned `id` is used for all subsequent message sends.

**Field name note:** The canonical contract uses `agent_id` throughout. The current Stack Bench backend uses `agent_name`. The `HTTPClient` handles this mapping internally via wire-format types (see Phase 2). Third-party backends implementing the contract fresh should use `agent_id`.

#### 3. Send Message (SSE Stream)

```
POST /conversations/{id}/messages
Content-Type: application/json
Accept: text/event-stream

Request:
{
  "content": "What should the architecture look like?"
}

Note: The current Stack Bench backend uses `/conversations/{id}/send` with
`{"message": "..."}`. The canonical contract above uses `/conversations/{id}/messages`
with `{"content": "..."}`. The migration (Phase 5) updates the backend to match.
The HTTPClient's EndpointConfig allows overriding the path for backward compatibility.

Response 200: text/event-stream
```

This is the core endpoint. The response is a Server-Sent Events stream. The TUI reads this stream and renders content progressively.

**SSE Event Types:**

| Event Type | Data Schema | Description |
|-----------|------------|-------------|
| `message.delta` | `{"delta": "partial text"}` | Incremental text content. Concatenate deltas to build the full response. |
| `message.complete` | `{"content": "full text", "input_tokens": 100, "output_tokens": 50}` | Signals completion. Content field is informational (already streamed via deltas). Tokens are optional. |
| `thinking` | `{"content": "reasoning text"}` | Extended thinking / chain-of-thought content. Rendered collapsed in the TUI. |
| `tool.start` | `{"id": "tc-123", "name": "read_file", "input": "path=/foo", "display_type": "code"}` | A tool invocation has begun. The TUI shows a running indicator. |
| `tool.end` | `{"id": "tc-123", "name": "read_file", "output": "file contents", "error": "", "display_type": "code", "duration_ms": 150}` | A tool invocation has completed. The TUI updates the indicator and optionally shows the result. |
| `error` | `{"type": "rate_limit", "message": "Too many requests"}` | A stream-level error. The TUI displays it and terminates the stream. |
| `done` | `{}` | Explicit stream termination signal. |

**SSE Wire Format:**

```
event: message.delta
data: {"delta": "Here is "}

event: message.delta
data: {"delta": "my response."}

event: thinking
data: {"content": "Let me consider the options..."}

event: tool.start
data: {"id": "tc-1", "name": "read_file", "input": "path=main.go", "display_type": "code"}

event: tool.end
data: {"id": "tc-1", "name": "read_file", "output": "package main\n...", "display_type": "code", "duration_ms": 45}

event: message.complete
data: {"content": "Here is my response.", "input_tokens": 50, "output_tokens": 12}

```

**Display Types** for tool events control how the TUI renders tool results:

| Display Type | Rendering |
|-------------|-----------|
| `"diff"` | Colored unified diff with add/remove markers |
| `"code"` | Syntax-highlighted code block with gutter |
| `"bash"` | Terminal output style (monospace, gutter) |
| `"generic"` | Plain text, truncated to 200 chars |
| `""` (empty) | Same as `"generic"` |

**Backward Compatibility Aliases:**

The TUI also accepts these legacy event names for backward compatibility with existing backends:

| Legacy Event | Maps To |
|-------------|---------|
| `agent.message.chunk` | `message.delta` |
| `agent.message.complete` | `message.complete` |
| `agent.reasoning` | `thinking` |
| `agent.tool.start` | `tool.start` |
| `agent.tool.end` | `tool.end` |
| `agent.error` | `error` |

Backends can use either naming convention. The SSE parser handles both.

### Optional Endpoints

#### 4. List Conversations (Optional)

```
GET /conversations?agent_id=architect
Accept: application/json

Response 200:
[
  {
    "id": "conv-abc123",
    "agent_id": "architect",
    "state": "active",
    "exchange_count": 5,
    "created_at": "2026-04-04T12:00:00Z",
    "updated_at": "2026-04-04T12:30:00Z"
  }
]
```

If implemented, the TUI shows a conversation picker before starting a new chat. If the endpoint returns 404, the TUI skips the picker and always creates new conversations.

#### 5. Health Check (Optional)

```
GET /health

Response 200:
{"status": "ok"}
```

Used by the service manager to determine when a locally-started backend is ready. If the backend is remote, this endpoint is not needed.

### Contract Validation

The package includes a `contracttest` subpackage that backends can use to validate their implementation:

```go
import "github.com/dugshub/agent-tui/contracttest"

func TestBackendContract(t *testing.T) {
    contracttest.ValidateBackend(t, "http://localhost:8000")
}
```

This runs a standard test suite: list agents, create conversation, send message, validate SSE event format, check error handling.

## JSON-RPC over stdio Transport

The second supported transport. For backends that are scripts or CLI tools with no web server — the TUI spawns the backend as a subprocess and communicates via stdin/stdout using the [JSON-RPC 2.0](https://www.jsonrpc.org/specification) protocol.

### Why JSON-RPC (not raw stdio)

Raw stdin/stdout would require inventing ad-hoc message framing, error formats, and request correlation — effectively a worse JSON-RPC. JSON-RPC provides all of this as a standard, has libraries in every language, and aligns with MCP (Model Context Protocol) which uses the same wire format.

### Wire Format

The TUI writes JSON-RPC **requests** to the subprocess's stdin (one JSON object per line). The subprocess writes JSON-RPC **responses** and **notifications** to stdout (one JSON object per line).

Streaming is implemented via JSON-RPC **notifications** (no `id` field, no response expected) — the same event types as SSE, but wrapped in JSON-RPC envelope.

### Methods

#### `listAgents` (request → response)

```json
--> {"jsonrpc": "2.0", "method": "listAgents", "id": 1}
<-- {"jsonrpc": "2.0", "result": [{"id": "default", "name": "Assistant", "role": "General purpose"}], "id": 1}
```

#### `createConversation` (request → response)

```json
--> {"jsonrpc": "2.0", "method": "createConversation", "params": {"agent_id": "default"}, "id": 2}
<-- {"jsonrpc": "2.0", "result": {"id": "conv-1", "agent_id": "default"}, "id": 2}
```

#### `sendMessage` (request → streaming notifications → completion response)

```json
--> {"jsonrpc": "2.0", "method": "sendMessage", "params": {"conversation_id": "conv-1", "content": "Hello"}, "id": 3}
<-- {"jsonrpc": "2.0", "method": "stream.event", "params": {"type": "message.delta", "data": {"delta": "Hi "}}}
<-- {"jsonrpc": "2.0", "method": "stream.event", "params": {"type": "message.delta", "data": {"delta": "there!"}}}
<-- {"jsonrpc": "2.0", "method": "stream.event", "params": {"type": "thinking", "data": {"content": "The user greeted me."}}}
<-- {"jsonrpc": "2.0", "method": "stream.event", "params": {"type": "tool.start", "data": {"id": "tc-1", "name": "search", "input": "query=hello"}}}
<-- {"jsonrpc": "2.0", "method": "stream.event", "params": {"type": "tool.end", "data": {"id": "tc-1", "name": "search", "output": "results..."}}}
<-- {"jsonrpc": "2.0", "method": "stream.event", "params": {"type": "done", "data": {}}}
<-- {"jsonrpc": "2.0", "result": {"status": "complete"}, "id": 3}
```

The `stream.event` notifications use the **same event types and data schemas** as the SSE transport (`message.delta`, `thinking`, `tool.start`, `tool.end`, `error`, `done`). This means backend developers learn one set of event types regardless of transport.

The final response (with matching `id`) signals the stream is complete. The TUI considers the exchange done when it receives either a `done` notification or the response — whichever comes first.

#### `listConversations` (optional, request → response)

```json
--> {"jsonrpc": "2.0", "method": "listConversations", "params": {"agent_id": "default"}, "id": 4}
<-- {"jsonrpc": "2.0", "result": [...], "id": 4}
```

If the backend doesn't support this, it returns a JSON-RPC error with code `-32601` (Method not found). The TUI skips the picker.

### Error Handling

Backends signal errors using standard JSON-RPC error responses:

```json
<-- {"jsonrpc": "2.0", "error": {"code": -32603, "message": "Model rate limited"}, "id": 3}
```

Or via a `stream.event` notification with type `error` (same as SSE):

```json
<-- {"jsonrpc": "2.0", "method": "stream.event", "params": {"type": "error", "data": {"type": "rate_limit", "message": "Too many requests"}}}
```

### Process Lifecycle

1. TUI spawns the subprocess via `exec.Command` with the configured command + args
2. TUI sends JSON-RPC requests to stdin
3. Backend writes JSON-RPC responses/notifications to stdout
4. Backend's stderr is captured and displayed on error (not part of the protocol)
5. On TUI quit: TUI closes stdin, waits 5s for graceful exit, then sends SIGTERM

### Minimal Python Backend Example (stdio)

```python
#!/usr/bin/env python3
"""Minimal agent-tui stdio backend. Zero dependencies."""
import sys, json

def handle(method, params, req_id):
    if method == "listAgents":
        return {"result": [{"id": "default", "name": "Assistant", "role": "Helpful assistant"}], "id": req_id}
    elif method == "createConversation":
        return {"result": {"id": "conv-1", "agent_id": params.get("agent_id", "default")}, "id": req_id}
    elif method == "sendMessage":
        content = params["content"]
        # Stream notifications
        for word in f"You said: {content}".split():
            notify({"type": "message.delta", "data": {"delta": word + " "}})
        notify({"type": "done", "data": {}})
        return {"result": {"status": "complete"}, "id": req_id}
    else:
        return {"error": {"code": -32601, "message": f"Method not found: {method}"}, "id": req_id}

def notify(params):
    write({"jsonrpc": "2.0", "method": "stream.event", "params": params})

def write(obj):
    print(json.dumps(obj), flush=True)

for line in sys.stdin:
    req = json.loads(line.strip())
    resp = handle(req["method"], req.get("params", {}), req.get("id"))
    if resp:
        write({"jsonrpc": "2.0", **resp})
```

### Minimal TypeScript Backend Example (stdio)

```typescript
#!/usr/bin/env npx tsx
/** Minimal agent-tui stdio backend. Zero dependencies beyond Node. */
import * as readline from 'readline';

const rl = readline.createInterface({ input: process.stdin });

function write(obj: any) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function notify(params: any) {
  write({ jsonrpc: '2.0', method: 'stream.event', params });
}

rl.on('line', (line) => {
  const req = JSON.parse(line);
  const { method, params = {}, id } = req;

  if (method === 'listAgents') {
    write({ jsonrpc: '2.0', result: [{ id: 'default', name: 'Assistant', role: 'Helpful' }], id });
  } else if (method === 'createConversation') {
    write({ jsonrpc: '2.0', result: { id: 'conv-1', agent_id: params.agent_id ?? 'default' }, id });
  } else if (method === 'sendMessage') {
    for (const word of `You said: ${params.content}`.split(' ')) {
      notify({ type: 'message.delta', data: { delta: word + ' ' } });
    }
    notify({ type: 'done', data: {} });
    write({ jsonrpc: '2.0', result: { status: 'complete' }, id });
  } else {
    write({ jsonrpc: '2.0', error: { code: -32601, message: `Unknown: ${method}` }, id });
  }
});
```

## Package Architecture

### Module Path

```
github.com/dugshub/agent-tui
```

### Directory Layout

```
agent-tui/
  go.mod
  go.sum
  README.md
  LICENSE

  # --- Public API (exported) ---
  tui.go                    # Main entry point: New(), Run(), Config
  config.go                 # Configuration types
  client.go                 # Client interface (exported)
  types.go                  # Shared types: AgentSummary, StreamChunk, ChunkType, etc.
  command.go                # Command types: Def, ParseResult, Registry (exported)
  service.go                # ServiceNode interface, ServiceManager (exported)
  theme.go                  # Theme, Style, token types (exported)

  # --- Internal implementation ---
  internal/
    sse/
      parse.go              # SSE parser (ParseSSE, ChunkFromSSE)
      parse_test.go
    chat/
      model.go              # Chat model (messages, streaming, parts)
      view.go               # Chat rendering
      input.go              # Input editing helpers
      picker.go             # Conversation picker
      model_test.go
    app/
      model.go              # Top-level Bubble Tea model (phases, routing)
    ui/
      markdown.go           # Markdown-to-terminal renderer
      markdown_test.go
      autocomplete/
        autocomplete.go     # Autocomplete dropdown
      theme/
        resolve.go          # Theme resolution (internal, delegates to public Theme)
        builtin.go          # Built-in dark/light themes
      components/
        atoms/
          atoms.go          # RenderContext, shared types
          textblock.go
          codeblock.go
          inlinecode.go
          separator.go
          spinner.go
          badge.go
          icon.go
        molecules/
          molecules.go
          statusblock.go
          toolcallblock.go
          diffblock.go
    command/
      registry.go           # Internal registry implementation
      parse.go              # Parser implementation
    service/
      manager.go            # ServiceManager implementation
      local.go              # LocalService (exec-based, for local backends)
    httpclient/
      client.go             # HTTPClient implementation of the Client interface
      stub.go               # StubClient for testing/demo
      client_test.go
    stdioclient/
      client.go             # StdioClient: JSON-RPC over stdin/stdout
      jsonrpc.go            # JSON-RPC 2.0 framing (read/write/notifications)
      client_test.go

  # --- Test utilities (exported) ---
  contracttest/
    validate.go             # Backend contract validation test helpers
    validate_test.go

  # --- Examples ---
  _examples/
    minimal/
      main.go               # ~30 lines: connect to remote backend
    local-python/
      main.go               # ~50 lines: auto-start a Python backend
      backend/              # Tiny Flask SSE backend for demo
    custom-theme/
      main.go               # Custom theme example
    custom-commands/
      main.go               # Custom slash commands example
    stdio-python/
      main.go               # ~20 lines: spawn a Python script via JSON-RPC stdio
      agent.py              # Minimal Python stdio backend (zero deps)
    stdio-typescript/
      main.go               # ~20 lines: spawn a TS script via JSON-RPC stdio
      agent.ts              # Minimal TypeScript stdio backend (zero deps)
```

### Public API Surface

The public API is designed for minimal boilerplate. A consumer should be able to get a working TUI in under 50 lines.

#### Core Types (exported from root package)

```go
package tui

// --- Configuration ---

// Config configures an agent-tui instance.
type Config struct {
    // AppName is displayed in headers and the agent picker. Required.
    AppName string

    // AssistantLabel is the prefix shown before assistant messages (e.g., "ai:", "claude:").
    // Defaults to the lowercase AppName + ":" if empty.
    AssistantLabel string

    // Backend specifies how to connect to the backend.
    // Exactly one of BackendURL, BackendService, or BackendStdio must be set.
    BackendURL     string       // HTTP/SSE: Direct URL (e.g., "http://localhost:8000")
    BackendService ServiceNode  // HTTP/SSE: Auto-managed local service
    BackendStdio   *StdioConfig // JSON-RPC: Spawn subprocess, communicate via stdin/stdout

    // EnvOverride is the environment variable name that overrides BackendURL.
    // When set and the env var is non-empty, its value is used as BackendURL.
    // Defaults to "" (no env override).
    EnvOverride string

    // Theme is the initial theme. Defaults to DarkTheme() if nil.
    Theme *Theme

    // Commands are additional slash commands to register.
    // Built-in commands (/help, /clear, /quit) are always registered.
    // Custom commands with the same name as a built-in override the built-in.
    Commands []CommandDef

    // Endpoints allows overriding the default API path structure.
    // Nil means use defaults (/agents, /conversations, etc.).
    Endpoints *EndpointConfig

    // OnReady is called after the backend is connected and agents are loaded.
    // Useful for logging or telemetry. Optional.
    OnReady func(agents []AgentSummary)
}

// EndpointConfig allows customizing the API path structure.
// All fields default to the standard contract paths if empty.
type EndpointConfig struct {
    ListAgents         string // default: "/agents"
    CreateConversation string // default: "/conversations"
    SendMessage        string // default: "/conversations/{id}/messages"
    ListConversations  string // default: "/conversations"
    GetConversation    string // default: "/conversations/{id}"
    Health             string // default: "/health"
}

// --- Entry Points ---

// New creates a configured TUI application.
// Call Run() to start it.
func New(cfg Config) (*App, error)

// App is a configured TUI application.
type App struct { /* unexported fields */ }

// Run starts the TUI. Blocks until the user quits.
// Returns nil on clean exit.
func (a *App) Run() error

// --- Client Interface ---

// Client defines the interface for communicating with an agent backend.
// The package provides HTTPClient (HTTP/SSE), StdioClient (JSON-RPC over stdin/stdout),
// and StubClient (testing). Consumers can implement this for custom transports.
//
// The first three methods are required. ListConversations is optional -- if the
// backend does not support it, return (nil, nil) and the TUI skips the picker.
// GetConversation is optional -- used to hydrate full message history when
// continuing an existing conversation. Return (nil, nil) to skip hydration.
type Client interface {
    ListAgents(ctx context.Context) ([]AgentSummary, error)
    CreateConversation(ctx context.Context, agentID string) (string, error)
    SendMessage(ctx context.Context, conversationID string, content string) (<-chan StreamChunk, error)
    ListConversations(ctx context.Context, agentName string) ([]Conversation, error)
    GetConversation(ctx context.Context, id string) (*ConversationDetail, error)
}

// NewHTTPClient creates a Client that communicates over HTTP/SSE.
func NewHTTPClient(baseURL string, endpoints *EndpointConfig) Client

// NewStubClient creates a Client that returns canned responses.
// Useful for development without a backend.
func NewStubClient() Client

// --- Agent & Conversation Types ---

type AgentSummary struct {
    ID    string `json:"id"`
    Name  string `json:"name"`
    Role  string `json:"role"`
    Model string `json:"model,omitempty"`
}

type Conversation struct {
    ID            string    `json:"id"`
    AgentID       string    `json:"agent_id"`
    State         string    `json:"state"`
    ExchangeCount int       `json:"exchange_count"`
    CreatedAt     time.Time `json:"created_at"`
    UpdatedAt     time.Time `json:"updated_at"`
}

// ConversationDetail is the full conversation with message history.
// Used by GetConversation to hydrate chat when continuing a conversation.
type ConversationDetail struct {
    ID            string                `json:"id"`
    AgentID       string                `json:"agent_id"`
    State         string                `json:"state"`
    ExchangeCount int                   `json:"exchange_count"`
    Messages      []ConversationMessage `json:"messages"`
    CreatedAt     time.Time             `json:"created_at"`
    UpdatedAt     time.Time             `json:"updated_at"`
}

type ConversationMessage struct {
    ID       string        `json:"id"`
    Kind     string        `json:"kind"`
    Sequence int           `json:"sequence"`
    Parts    []MessagePart `json:"parts"`
}

type MessagePart struct {
    Type    string  `json:"type"`
    Content *string `json:"content,omitempty"`
}

// --- Streaming Types ---

type ChunkType string

const (
    ChunkText      ChunkType = "text"
    ChunkThinking  ChunkType = "thinking"
    ChunkToolStart ChunkType = "tool_start"
    ChunkToolEnd   ChunkType = "tool_end"
)

type StreamChunk struct {
    Content     string
    Type        ChunkType
    Done        bool
    Error       error
    ToolCallID  string
    ToolName    string
    DisplayType string
    ToolInput   string
    ToolError   string
}

// --- Command System ---

// CommandDef defines a slash command.
type CommandDef struct {
    Name        string
    Aliases     []string
    Description string
    Category    string
    Hidden      bool
    Handler     CommandHandler
}

// CommandHandler is called when a slash command is executed.
type CommandHandler func(result CommandParseResult) tea.Cmd

// CommandParseResult holds the parsed output of a slash command.
type CommandParseResult struct {
    Command string
    Args    []string
    Flags   map[string]bool
    Options map[string]string
    Raw     string
}

// --- Service Management ---

// ServiceNode is a managed backend process.
// Implement this interface to auto-start your backend.
type ServiceNode interface {
    Name() string
    Start(ctx context.Context) error
    Stop() error
    Health() ServiceStatus
    CheckHealth() ServiceStatus
    BaseURL() string
}

type ServiceStatus int

const (
    StatusStopped ServiceStatus = iota
    StatusStarting
    StatusHealthy
    StatusUnhealthy
)

// ExecServiceConfig configures the built-in exec-based service node.
// This covers the common case of starting a backend via a shell command.
type ExecServiceConfig struct {
    Name       string   // Display name (e.g., "backend")
    Command    string   // Executable (e.g., "python", "node", "go")
    Args       []string // Arguments (e.g., ["-m", "uvicorn", "app:app"])
    Dir        string   // Working directory
    Host       string   // Defaults to "127.0.0.1"
    Port       int      // Defaults to 8000
    HealthPath string   // Defaults to "/health"
    Env        []string // Additional environment variables ("KEY=VALUE")
}

// NewExecService creates a ServiceNode that starts a process via exec.
func NewExecService(cfg ExecServiceConfig) ServiceNode

// --- stdio Transport ---

// StdioConfig configures a JSON-RPC over stdio backend connection.
// The TUI spawns the command as a subprocess and communicates via stdin/stdout.
type StdioConfig struct {
    Command string   // Executable (e.g., "python", "node", "npx")
    Args    []string // Arguments (e.g., ["agent.py"] or ["tsx", "agent.ts"])
    Dir     string   // Working directory (optional)
    Env     []string // Additional environment variables ("KEY=VALUE")
}

// NewStdioClient creates a Client that communicates via JSON-RPC over stdin/stdout.
// Used internally when Config.BackendStdio is set. Exported for advanced use.
func NewStdioClient(cfg StdioConfig) (Client, error)

// --- Theme System ---

// Theme maps design tokens to terminal styles.
type Theme struct {
    Name       string
    Categories [8]color.Color
    Statuses   [7]color.Color
    Foreground color.Color
    Background color.Color
    DimColor   color.Color
}

// Style composes token dimensions into a styling intent.
type Style struct {
    Category  Category
    Hierarchy Hierarchy
    Emphasis  Emphasis
    Status    Status
}

// Category, Hierarchy, Emphasis, Status enums are exported.
// DarkTheme() and LightTheme() are exported factory functions.

func DarkTheme() *Theme
func LightTheme() *Theme
```

#### Minimal Consumer Example

```go
package main

import (
    "fmt"
    "os"

    tui "github.com/dugshub/agent-tui"
)

func main() {
    app, err := tui.New(tui.Config{
        AppName:    "My Agent",
        BackendURL: "http://localhost:8000",
    })
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
    if err := app.Run(); err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
}
```

#### Local Backend Example

```go
package main

import (
    "fmt"
    "os"

    tui "github.com/dugshub/agent-tui"
)

func main() {
    app, err := tui.New(tui.Config{
        AppName:     "My Agent",
        EnvOverride: "MY_AGENT_URL",
        BackendService: tui.NewExecService(tui.ExecServiceConfig{
            Name:    "backend",
            Command: "python",
            Args:    []string{"-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"},
            Dir:     "./backend",
            Port:    8000,
        }),
    })
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
    if err := app.Run(); err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
}
```

#### Custom Commands Example

```go
app, err := tui.New(tui.Config{
    AppName:    "My Agent",
    BackendURL: "http://localhost:8000",
    Commands: []tui.CommandDef{
        {
            Name:        "deploy",
            Aliases:     []string{"d"},
            Description: "Deploy the current project",
            Category:    "operations",
            Handler: func(result tui.CommandParseResult) tea.Cmd {
                // Custom logic here
                return nil
            },
        },
    },
})
```

#### stdio Backend Example (Python)

```go
app, err := tui.New(tui.Config{
    AppName: "My Agent",
    BackendStdio: &tui.StdioConfig{
        Command: "python",
        Args:    []string{"agent.py"},
        Dir:     "./backend",
    },
})
```

#### stdio Backend Example (TypeScript)

```go
app, err := tui.New(tui.Config{
    AppName: "My Agent",
    BackendStdio: &tui.StdioConfig{
        Command: "npx",
        Args:    []string{"tsx", "agent.ts"},
        Dir:     "./backend",
    },
})
```

## Extension Points

### 1. Custom Commands

Consumers register `CommandDef` entries via `Config.Commands`. These are merged with the built-in commands (`/help`, `/clear`, `/quit`). If a custom command has the same name as a built-in, the custom command wins, allowing full override of default behavior.

The command handler receives a `CommandParseResult` with the parsed command name, positional args, flags (`-f`), and options (`--key=val`). It returns a `tea.Cmd` which is executed by the Bubble Tea runtime.

### 2. Custom Themes

Consumers provide a `*Theme` via `Config.Theme`. The theme defines colors for 8 semantic categories, 7 status states, plus foreground/background/dim. The built-in `DarkTheme()` and `LightTheme()` are exported so consumers can use them as a starting point and modify specific colors.

```go
myTheme := tui.DarkTheme()
myTheme.Name = "nord"
myTheme.Categories[tui.CatAgent] = lipgloss.Color("#88C0D0")
// ... customize other colors ...

app, _ := tui.New(tui.Config{
    AppName: "My Agent",
    Theme:   myTheme,
    // ...
})
```

### 3. Custom Service Nodes

The `ServiceNode` interface is exported. Consumers implement it for non-exec backends (Docker containers, cloud services, etc.):

```go
type DockerService struct { /* ... */ }
func (d *DockerService) Name() string           { return "backend" }
func (d *DockerService) Start(ctx context.Context) error { /* docker compose up */ }
func (d *DockerService) Stop() error            { /* docker compose down */ }
func (d *DockerService) Health() tui.ServiceStatus { /* ... */ }
func (d *DockerService) CheckHealth() tui.ServiceStatus { /* docker inspect */ }
func (d *DockerService) BaseURL() string        { return "http://localhost:8000" }
```

### 4. Custom Client Implementations

The `Client` interface is exported. The package ships with three implementations: `HTTPClient` (HTTP/SSE), `StdioClient` (JSON-RPC over stdio), and `StubClient` (testing). Consumers can implement the interface for other transports (WebSocket, gRPC, in-process function calls):

```go
type InProcessClient struct {
    agent *myagent.Agent
}

func (c *InProcessClient) SendMessage(ctx context.Context, convID string, content string) (<-chan tui.StreamChunk, error) {
    ch := make(chan tui.StreamChunk, 16)
    go func() {
        defer close(ch)
        for chunk := range c.agent.Stream(content) {
            ch <- tui.StreamChunk{Content: chunk.Text, Type: tui.ChunkText}
        }
        ch <- tui.StreamChunk{Done: true}
    }()
    return ch, nil
}
```

### 5. Endpoint Customization

Consumers whose backends use different URL paths can override them via `EndpointConfig`:

```go
app, _ := tui.New(tui.Config{
    AppName:    "My Agent",
    BackendURL: "http://localhost:3000",
    Endpoints: &tui.EndpointConfig{
        ListAgents:         "/api/v1/agents",
        CreateConversation: "/api/v1/sessions",
        SendMessage:        "/api/v1/sessions/{id}/chat",
        GetConversation:    "/api/v1/sessions/{id}",
        Health:             "/api/v1/ping",
    },
})
```

The `{id}` placeholder in `SendMessage` is replaced with the conversation ID at runtime.

## Migration Plan: Stack Bench to agent-tui Consumer

After the package is built, Stack Bench's `app/cli/` transforms from a full application to a thin configuration wrapper.

### Before (current `app/cli/main.go` -- 103 lines)

The current `main.go` contains backend discovery logic, signal handling, service management, and Bubble Tea program creation.

### After (new `app/cli/main.go` -- ~40 lines)

```go
package main

import (
    "fmt"
    "os"

    tui "github.com/dugshub/agent-tui"
)

func main() {
    app, err := tui.New(tui.Config{
        AppName:        "Stack Bench",
        AssistantLabel: "sb:",
        EnvOverride:    "SB_BACKEND_URL",
        BackendService: tui.NewExecService(tui.ExecServiceConfig{
            Name:    "backend",
            Command: "uv",
            Args:    []string{"run", "uvicorn", "organisms.api.app:app", "--host", "127.0.0.1", "--port", "8000"},
            Dir:     findBackendDir(),
            Port:    8000,
        }),
        Commands: []tui.CommandDef{
            // Stack-bench-specific commands go here
        },
    })
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
    if err := app.Run(); err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
}

func findBackendDir() string {
    // ... same heuristic as today ...
}
```

### Migration Steps

1. Create the `agent-tui` repository and move code there (Phase 3 below).
2. Update `app/cli/go.mod` to depend on `github.com/dugshub/agent-tui`.
3. Replace `app/cli/main.go` with the thin wrapper above.
4. Delete all of `app/cli/internal/` (now lives in the package).
5. Run `just test` and `just quality` to verify parity.

## Implementation Phases

| Phase | What | Depends On | Estimated Size |
|-------|------|------------|----------------|
| 1 | Define public API surface (incl. StdioConfig) | -- | ~450 lines |
| 2 | Restructure internals | Phase 1 | ~200 lines changed |
| 3 | Extract to agentic-patterns monorepo | Phase 2 | Repository setup |
| 4 | Build consumer configuration layer | Phase 3 | ~350 lines |
| 4b | Build JSON-RPC stdio transport | Phase 1 | ~480 lines |
| 5 | Migrate Stack Bench CLI | Phase 4 | ~100 lines (net reduction) |
| 6 | Contract test suite + examples (HTTP + stdio) | Phase 4, 4b | ~600 lines |
| 7 | Backend implementor's guide (Python + TS) + release | Phase 6 | Docs + reference code |

### Phase 1: Define Public API Surface

Create the exported types and interfaces in the root package. These are the types that consumers import.

**Files to create (in `agent-tui/`):**

- `tui.go` -- `New(Config) (*App, error)`, `App.Run() error`
- `config.go` -- `Config`, `EndpointConfig`
- `client.go` -- `Client` interface, `NewHTTPClient`, `NewStubClient`
- `types.go` -- `AgentSummary`, `Conversation`, `StreamChunk`, `ChunkType`
- `command.go` -- `CommandDef`, `CommandHandler`, `CommandParseResult`
- `service.go` -- `ServiceNode` interface, `ServiceStatus`, `ExecServiceConfig`, `NewExecService`
- `stdio.go` -- `StdioConfig`, `NewStdioClient`
- `theme.go` -- `Theme`, `Style`, token enums, `DarkTheme()`, `LightTheme()`

The public types are thin wrappers or re-exports of internal types. The goal is a clean, minimal API surface that hides implementation details.

**Key decisions:**

- Public types use `json` tags matching the HTTP contract (e.g., `agent_id` not `agent_name`).
- The `Client` interface uses the canonical event names from the contract (`message.delta`, not `agent.message.chunk`). Legacy name mapping is internal.
- `StreamChunk` is the same type used internally and exposed publicly, so consumers implementing custom `Client` can construct them directly.

### Phase 2: Restructure Internals

Move existing code from `app/cli/internal/` into `agent-tui/internal/`, refactoring import paths and replacing Stack-Bench-specific references with configurable values.

**Package mapping:**

| Current (`app/cli/internal/`) | New (`agent-tui/internal/`) | Changes |
|-------------------------------|---------------------------|---------|
| `api/sse.go` | `sse/parse.go` | Rename package; add canonical event name support |
| `api/client.go` | `httpclient/client.go` | Accept `EndpointConfig`; use `agent_id` not `agent_name` |
| `api/types.go` | Split: root `types.go` (public) + `httpclient/types.go` (wire format) | Separate public types from wire types |
| `chat/` | `chat/` | Replace hardcoded `"sb:"` with configurable label |
| `command/` | `command/` | Same structure, commands initialized from Config |
| `service/` | `service/` | `local.go` becomes generic `ExecService` |
| `app/` | `app/` | Replace hardcoded `"STACK BENCH"` with Config.AppName |
| `ui/` | `ui/` | Fix package-level theme vars (see refactor 8) |

**Specific refactors:**

1. `chat/view.go` line 151: replace `"sb:"` with a label from config passed through the model chain.
2. `app/model.go` line 215: replace `" STACK BENCH"` with config app name.
3. `api/client.go` `ListAgents`: parameterize endpoint paths.
4. `api/client.go` `CreateConversation`: use `agent_id` field name (backend contract canonical name).
5. `api/client.go` `SendMessage`: update path from `/conversations/{id}/send` to `/conversations/{id}/messages` and request body field from `message` to `content`.
6. `service/local.go`: generalize from hardcoded `uv run uvicorn` to configurable command.
7. `main.go` logic: absorbed into `tui.New()` and `App.Run()`.
8. `ui/markdown.go` lines 52-61: move package-level `var` style definitions (which call `theme.Active()` at init time) into a function that resolves against the configured theme at render time. Currently these are frozen at package init, which breaks per-instance theme configuration.
9. `ui/autocomplete/autocomplete.go` lines 155-167: remove local `min`/`max` helper functions that shadow Go 1.21+ built-ins (Go 1.25 is used per `go.mod`).

### Phase 3: Extract Package (within stack-bench, portable to agentic-patterns later)

**Development happens in the stack-bench repo** where the CLI source lives. The package is structured to be relocatable — a clean `go.mod` with no stack-bench-specific imports means it can be moved to agentic-patterns (or a standalone repo) later with only a module path change.

1. Create `packages/agent-tui/` directory in the stack-bench repo.
2. Initialize `go.mod` with `module github.com/dugshub/agent-tui` (the Go module path is independent of the git repo path — changing it later is a one-line edit + find-replace in consumer `go.mod` files).
3. Copy the restructured code from Phase 2.
4. Ensure `go build ./...` and `go test ./...` pass.
5. **Do not tag a release yet** — tagging happens after relocation to the final home (agentic-patterns or standalone).

**Future relocation:** Move `packages/agent-tui/` to its final home, update the `module` line in `go.mod`, update consumer `require` directives, tag `v0.1.0`.

### Phase 4: Build Consumer Configuration Layer

Implement the `New(Config) (*App, error)` constructor that wires everything together:

1. **Resolve backend connection:** Check `EnvOverride` env var, then `BackendURL`, then `BackendService`, then `BackendStdio`. Create the appropriate `Client` (`HTTPClient` for URL/service, `StdioClient` for stdio). Exactly one backend option must be set (or resolved via env override).
2. **Start service if needed:** If `BackendService` is set, create a `ServiceManager` and start it.
3. **Register commands:** Merge built-in commands with `Config.Commands`. Built-in: `/help`, `/clear`, `/quit`. If the consumer registered a command with the same name, theirs wins.
4. **Set up theme:** Use `Config.Theme` or default to `DarkTheme()`.
5. **Create the Bubble Tea program:** Wire the app model with the client, command registry, service manager, and config values (AppName, AssistantLabel).
6. **Signal handling:** `App.Run()` sets up SIGINT/SIGTERM handlers for clean shutdown.

### Phase 4b: Build JSON-RPC stdio Transport

Implement the `StdioClient` — a `Client` implementation that spawns a subprocess and communicates via JSON-RPC 2.0 over stdin/stdout.

**Files to create (in `agent-tui/internal/stdioclient/`):**

- `jsonrpc.go` (~150 lines) -- JSON-RPC 2.0 wire types and framing:
  - `Request` struct: `{"jsonrpc": "2.0", "method": "...", "params": {...}, "id": N}`
  - `Response` struct: `{"jsonrpc": "2.0", "result": {...}, "id": N}` or `{"error": {...}, "id": N}`
  - `Notification` struct: `{"jsonrpc": "2.0", "method": "stream.event", "params": {...}}`
  - `Writer`: writes JSON-RPC objects as newline-delimited JSON to an `io.Writer`
  - `Reader`: reads newline-delimited JSON from a `bufio.Scanner`, dispatches to response or notification handlers
  - Request ID generation (atomic counter)

- `client.go` (~200 lines) -- `StdioClient` implementing `Client`:
  - `NewStdioClient(StdioConfig)`: spawns `exec.Command`, pipes stdin/stdout, starts reader goroutine
  - `ListAgents`: sends `listAgents` request, waits for response
  - `CreateConversation`: sends `createConversation` request, waits for response
  - `SendMessage`: sends `sendMessage` request, returns `<-chan StreamChunk` fed by `stream.event` notifications. Channel is closed on `done` notification or final response.
  - `ListConversations`: sends `listConversations` request. On `-32601` error (Method not found), returns `(nil, nil)`.
  - `GetConversation`: same optional semantics.
  - `Close()`: closes stdin, waits 5s, sends SIGTERM

- `client_test.go` (~130 lines) -- Tests using a mock subprocess (in-process pipe):
  - Happy path: full sendMessage flow with streaming notifications
  - Error handling: JSON-RPC error responses, malformed JSON, process exit
  - Optional method handling: `-32601` returns nil
  - Process lifecycle: graceful shutdown

**Key implementation detail:** The reader goroutine reads stdout line-by-line. For each line, it unmarshals the JSON to determine if it's a response (has `id`) or notification (no `id`). Responses are dispatched to a waiting channel keyed by request ID. Notifications are dispatched to the active stream channel (if any).

This phase can run **in parallel** with Phases 2-4 since it only depends on the Phase 1 types.

### Phase 5: Migrate Stack Bench CLI

1. Add `require github.com/dugshub/agent-tui v0.1.0` to `app/cli/go.mod`.
2. Replace `app/cli/main.go` with the thin wrapper.
3. Delete `app/cli/internal/` entirely.
4. Update `app/cli/Justfile` (build/test commands stay the same).
5. Run the full Stack Bench quality gate to verify behavioral parity.

### Phase 6: Contract Test Suite + Examples

1. Build `contracttest/validate.go` with test helpers that any backend can use (both HTTP and stdio transports).
2. Create `_examples/minimal/` -- remote HTTP/SSE backend connection (~30 lines).
3. Create `_examples/local-python/` -- auto-start Python backend with a tiny Flask SSE server.
4. Create `_examples/stdio-python/` -- spawn a Python script via JSON-RPC stdio (~20 lines Go + the `agent.py` from the spec).
5. Create `_examples/stdio-typescript/` -- spawn a TS script via JSON-RPC stdio (~20 lines Go + the `agent.ts` from the spec).
6. Create `_examples/custom-theme/` -- Nord theme customization.
7. Create `_examples/custom-commands/` -- custom slash commands.

### Phase 7: Backend Implementor's Guide + Release

1. Write `README.md` with quick-start, configuration reference.
2. Write `docs/backend-guide.md` -- **Backend Implementor's Guide** covering:
   - HTTP/SSE contract reference with curl examples for every endpoint
   - JSON-RPC stdio contract reference with example stdin/stdout transcripts
   - Python reference implementation (HTTP/SSE via FastAPI + stdio via raw script)
   - TypeScript reference implementation (HTTP/SSE via Express + stdio via raw script)
   - Common patterns: single-agent backends, multi-agent, tool calling, error handling
   - Troubleshooting: debugging SSE streams with curl, debugging stdio with pipe
3. Write `CONTRIBUTING.md`.
4. Tag `agent-tui/v0.1.0` (first public release with both transports, docs, and examples).

## Key Design Decisions

### 1. Root-package exports with internal implementation

The public API lives in the root `github.com/dugshub/agent-tui` package. Consumers never import subpackages. Internally, the code is organized into `internal/` subpackages for clean separation. This gives consumers a flat import (`import tui "github.com/dugshub/agent-tui"`) while keeping the implementation well-structured.

**Alternative considered:** Separate `tui/client`, `tui/theme`, `tui/command` packages. Rejected because it forces consumers to import 4-5 packages for basic usage. A single import with clear type names is better DX.

### 2. SSE event names use short canonical forms

The contract uses `message.delta`, `thinking`, `tool.start`, etc. rather than the longer `agent.message.chunk` form currently used by the Stack Bench backend. The shorter names are clearer for third-party backend implementors. Legacy names are supported via internal aliases in the SSE parser.

**Migration:** The Stack Bench backend will be updated to emit the canonical names. The TUI accepts both forms indefinitely for backward compatibility.

### 3. ExecService as a built-in convenience

Most consumers who want local backend management will use `exec.Command` to start a process. Rather than forcing them to implement `ServiceNode`, the package provides `NewExecService(ExecServiceConfig)` which covers the common case. The `ServiceNode` interface remains available for advanced use cases (Docker, cloud, etc.).

### 4. No `--no-backend` flag in the package

The current CLI has a `--no-backend` flag. This is application-level behavior, not package-level. Consumers who want this behavior simply set `BackendURL` to their stub endpoint or use `NewStubClient()`. The package does not parse command-line flags.

### 5. Commands are data, not closures registered at init

The current `DefaultRegistry()` creates commands with closures. The package instead accepts `[]CommandDef` in config, and the built-in commands are registered internally during `New()`. This avoids init-time side effects and makes the command set fully declarable.

### 6. Agent picker is built-in, not optional

The agent picker phase (list agents, select one, create conversation) is part of the package's standard flow. If a backend has only one agent, it returns a single-element list, and the picker auto-selects it without user interaction. This avoids a configuration knob (`SkipAgentPicker`) that would add complexity.

**Implementation:** When `ListAgents` returns exactly one agent, the picker phase is skipped and a conversation is created immediately.

### 7. JSON-RPC over stdio as the second transport (not raw stdio)

The stdio transport uses JSON-RPC 2.0 rather than ad-hoc line-delimited JSON. Raw stdio would require inventing message framing, error formats, and request correlation — effectively a worse JSON-RPC. JSON-RPC is a tiny spec with libraries in every language, aligns with MCP (Model Context Protocol), and gives us structured errors, request IDs, and a clean notification mechanism for streaming.

**Key design:** Streaming uses JSON-RPC **notifications** (`stream.event`) with the same event type names and data schemas as the SSE transport. Backend developers learn one set of events regardless of transport.

### 8. Theme system is exported as-is

The four-dimensional token system (Category, Hierarchy, Emphasis, Status) from the CLI component spec is preserved and exported. It is the right abstraction -- consumers who want to customize colors do so through semantic tokens, not by overriding individual lipgloss styles. The built-in DarkTheme and LightTheme cover 90% of use cases.

## Testing Strategy

### Unit Tests (internal packages)

Every internal package has `_test.go` files, carried over from the current CLI:

- `internal/stdioclient/client_test.go` -- JSON-RPC framing, stdio streaming, process lifecycle, error handling, optional method fallback
- `internal/sse/parse_test.go` -- SSE parsing, chunk conversion, legacy event names, malformed data
- `internal/chat/model_test.go` -- Message accumulation, tool call lifecycle, error handling, stream finalization
- `internal/command/parse_test.go` -- Command parsing, tokenization, quoted strings
- `internal/command/registry_test.go` -- Registration, lookup, suggest, fuzzy matching
- `internal/ui/markdown_test.go` -- Headers, code blocks, inline formatting, streaming chunks
- `internal/ui/components/atoms/*_test.go` -- Each atom tested with both themes, width constraints
- `internal/ui/components/molecules/*_test.go` -- Each molecule tested for composition correctness

### Integration Tests (root package)

- `tui_test.go` -- `New()` with various Config combinations: URL-only, service, stdio, env override, custom commands, custom theme
- `config_test.go` -- Validation: missing AppName errors, multiple backend options set errors, stdio + BackendURL conflict, etc.

### Contract Tests (exported)

- `contracttest/validate_test.go` -- Tests that validate the test helpers themselves against a mock server

### Example Tests

Each example directory has a `main_test.go` that verifies the example compiles and the Config is valid (does not start a backend).

### CI

- `go test ./...` runs all unit, integration, and example tests
- `go vet ./...` for static analysis
- `golangci-lint run` for comprehensive linting
- No backend needed for CI -- all tests use StubClient or mock HTTP servers

## Open Questions

1. **Module path:** Should this be `github.com/dugshub/agent-tui` or `github.com/dugshub/agenttui` (no hyphen)? Go module paths allow hyphens, but the imported package name would be `agent-tui` which is not a valid Go identifier. Consumers would need an alias: `import tui "github.com/dugshub/agent-tui"`. The hyphenated name is clearer for discoverability. **Recommendation:** Use `github.com/dugshub/agent-tui` with the convention that consumers alias it as `tui`.

2. **Backend contract versioning:** Should the contract include a version header (`X-Agent-TUI-Version: 1`)? This would allow the TUI to detect incompatible backends. **Recommendation:** Not for v0.x. Add it in v1.0 if needed.

3. **Conversation branching:** The current CLI supports `BranchConversation`. This is a Stack-Bench-specific feature (conversation trees). Should the package support it? **Recommendation:** No. The `Client` interface includes the four core methods. Branching is an application-level concern that Stack Bench can implement by wrapping the Client or extending it in its own code.

4. **Single-agent auto-select:** When the backend returns exactly one agent, should the picker be skipped entirely (auto-create conversation) or should the picker still show with auto-selection? **Recommendation:** Skip entirely. One agent means no choice to make. Show a brief "Starting conversation with {name}..." message instead.
