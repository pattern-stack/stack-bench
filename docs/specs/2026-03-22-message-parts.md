---
title: Message Parts — Part-Aware Chat Model
date: 2026-03-22
status: draft
branch:
depends_on: []
adrs: []
issues: [SB-008, SB-009, SB-010, SB-013]
---

# Message Parts — Part-Aware Chat Model

## Goal

Replace the flat `chat.Message{Role, Content}` with a part-aware model that accumulates structured parts (text, thinking, tool calls, errors) from SSE events, and renders each part with the appropriate component. The backend enriches tool events with a `display_type` hint so both the Go CLI and React frontend render tool results consistently without duplicating tool-name-to-display mapping.

## Context

### What exists

**Backend** (`conversation_runner.py`):
- Streams agentic-patterns events via `SSEFormatter.format_stream_event(event)`
- Events include: `agent.message.chunk`, `agent.message.complete`, `agent.reasoning`, `agent.tool.start`, `agent.tool.end`, `agent.tool.rejected`, `agent.error`, `agent.iteration.start/end`
- Tool events carry `tool_name`, `arguments`, `result` — but no display hint

**CLI SSE parser** (`api/sse.go`):
- `ChunkFromSSE()` handles all event types, converts to `StreamChunk{Content, Type, Done, Error}`
- `ChunkType`: `ChunkText`, `ChunkThinking`, `ChunkToolStart`, `ChunkToolEnd`
- Loses structured data — tool name goes into `Content`, arguments/result are dropped

**CLI chat model** (`chat/model.go`):
- `Message{Role, Content, Raw}` — flat, no parts
- `handleResponse()` only checks `Content` and `Done`, ignores `Type`
- All assistant content concatenated into one string, rendered via `RenderMarkdown()`

**CLI components** (all exist, tested):
- `ToolCallBlock` — name badge + state icon + args + result
- `DiffBlock` — file path + colored diff with line numbers
- `StatusBlock` — spinner + verb + elapsed/count badges
- `ErrorBlock` — error message with icon
- `CodeBlock` — syntax-highlighted code with file path header
- `RenderMarkdown()` — goldmark + chroma rendering

### What's missing

1. Backend doesn't tell clients how to render tool results
2. `StreamChunk` loses structured tool data (name, args, result are not separate fields)
3. Chat model has no concept of parts — can't accumulate a tool call across start/end events
4. Rendering is monolithic — everything goes through markdown

## Domain Model

```
Message
  Role: user | assistant | system
  Parts: []MessagePart (ordered)

MessagePart
  Type: text | thinking | tool_call | error
  Content: string (accumulated text)
  ToolCall: *ToolCallPart (nil unless Type == tool_call)
  Complete: bool

ToolCallPart
  ID: string (tool_call_id from SSE)
  Name: string (tool_name)
  DisplayType: string (from backend: "generic", "diff", "code", "bash")
  Arguments: map[string]any
  State: pending | running | complete | error
  Result: string
  Error: string
  DurationMs: int
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Backend: enrich tool SSE events with `display_type` | -- |
| 2 | CLI: enrich `StreamChunk` with structured tool data | -- |
| 3 | CLI: part-aware message model + accumulation | Phase 2 |
| 4 | CLI: render each part with the right component | Phase 3 |

Phases 1 and 2 are independent. Phases 3-4 can be one branch.

## Phase Details

### Phase 1: Backend display_type enrichment

**Files:** `app/backend/src/molecules/runtime/conversation_runner.py`

Add a `display_type` field to `agent.tool.start` and `agent.tool.end` SSE events before yielding. The mapping is a simple dict in the ConversationRunner:

```python
TOOL_DISPLAY_TYPES = {
    # File operations → diff view
    "edit_file": "diff",
    "write_file": "diff",
    "apply_patch": "diff",
    # Read/code operations → code view
    "read_file": "code",
    "grep": "code",
    "glob": "code",
    # Shell operations → bash view
    "bash": "bash",
    "execute_command": "bash",
}
# Default: "generic"
```

Instead of `yield formatter.format_stream_event(event)` for tool events, manually build the data dict and inject `display_type`:

```python
if isinstance(event, (ToolCallStartEvent, ToolCallEndEvent)):
    data = asdict(event)
    data["display_type"] = TOOL_DISPLAY_TYPES.get(event.tool_name, "generic")
    yield formatter.format(event.event_type, data)
else:
    yield formatter.format_stream_event(event)
```

This is ~10 lines of code. The mapping can be extended later (pull from `tool_ux` metadata, make it configurable per agent, etc.) but the SSE contract is stable.

### Phase 2: CLI StreamChunk enrichment

**Files:** `app/cli/internal/api/client.go`, `app/cli/internal/api/sse.go`

Expand `StreamChunk` to carry structured tool data:

```go
type StreamChunk struct {
    Content     string
    Type        ChunkType
    Done        bool
    Error       error
    // Tool fields (populated for ChunkToolStart / ChunkToolEnd)
    ToolCallID  string
    ToolName    string
    DisplayType string            // "generic", "diff", "code", "bash"
    Arguments   map[string]any
    Result      string
    ToolError   string
    DurationMs  int
}
```

Update `ChunkFromSSE()` to parse the full JSON payload for tool events instead of just extracting one field into `Content`.

Add new chunk types for events we currently ignore:

```go
const (
    ChunkText        ChunkType = "text"
    ChunkThinking    ChunkType = "thinking"
    ChunkToolStart   ChunkType = "tool_start"
    ChunkToolEnd     ChunkType = "tool_end"
    ChunkToolReject  ChunkType = "tool_rejected"
    ChunkError       ChunkType = "error"
    ChunkIteration   ChunkType = "iteration"    // new
    ChunkMsgStart    ChunkType = "msg_start"    // new
)
```

### Phase 3: Part-aware message model

**Files:** `app/cli/internal/chat/model.go` (new types + accumulation logic)

Replace `Message{Role, Content, Raw}` with:

```go
type PartType string
const (
    PartText     PartType = "text"
    PartThinking PartType = "thinking"
    PartToolCall PartType = "tool_call"
    PartError    PartType = "error"
)

type ToolCallPart struct {
    ID          string
    Name        string
    DisplayType string
    Arguments   map[string]any
    State       ToolCallState  // reuse molecules.ToolCallState
    Result      string
    Error       string
    DurationMs  int
}

type MessagePart struct {
    Type     PartType
    Content  string
    ToolCall *ToolCallPart
    Complete bool
}

type Message struct {
    Role  Role
    Parts []MessagePart
    Raw   bool  // keep for gallery mode backward compat
}
```

Update `handleResponse()` to dispatch by `StreamChunk.Type`:

- `ChunkMsgStart` — append new assistant Message with empty Parts
- `ChunkText` — append to last text part (or create one)
- `ChunkThinking` — append to last thinking part (or create one)
- `ChunkToolStart` — append new tool_call part with State=Running
- `ChunkToolEnd` — find matching part by ToolCallID, set State=Complete, fill Result
- `ChunkToolReject` — append error part with rejection reason
- `ChunkError` — append error part
- `Done` — mark all parts Complete

### Phase 4: Part-aware rendering

**Files:** `app/cli/internal/chat/view.go`

Replace the monolithic `renderMessage()` with per-part dispatch:

```go
func renderMessage(msg Message, width int) string {
    if msg.Raw {
        return msg.Content  // gallery mode
    }
    ctx := atoms.DefaultContext(width)
    var sections []string
    // Role badge (once, at top)
    sections = append(sections, renderRoleBadge(ctx, msg.Role))
    // Each part
    for _, part := range msg.Parts {
        sections = append(sections, renderPart(ctx, msg.Role, part))
    }
    return strings.Join(sections, "\n")
}

func renderPart(ctx atoms.RenderContext, role Role, part MessagePart) string {
    switch part.Type {
    case PartText:
        return renderTextPart(ctx, part)        // RenderMarkdown
    case PartThinking:
        return renderThinkingPart(ctx, part)    // collapsed/dim block
    case PartToolCall:
        return renderToolCallPart(ctx, part)    // dispatch by DisplayType
    case PartError:
        return renderErrorPart(ctx, part)       // ErrorBlock
    }
}

func renderToolCallPart(ctx atoms.RenderContext, part MessagePart) string {
    tc := part.ToolCall
    switch tc.DisplayType {
    case "diff":
        return molecules.DiffBlock(ctx, molecules.DiffBlockData{...})
    case "code":
        return atoms.CodeBlock(ctx, atoms.CodeBlockData{...})
    case "bash":
        return atoms.CodeBlock(ctx, atoms.CodeBlockData{Language: "bash", ...})
    default:
        return molecules.ToolCallBlock(ctx, molecules.ToolCallBlockData{...})
    }
}
```

Thinking parts render as a dim, single-line summary (e.g., "Thinking..." or first line of reasoning) — not the full content. This matches Claude Code's UX.

## Raw Message Backward Compatibility

Gallery mode and pre-rendered content use `Message{Raw: true, Content: "..."}`. When `Raw` is true, `Parts` is ignored and `Content` is rendered as-is. The `Content` field on `Message` becomes a convenience accessor:

```go
func (m Message) Content() string {
    if m.Raw { return m.RawContent }
    var buf strings.Builder
    for _, p := range m.Parts {
        buf.WriteString(p.Content)
    }
    return buf.String()
}
```

## Acceptance Criteria

- [ ] Backend `agent.tool.start` and `agent.tool.end` SSE events include `display_type` field
- [ ] CLI `StreamChunk` carries `ToolCallID`, `ToolName`, `DisplayType`, `Arguments`, `Result`
- [ ] Chat model accumulates parts: text chunks build a text part, tool start/end build a tool_call part
- [ ] `renderMessage` dispatches per part type to the correct component
- [ ] Tool calls with `display_type: "diff"` render as `DiffBlock`
- [ ] Tool calls with `display_type: "bash"` render as `CodeBlock` with shell language
- [ ] Tool calls with `display_type: "code"` render as `CodeBlock` with file path
- [ ] Tool calls with `display_type: "generic"` render as `ToolCallBlock`
- [ ] Thinking parts render as dim collapsed text
- [ ] Error parts render as `ErrorBlock`
- [ ] Gallery mode (`Raw: true`) still works unchanged
- [ ] Demo mode still works (DemoClient emits only ChunkText)

## Open Questions

1. **Thinking UX** — Should thinking be always collapsed (one-line), expandable, or full? Start collapsed, iterate.
2. **Tool argument display** — For `generic` display type, show raw JSON args or try to summarize? Start with tool name + one-line summary.
3. **Iteration events** — Surface as status lines between parts, or skip for MVP? Skip for MVP.
4. **Streaming markdown** — SB-013 describes incremental block-level rendering. This spec assumes full re-render per chunk (current behavior). Streaming optimization is additive later.
5. **Frontend alignment** — React frontend will consume the same SSE `display_type` field. Frontend spec is separate but the backend contract is shared.
