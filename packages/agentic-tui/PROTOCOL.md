# agentic-tui Backend Protocol

This document defines the contract that any backend must implement to work with `agentic-tui`. Two transports are supported: **HTTP/SSE** (server-sent events over HTTP) and **JSON-RPC 2.0 over stdio** (subprocess communication).

Pick whichever transport fits your architecture. The TUI handles both transparently.

---

## Table of Contents

1. [HTTP Transport](#http-transport)
2. [SSE Event Vocabulary](#sse-event-vocabulary)
3. [Display Types](#display-types)
4. [JSON-RPC Stdio Transport](#json-rpc-stdio-transport)
5. [Streaming Lifecycle](#streaming-lifecycle)
6. [Backward Compatibility](#backward-compatibility)
7. [Implementing a Backend in 30 Minutes](#implementing-a-backend-in-30-minutes)

---

## HTTP Transport

The HTTP transport communicates with a running server. All endpoints accept and return JSON unless noted. Paths are configurable via `EndpointConfig`; defaults are shown below.

### Endpoints

| Method | Default Path | Request Body | Response | Required |
|--------|-------------|-------------|----------|----------|
| GET | `/health` | -- | `{"status": "ok"}` | No |
| GET | `/agents` | -- | `AgentSummary[]` | Yes |
| POST | `/conversations` | `CreateConversationRequest` | `ConversationResponse` | Yes |
| POST | `/conversations/{id}/messages` | `SendMessageRequest` | SSE stream | Yes |
| GET | `/conversations` | query: `?agent_name=...` | `Conversation[]` | No |
| GET | `/conversations/{id}` | -- | `ConversationDetailResponse` | No |

### Request/Response Schemas

**AgentSummary**
```json
{
  "id": "string",
  "name": "string",
  "role": "string"
}
```

**CreateConversationRequest**
```json
{
  "agent_id": "string"
}
```

**ConversationResponse**
```json
{
  "id": "string",
  "agent_id": "string"
}
```

**SendMessageRequest**
```json
{
  "content": "string"
}
```

The `POST /conversations/{id}/messages` endpoint MUST:
- Return `Content-Type: text/event-stream`
- Stream SSE events as defined below
- Keep the connection open until the stream completes

---

## SSE Event Vocabulary

Each SSE frame has an `event:` line and a `data:` line containing JSON. The canonical event names are listed first; legacy aliases are accepted by the TUI but new backends should use the canonical names.

### message.delta

Streaming text fragment. Sent zero or more times during a response.

```
event: message.delta
data: {"delta": "Hello "}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `delta` | string | Yes | Text fragment to append |

**Legacy aliases:** `agent.message.chunk`

### message.complete

Marks the end of a message. Sent once after all deltas.

```
event: message.complete
data: {"content": "Hello world!", "input_tokens": 150, "output_tokens": 42}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Full assembled message |
| `input_tokens` | int | No | Prompt tokens consumed |
| `output_tokens` | int | No | Completion tokens generated |

**Legacy aliases:** `agent.message.complete`

### thinking

Reasoning/chain-of-thought content. Displayed in a collapsible section.

```
event: thinking
data: {"content": "Let me analyze this step by step..."}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Reasoning text |

**Legacy aliases:** `agent.reasoning`

### tool.start

Signals a tool invocation has begun.

```
event: tool.start
data: {
  "tool_call_id": "call_abc123",
  "tool_name": "read_file",
  "display_type": "code",
  "arguments": {"path": "/src/main.go"}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_call_id` | string | Yes | Unique ID for this invocation |
| `tool_name` | string | Yes | Name of the tool |
| `display_type` | string | No | How to render the result (see [Display Types](#display-types)) |
| `arguments` | object | No | Tool input parameters |

**Legacy aliases:** `agent.tool.start`, `tool_start`

### tool.end

Signals a tool invocation has completed.

```
event: tool.end
data: {
  "tool_call_id": "call_abc123",
  "result": "file contents here...",
  "error": null,
  "duration_ms": 45,
  "display_type": "code"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_call_id` | string | Yes | Matches the `tool.start` ID |
| `result` | string | No | Tool output |
| `error` | string | No | Error message if the tool failed |
| `duration_ms` | int | No | Execution time in milliseconds |
| `display_type` | string | No | How to render the result |

**Legacy aliases:** `agent.tool.end`, `tool_end`

### tool.rejected

A tool call was rejected by a safety gate or policy.

```
event: tool.rejected
data: {"tool_name": "execute_command", "reason": "Command not in allowlist"}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_name` | string | Yes | Name of the rejected tool |
| `reason` | string | Yes | Why it was rejected |

**Legacy aliases:** `agent.tool.rejected`

### error

A fatal error that terminates the stream.

```
event: error
data: {"error_type": "rate_limit", "message": "Too many requests"}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error_type` | string | Yes | Error category |
| `message` | string | Yes | Human-readable description |

**Legacy aliases:** `agent.error`

### done

Signals the stream is complete. Backends SHOULD send this as the final event.

```
event: done
data: {}
```

No fields required. The TUI also handles connection close as an implicit done.

---

## Display Types

The `display_type` field on `tool.start` and `tool.end` controls how the TUI renders tool results:

| Value | Rendering |
|-------|-----------|
| `generic` | Default plain-text display |
| `diff` | Unified diff with syntax highlighting |
| `code` | Syntax-highlighted code block |
| `bash` | Terminal/shell output formatting |

If omitted, `generic` is used.

---

## JSON-RPC Stdio Transport

The stdio transport spawns a backend as a subprocess and communicates via JSON-RPC 2.0 over stdin/stdout. Each message is a single JSON object terminated by a newline (`\n`).

### Methods

#### listAgents (required)

List available agents.

**Request:**
```json
{"jsonrpc": "2.0", "method": "listAgents", "id": 1}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": [
    {"id": "default", "name": "Assistant", "role": "Helpful assistant"}
  ],
  "id": 1
}
```

#### createConversation (required)

Create a new conversation.

**Request:**
```json
{"jsonrpc": "2.0", "method": "createConversation", "params": {"agent_id": "default"}, "id": 2}
```

**Response:**
```json
{"jsonrpc": "2.0", "result": {"id": "conv-1", "agent_id": "default"}, "id": 2}
```

#### sendMessage (required)

Send a user message. The backend streams events as JSON-RPC **notifications** (no `id` field) using the `stream.event` method, then sends a final **response** with the matching `id`.

**Request:**
```json
{"jsonrpc": "2.0", "method": "sendMessage", "params": {"conversation_id": "conv-1", "content": "Hello"}, "id": 3}
```

**Notifications (streamed):**
```json
{"jsonrpc": "2.0", "method": "stream.event", "params": {"type": "message.delta", "data": {"delta": "Hi "}}}
{"jsonrpc": "2.0", "method": "stream.event", "params": {"type": "message.delta", "data": {"delta": "there!"}}}
{"jsonrpc": "2.0", "method": "stream.event", "params": {"type": "done", "data": {}}}
```

**Final response:**
```json
{"jsonrpc": "2.0", "result": {"status": "complete"}, "id": 3}
```

The `params.type` field in `stream.event` notifications uses the same event vocabulary as SSE (see above). The `params.data` field contains the same JSON payload.

#### listConversations (optional)

**Request:**
```json
{"jsonrpc": "2.0", "method": "listConversations", "params": {"agent_name": "default"}, "id": 4}
```

**Response:**
```json
{"jsonrpc": "2.0", "result": [{"id": "conv-1", "agent_id": "default", "state": "active"}], "id": 4}
```

#### getConversation (optional)

**Request:**
```json
{"jsonrpc": "2.0", "method": "getConversation", "params": {"id": "conv-1"}, "id": 5}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": "conv-1",
    "messages": [
      {"id": "msg-1", "kind": "human", "sequence": 1, "parts": [{"type": "text", "content": "Hello"}]},
      {"id": "msg-2", "kind": "ai", "sequence": 2, "parts": [{"type": "text", "content": "Hi there!"}]}
    ]
  },
  "id": 5
}
```

### Error Handling

Errors follow JSON-RPC 2.0 conventions:

```json
{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found: foo"}, "id": 6}
```

Standard error codes:
- `-32700` — Parse error
- `-32600` — Invalid request
- `-32601` — Method not found
- `-32602` — Invalid params
- `-32603` — Internal error

---

## Streaming Lifecycle

Both transports follow the same logical sequence:

```
Client                          Backend
  |                                |
  |-- send message --------------->|
  |                                |
  |<-- message.delta (0..n) ------|
  |<-- thinking (0..n) ------------|
  |<-- tool.start (0..n) ---------|
  |<-- tool.end (0..n) -----------|
  |<-- message.complete (0..1) ---|
  |<-- done ----------------------|
  |                                |
```

Rules:
1. `message.delta` events arrive in order; concatenating all deltas produces the full message.
2. `thinking` events may arrive before, between, or after deltas.
3. `tool.start` and `tool.end` events are paired by `tool_call_id`. Multiple tools may run concurrently.
4. `message.complete` is sent after all deltas. It contains the full assembled text and token counts.
5. `done` marks the end of the stream. For HTTP/SSE, the connection closes after this. For stdio, the response message with the matching `id` follows.
6. `error` terminates the stream immediately. No `done` is sent after an error.

---

## Backward Compatibility

The TUI accepts both canonical and legacy event names. New backends SHOULD use canonical names only.

| Canonical | Legacy Aliases |
|-----------|---------------|
| `message.delta` | `agent.message.chunk` |
| `message.complete` | `agent.message.complete` |
| `thinking` | `agent.reasoning` |
| `tool.start` | `agent.tool.start`, `tool_start` |
| `tool.end` | `agent.tool.end`, `tool_end` |
| `tool.rejected` | `agent.tool.rejected` |
| `error` | `agent.error` |

Optional fields may be omitted. The TUI uses sensible defaults:
- Missing `display_type` defaults to `generic`
- Missing `input_tokens`/`output_tokens` default to `0`
- Missing `duration_ms` defaults to `0`

---

## Implementing a Backend in 30 Minutes

The fastest path is the **stdio transport** -- you only need to read JSON from stdin and write JSON to stdout.

### Step 1: Scaffold

Pick your language. Here is a minimal Python backend (zero dependencies):

```python
#!/usr/bin/env python3
import sys, json

def handle(method, params, req_id):
    if method == "listAgents":
        return {"result": [{"id": "default", "name": "My Agent", "role": "Assistant"}], "id": req_id}
    elif method == "createConversation":
        return {"result": {"id": "conv-1"}, "id": req_id}
    elif method == "sendMessage":
        # Stream a response
        notify({"type": "message.delta", "data": {"delta": "Hello from my agent!"}})
        notify({"type": "done", "data": {}})
        return {"result": {"status": "complete"}, "id": req_id}
    else:
        return {"error": {"code": -32601, "message": f"Unknown: {method}"}, "id": req_id}

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

### Step 2: Wire it up

```go
package main

import (
    "fmt"
    "os"
    tui "github.com/dugshub/agentic-tui"
)

func main() {
    app, _ := tui.New(tui.Config{
        AppName: "My Agent",
        BackendStdio: &tui.StdioConfig{
            Command: "python3",
            Args:    []string{"agent.py"},
        },
    })
    if err := app.Run(); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}
```

### Step 3: Run it

```bash
go run main.go
```

You now have a working agent TUI. From here:

- **Add tools**: Send `tool.start` / `tool.end` events to show tool usage in the UI.
- **Add thinking**: Send `thinking` events to show chain-of-thought reasoning.
- **Switch to HTTP**: If you prefer a long-running server, implement the HTTP endpoints and use `BackendURL` instead of `BackendStdio`.
- **Validate**: Use `contracttest.ValidateStdioBackend(t, "python3", "agent.py")` to run the contract test suite against your backend.

### Step 4: Validate with contract tests

```go
package mybackend_test

import (
    "testing"
    "github.com/dugshub/agentic-tui/contracttest"
)

func TestMyBackend(t *testing.T) {
    // For stdio backends:
    contracttest.ValidateStdioBackend(t, "python3", "agent.py")

    // For HTTP backends:
    // contracttest.ValidateBackend(t, "http://localhost:8000")
}
```

The contract tests verify:
- `listAgents` returns at least one agent with a non-empty ID
- `createConversation` returns a conversation ID
- `sendMessage` streams `message.delta` events and a `done` signal
- (HTTP only) Health check, correct content types, SSE format
