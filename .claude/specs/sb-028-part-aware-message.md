# SB-028: Part-aware message model and rendering dispatch

**Issue:** GH #88
**Depends on:** SB-027 (molecule components: ToolCallBlock, DiffBlock, ErrorBlock)
**Depends on:** SB-026 (backend `display_type` enrichment on tool SSE events)

## Problem

The chat model uses a flat `Message{Role, Content}` struct. `handleResponse()` concatenates all stream content into a single string regardless of chunk type. `renderMessage()` feeds that string through `RenderMarkdown()` as one blob. This means:

- Thinking tokens are mixed into the visible response text
- Tool calls (start/end, results, errors) are invisible or dumped as plain text
- There is no way to render tool results using specialized components (DiffBlock, CodeBlock)
- No structured data survives for gallery mode or conversation replay

## Design

### 1. Type definitions

All types live in `app/cli/internal/chat/model.go`.

#### PartType enum

```go
type PartType int

const (
    PartText     PartType = iota // Markdown text from the assistant
    PartThinking                  // Extended thinking / reasoning
    PartToolCall                  // A tool invocation (start -> result/error)
    PartError                     // Stream-level or API error
)
```

#### ToolCallState

```go
type ToolCallState int

const (
    ToolCallRunning  ToolCallState = iota
    ToolCallComplete
    ToolCallFailed
)
```

#### DisplayType

```go
type DisplayType string

const (
    DisplayDiff    DisplayType = "diff"
    DisplayCode    DisplayType = "code"
    DisplayBash    DisplayType = "bash"
    DisplayGeneric DisplayType = "generic"
)
```

#### MessagePart (interface + concrete types)

Use a sealed interface pattern with a private marker method:

```go
type MessagePart interface {
    partType() PartType
}

type TextPart struct {
    Content string
}
func (TextPart) partType() PartType { return PartText }

type ThinkingPart struct {
    Content string
}
func (ThinkingPart) partType() PartType { return PartThinking }

type ToolCallPart struct {
    ID          string        // tool_call_id from SSE
    Name        string        // tool_name
    DisplayType DisplayType   // from SSE display_type field
    State       ToolCallState
    Input       string        // raw input/arguments string (for display)
    Result      string        // tool output on completion
    Error       string        // error message on failure
}
func (ToolCallPart) partType() PartType { return PartToolCall }

type ErrorPart struct {
    Message string
}
func (ErrorPart) partType() PartType { return PartError }
```

#### Updated Message struct

```go
type Message struct {
    Role  Role
    Parts []MessagePart
    Raw   string // Full concatenated text for gallery mode / backward compat
}
```

The `Content` field is removed. A helper provides backward compat:

```go
func (m Message) Content() string {
    if m.Raw != "" {
        return m.Raw
    }
    var sb strings.Builder
    for _, p := range m.Parts {
        switch v := p.(type) {
        case TextPart:
            sb.WriteString(v.Content)
        case ErrorPart:
            sb.WriteString("Error: " + v.Message)
        }
    }
    return sb.String()
}
```

### 2. StreamChunk enrichment (API layer)

`StreamChunk` in `app/cli/internal/api/client.go` needs additional fields to carry the richer data from SSE tool events:

```go
type StreamChunk struct {
    Content     string
    Type        ChunkType
    Done        bool
    Error       error
    // New fields for tool events (populated when Type is ChunkToolStart or ChunkToolEnd):
    ToolCallID  string      // tool_call_id from SSE payload
    ToolName    string      // tool_name from SSE payload
    DisplayType string      // display_type from SSE payload (requires SB-026)
    ToolInput   string      // arguments stringified (tool_start only)
    ToolError   string      // error field (tool_end only, if failed)
}
```

`ChunkFromSSE()` in `sse.go` must be updated to parse these new fields from the SSE JSON payloads. The `SSEToolStartData` and `SSEToolEndData` structs also get the new fields:

```go
type SSEToolStartData struct {
    ToolCallID  string `json:"tool_call_id"`
    ToolName    string `json:"tool_name"`
    Input       string `json:"input"`
    DisplayType string `json:"display_type"`
}

type SSEToolEndData struct {
    ToolCallID  string `json:"tool_call_id"`
    ToolName    string `json:"tool_name"`
    Output      string `json:"output"`
    Error       string `json:"error"`
    DisplayType string `json:"display_type"`
    DurationMs  int    `json:"duration_ms"`
}
```

And `ChunkFromSSE` populates the new StreamChunk fields:

```go
case "agent.tool.start", "tool_start":
    var d SSEToolStartData
    if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
        return nil
    }
    return &StreamChunk{
        Content:     d.ToolName,       // backward compat
        Type:        ChunkToolStart,
        ToolCallID:  d.ToolCallID,
        ToolName:    d.ToolName,
        DisplayType: d.DisplayType,
        ToolInput:   d.Input,
    }

case "agent.tool.end", "tool_end":
    var d SSEToolEndData
    if err := json.Unmarshal([]byte(evt.Data), &d); err != nil {
        return nil
    }
    return &StreamChunk{
        Content:     d.Output,         // backward compat
        Type:        ChunkToolEnd,
        ToolCallID:  d.ToolCallID,
        ToolName:    d.ToolName,
        DisplayType: d.DisplayType,
        ToolError:   d.Error,
    }
```

### 3. handleResponse dispatch

Replace the current `handleResponse` which blindly concatenates `chunk.Content`. The new version dispatches by `chunk.Type`:

```go
func (m *Model) handleResponse(msg ResponseMsg) (Model, tea.Cmd) {
    chunk := msg.Chunk

    if chunk.Error != nil {
        m.streaming = false
        m.streamCh = nil
        m.appendPart(RoleAssistant, ErrorPart{Message: chunk.Error.Error()})
        return *m, nil
    }

    switch chunk.Type {
    case ChunkText:
        m.accumulateText(chunk.Content)

    case ChunkThinking:
        m.accumulateThinking(chunk.Content)

    case ChunkToolStart:
        m.startToolCall(chunk)

    case ChunkToolEnd:
        m.endToolCall(chunk)
    }

    if chunk.Done {
        m.streaming = false
        m.streamCh = nil
        m.finalizeRaw()
        return *m, nil
    }

    return *m, readStream(m.streamCh)
}
```

#### Accumulation helpers

```go
// accumulateText appends text to the last TextPart of the current assistant message,
// or creates a new TextPart if the last part is not text.
func (m *Model) accumulateText(content string) {
    msg := m.ensureAssistantMessage()
    if len(msg.Parts) > 0 {
        if tp, ok := msg.Parts[len(msg.Parts)-1].(TextPart); ok {
            msg.Parts[len(msg.Parts)-1] = TextPart{Content: tp.Content + content}
            return
        }
    }
    msg.Parts = append(msg.Parts, TextPart{Content: content})
}

// accumulateThinking appends to the last ThinkingPart or creates one.
func (m *Model) accumulateThinking(content string) {
    msg := m.ensureAssistantMessage()
    if len(msg.Parts) > 0 {
        if tp, ok := msg.Parts[len(msg.Parts)-1].(ThinkingPart); ok {
            msg.Parts[len(msg.Parts)-1] = ThinkingPart{Content: tp.Content + content}
            return
        }
    }
    msg.Parts = append(msg.Parts, ThinkingPart{Content: content})
}

// startToolCall creates a new ToolCallPart in Running state.
func (m *Model) startToolCall(chunk api.StreamChunk) {
    msg := m.ensureAssistantMessage()
    msg.Parts = append(msg.Parts, ToolCallPart{
        ID:          chunk.ToolCallID,
        Name:        chunk.ToolName,
        DisplayType: DisplayType(chunk.DisplayType),
        State:       ToolCallRunning,
        Input:       chunk.ToolInput,
    })
}

// endToolCall finds the matching ToolCallPart by ID and updates it.
func (m *Model) endToolCall(chunk api.StreamChunk) {
    msg := m.currentAssistantMessage()
    if msg == nil {
        return
    }
    for i, p := range msg.Parts {
        if tc, ok := p.(ToolCallPart); ok && tc.ID == chunk.ToolCallID {
            tc.Result = chunk.Content
            tc.Error = chunk.ToolError
            if tc.Error != "" {
                tc.State = ToolCallFailed
            } else {
                tc.State = ToolCallComplete
            }
            msg.Parts[i] = tc
            return
        }
    }
}

// ensureAssistantMessage returns a pointer to the last assistant message,
// creating one if needed.
func (m *Model) ensureAssistantMessage() *Message {
    if len(m.messages) == 0 || m.messages[len(m.messages)-1].Role != RoleAssistant {
        m.messages = append(m.messages, Message{Role: RoleAssistant})
    }
    return &m.messages[len(m.messages)-1]
}

// currentAssistantMessage returns a pointer to the last assistant message, or nil.
func (m *Model) currentAssistantMessage() *Message {
    if len(m.messages) > 0 && m.messages[len(m.messages)-1].Role == RoleAssistant {
        return &m.messages[len(m.messages)-1]
    }
    return nil
}

// finalizeRaw builds the Raw field from text parts for backward compat.
func (m *Model) finalizeRaw() {
    msg := m.currentAssistantMessage()
    if msg == nil {
        return
    }
    var sb strings.Builder
    for _, p := range msg.Parts {
        if tp, ok := p.(TextPart); ok {
            sb.WriteString(tp.Content)
        }
    }
    msg.Raw = sb.String()
}

// appendPart adds a part to the last message of the given role, creating one if needed.
func (m *Model) appendPart(role Role, part MessagePart) {
    if len(m.messages) == 0 || m.messages[len(m.messages)-1].Role != role {
        m.messages = append(m.messages, Message{Role: role})
    }
    m.messages[len(m.messages)-1].Parts = append(m.messages[len(m.messages)-1].Parts, part)
}
```

### 4. renderMessage dispatch

In `app/cli/internal/chat/view.go`, `renderMessage` switches from rendering `msg.Content` to iterating `msg.Parts`:

```go
func renderMessage(msg Message, width int) string {
    switch msg.Role {
    case RoleUser:
        return renderUserMessage(msg, width)
    case RoleAssistant:
        return renderAssistantMessage(msg, width)
    case RoleSystem:
        return renderSystemMessage(msg, width)
    }
    return ""
}

func renderUserMessage(msg Message, width int) string {
    return fmt.Sprintf(" %s %s", ui.Dim.Render("you:"), ui.Fg.Render(msg.Content()))
}

func renderSystemMessage(msg Message, width int) string {
    t := theme.Active()
    sysStyle := lipgloss.NewStyle().Foreground(t.Categories[theme.CatSystem])
    return fmt.Sprintf("  %s %s", sysStyle.Render("sys:"), sysStyle.Render(msg.Content()))
}

func renderAssistantMessage(msg Message, width int) string {
    prefix := ui.Accent.Render("sb:")
    contentWidth := width - 4
    if contentWidth < 20 {
        contentWidth = 20
    }

    var sections []string
    for _, part := range msg.Parts {
        sections = append(sections, renderPart(part, contentWidth))
    }

    // If no parts (legacy message with only Raw), fall back to markdown render
    if len(sections) == 0 && msg.Raw != "" {
        sections = append(sections, ui.RenderMarkdown(msg.Raw, contentWidth))
    }

    rendered := strings.Join(sections, "\n")
    lines := strings.Split(rendered, "\n")
    if len(lines) > 1 {
        indent := strings.Repeat(" ", lipgloss.Width("  "+prefix+" "))
        for i := 1; i < len(lines); i++ {
            lines[i] = indent + lines[i]
        }
    }
    return fmt.Sprintf("  %s %s", prefix, strings.Join(lines, "\n"))
}
```

#### Per-part rendering

```go
func renderPart(part MessagePart, width int) string {
    switch p := part.(type) {
    case TextPart:
        return ui.RenderMarkdown(p.Content, width)
    case ThinkingPart:
        return renderThinkingPart(p, width)
    case ToolCallPart:
        return renderToolCallPart(p, width)
    case ErrorPart:
        return ui.Red.Render("Error: " + p.Message)
    }
    return ""
}
```

#### Thinking part rendering

Dim, collapsed by default. Shows first line as a summary:

```go
func renderThinkingPart(p ThinkingPart, width int) string {
    if p.Content == "" {
        return ""
    }
    lines := strings.Split(p.Content, "\n")
    summary := lines[0]
    if len(summary) > 60 {
        summary = summary[:57] + "..."
    }
    return ui.Dim.Render("thinking: " + summary)
}
```

#### Tool call rendering by DisplayType

This dispatches to molecule components from SB-027. Until those exist, use inline fallbacks:

```go
func renderToolCallPart(p ToolCallPart, width int) string {
    // Status indicator
    var status string
    switch p.State {
    case ToolCallRunning:
        status = ui.Accent.Render("running")
    case ToolCallComplete:
        status = ui.Green.Render("done")
    case ToolCallFailed:
        status = ui.Red.Render("failed")
    }

    header := ui.Dim.Render("tool: ") + ui.Fg.Render(p.Name) + "  " + status

    if p.State == ToolCallRunning {
        return header
    }

    if p.Error != "" {
        return header + "\n" + ui.Red.Render(p.Error)
    }

    // Dispatch result rendering by DisplayType
    switch p.DisplayType {
    case DisplayDiff:
        // SB-027: molecules.DiffBlock(ctx, data)
        // Fallback until molecule exists:
        return header + "\n" + renderCodeFallback(p.Result, width)
    case DisplayCode:
        // SB-027: atoms.CodeBlock(ctx, data)
        return header + "\n" + renderCodeFallback(p.Result, width)
    case DisplayBash:
        // SB-027: atoms.CodeBlock(ctx, CodeBlockData{Code: p.Result, Language: "bash"})
        return header + "\n" + renderCodeFallback(p.Result, width)
    default: // DisplayGeneric
        // SB-027: molecules.ToolCallBlock(ctx, data)
        return header + "\n" + ui.Dim.Render(truncate(p.Result, 200))
    }
}

func renderCodeFallback(content string, width int) string {
    ctx := atoms.DefaultContext(width)
    return atoms.CodeBlock(ctx, atoms.CodeBlockData{Code: content})
}

func truncate(s string, max int) string {
    if len(s) <= max {
        return s
    }
    return s[:max-3] + "..."
}
```

### 5. Migration path from flat Content to Parts

The migration is incremental and backward compatible:

**Phase A (this issue):**
1. Add `Parts []MessagePart` and `Raw string` to `Message`
2. Change `Content string` to a `Content() string` method
3. Update all call sites that read `msg.Content` to call `msg.Content()`
4. Update `handleResponse` to dispatch by chunk type
5. Update `renderMessage` to iterate parts
6. User messages and system messages continue using `Raw` directly (they have no parts)

**Call sites to update for Content -> Content():**
- `view.go:renderMessage` (the main one, replaced by part iteration)
- `model.go:submit()` line 209 -- creates user messages. Change to: `Message{Role: RoleUser, Raw: text}`
- `model.go:showHelp()` line 267 -- creates system messages. Change to: `Message{Role: RoleSystem, Raw: ...}`
- `model.go:handleResponse` error cases -- change to append `ErrorPart`

**For user/system messages**, set `Raw` directly (no parts needed):

```go
// User message creation (in submit()):
m.messages = append(m.messages, Message{Role: RoleUser, Raw: text})

// System message creation (in showHelp()):
m.messages = append(m.messages, Message{Role: RoleSystem, Raw: content})
```

### 6. Backward compatibility for gallery mode

The `Raw` field on `Message` always holds the concatenated text content. It is:
- Set directly for user and system messages
- Built from TextParts by `finalizeRaw()` when streaming completes
- Used by `Content()` as the fallback when `Parts` is empty

This means any future gallery/export feature can iterate messages and read `msg.Raw` for a plain-text view without needing to understand parts.

For loading historical conversations (from `GetConversation` API), the API already returns `Parts []MessagePart` per message. A conversion function maps API parts to chat parts:

```go
func partsFromAPI(apiParts []api.MessagePart) ([]MessagePart, string) {
    var parts []MessagePart
    var raw strings.Builder
    for _, ap := range apiParts {
        content := ""
        if ap.Content != nil {
            content = *ap.Content
        }
        switch ap.Type {
        case "text":
            parts = append(parts, TextPart{Content: content})
            raw.WriteString(content)
        case "tool_use":
            parts = append(parts, ToolCallPart{
                ID:    deref(ap.ToolCallID),
                Name:  deref(ap.ToolName),
                State: ToolCallComplete,
            })
        default:
            parts = append(parts, TextPart{Content: content})
            raw.WriteString(content)
        }
    }
    return parts, raw.String()
}
```

Note: The `api.MessagePart` struct (in `types.go`) already exists and has `Type`, `Content` fields. It will need `ToolCallID`, `ToolName`, `DisplayType` fields added (some already present as nullable).

## File changes summary

| File | Change |
|------|--------|
| `app/cli/internal/api/client.go` | Add fields to `StreamChunk`: `ToolCallID`, `ToolName`, `DisplayType`, `ToolInput`, `ToolError` |
| `app/cli/internal/api/sse.go` | Update `SSEToolStartData`, `SSEToolEndData` structs; update `ChunkFromSSE` to populate new fields |
| `app/cli/internal/chat/model.go` | Add `PartType`, `ToolCallState`, `DisplayType` enums; `MessagePart` interface + 4 concrete types; update `Message` struct; rewrite `handleResponse`; add accumulation helpers |
| `app/cli/internal/chat/view.go` | Rewrite `renderMessage` to dispatch per part; add `renderPart`, `renderThinkingPart`, `renderToolCallPart`, `renderCodeFallback` |

No new files. Four files modified.

## Testing strategy

### Unit tests in `app/cli/internal/chat/model_test.go`

1. **`TestAccumulateText`** -- Send multiple `ChunkText` responses. Assert the last assistant message has a single `TextPart` with concatenated content.

2. **`TestAccumulateTextAfterToolCall`** -- Send text, then tool_start, then more text. Assert the message has three parts: `TextPart`, `ToolCallPart`, `TextPart`.

3. **`TestAccumulateThinking`** -- Send `ChunkThinking` chunks. Assert a single `ThinkingPart` with concatenated content.

4. **`TestToolCallLifecycle`** -- Send `ChunkToolStart` then `ChunkToolEnd`. Assert the `ToolCallPart` transitions from `ToolCallRunning` to `ToolCallComplete` with the result populated.

5. **`TestToolCallFailed`** -- Send `ChunkToolStart` then `ChunkToolEnd` with error. Assert `ToolCallFailed` state and error message.

6. **`TestToolCallUnmatchedEnd`** -- Send `ChunkToolEnd` with no matching start. Assert no panic, no new part created.

7. **`TestErrorChunk`** -- Send a chunk with `Error != nil`. Assert an `ErrorPart` is appended and streaming stops.

8. **`TestFinalizeRaw`** -- After streaming completes (Done=true), assert `msg.Raw` contains concatenated text from all `TextPart`s only (no thinking, no tool results).

9. **`TestContentMethod`** -- Assert `Message.Content()` returns `Raw` when set, falls back to concatenating `TextPart`s.

10. **`TestBackwardCompatUserMessage`** -- Create a user message with `Raw` set. Assert `Content()` returns the raw text.

### Unit tests in `app/cli/internal/chat/view_test.go`

11. **`TestRenderTextPart`** -- Assert text parts go through `RenderMarkdown`.

12. **`TestRenderThinkingPart`** -- Assert thinking renders as dim text with truncated first line.

13. **`TestRenderToolCallRunning`** -- Assert running tool shows name + "running" status, no result.

14. **`TestRenderToolCallComplete`** -- Assert completed tool shows name + "done" + result rendered via code fallback.

15. **`TestRenderToolCallByDisplayType`** -- Parametrized: diff, code, bash, generic. Assert each dispatches to the right renderer (once SB-027 molecules exist, update to assert molecule usage).

16. **`TestRenderErrorPart`** -- Assert error parts render in red.

17. **`TestRenderLegacyRawOnly`** -- Message with no Parts but Raw set. Assert it falls back to markdown rendering.

### Unit tests in `app/cli/internal/api/sse_test.go`

18. **`TestChunkFromSSEToolStartFields`** -- Assert `ToolCallID`, `ToolName`, `DisplayType`, `ToolInput` are populated from `agent.tool.start` event JSON.

19. **`TestChunkFromSSEToolEndFields`** -- Assert `ToolCallID`, `ToolName`, `DisplayType`, `ToolError` (when present) are populated from `agent.tool.end` event JSON.

20. **`TestChunkFromSSEToolStartMissingDisplayType`** -- When `display_type` is absent from JSON (pre-SB-026 backend), assert `DisplayType` defaults to empty string (caller treats as generic).

### Test approach

All tests are pure unit tests with no external dependencies. The model tests construct `ResponseMsg` values directly and call `handleResponse` in sequence. The view tests construct `Message` values with parts and call `renderMessage` directly. No mocking needed beyond constructing data.
