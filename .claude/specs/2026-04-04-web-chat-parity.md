---
title: "Web Chat Parity: CLI-to-Frontend Component Migration"
status: draft
date: 2026-04-04
epic: EP-015
---

# Web Chat Parity: CLI-to-Frontend Component Migration

## Overview

The Go CLI has a full-featured chat experience with multi-part messages, markdown rendering, SSE streaming, tool call visualization, diff blocks, thinking display, status indicators, and slash command autocomplete. The React frontend's AgentPanel is a shallow mock sidebar rendering plain text bubbles. This epic bridges the gap to achieve functional parity.

## Current State

### CLI Chat (reference implementation)
| Layer | Components |
|-------|-----------|
| **Atoms** | TextBlock, CodeBlock, Spinner, Badge, Icon, InlineCode, Separator |
| **Molecules** | StatusBlock (spinner+verb+badges), ToolCallBlock (3-state expandable), DiffBlock (colored unified diff) |
| **Message Parts** | TextPart (markdown), ThinkingPart (collapsible), ToolCallPart (lifecycle), ErrorPart (styled) |
| **Chat Model** | Multi-part messages with Role enum, SSE streaming with 6 chunk types |
| **Controls** | Autocomplete dropdown with fuzzy matching, input prompt with slash commands |
| **Theme** | Semantic tokens: Category (Agent/System/Tool/User), Hierarchy (Primary-Quaternary), Emphasis (Strong/Normal/Subtle), Status (Success/Error/Warning/Info/Running/Muted) |

### Frontend (current)
| Layer | Relevant Components |
|-------|-----------|
| **Atoms** | Badge, Icon, Skeleton, Button — exist but not chat-oriented |
| **Molecules** | None chat-related (all diff-viewer/stack-focused) |
| **Organisms** | AgentPanel — plain text bubbles, mock 500ms delay, no streaming |
| **Types** | Generated `Message` schema (DB entity, not chat parts), `AgentMessage` local type (role + content string) |
| **Tokens** | CSS custom properties in `index.css` — backgrounds, borders, foreground, semantic colors, typography. No semantic token system matching CLI's Category/Hierarchy/Status model |
| **Hooks** | No SSE/streaming hooks. Generated REST hooks for messages entity |

### Backend (available)
- **SSE endpoint**: `GET /api/v1/events/stream?channel=` — StreamingResponse with keepalive, backpressure
- **Conversation API**: CRUD + `/send` (placeholder) + `/branch`
- **PubSub**: DomainEvent → EventBus → BroadcastBridge → SSE clients

## Design Decisions

### 1. Chat-specific token layer via CSS custom properties
Extend existing `index.css` CSS variables with chat-semantic tokens that map to CLI's Category/Hierarchy/Status model. No new token infrastructure — just additional `--chat-*` custom properties. Functional coverage first.

### 2. Reuse existing atoms where possible
Frontend Badge, Icon, Skeleton, Button already exist. Extend or wrap rather than duplicate. New chat atoms only where no existing atom covers the need.

### 3. Multi-part message model as TypeScript types
Define `ChatMessage` with `ChatMessagePart[]` union type mirroring CLI's sealed interface. This is the data contract between SSE stream and React rendering.

### 4. SSE via custom hook, not React Query
React Query is for request-response. SSE streaming needs a `useEventSource` hook that manages EventSource lifecycle, reconnection, and dispatches chunk events to a message reducer.

### 5. Incremental migration
AgentPanel evolves in-place. Each layer builds on the previous. No big-bang rewrite.

---

## Epic Breakdown: EP-015

### Layer 0: Foundation (Types + Tokens + Streaming)

#### SB-120: Chat Message Types
Define the TypeScript type system for multi-part chat messages.
- **Types**: `ChatRole` (user/assistant/system), `PartType` (text/thinking/toolCall/error), `DisplayType` (diff/code/bash/generic), `ToolCallState` (running/complete/failed)
- **Types**: `TextPart`, `ThinkingPart`, `ToolCallPart`, `ErrorPart` — discriminated union as `ChatMessagePart`
- **Type**: `ChatMessage` = { id, role, parts, timestamp }
- **Dependencies**: None
- **Acceptance Criteria**:
  - All part types match CLI's `model.go` definitions
  - Exported from `src/types/chat.ts`
  - Includes SSE chunk types: `ChunkText`, `ChunkThinking`, `ChunkToolStart`, `ChunkToolEnd` with `Done` flag
  - `StreamChunk` type includes all fields: content, type, done, error, toolCallId, toolName, displayType, toolInput, toolError

#### SB-121: Chat Design Tokens
Add chat-semantic CSS custom properties to the existing token system.
- Map CLI's Category/Status model to CSS variables: `--chat-agent`, `--chat-system`, `--chat-tool`, `--chat-user`, `--chat-success`, `--chat-error`, `--chat-warning`, `--chat-info`, `--chat-running`, `--chat-muted`
- Add hierarchy modifiers: `--chat-text-primary`, `--chat-text-secondary`, `--chat-text-tertiary`, `--chat-text-quaternary`
- Emphasis (Strong/Normal/Subtle) handled natively by CSS font-weight/opacity — no custom properties needed
- **Dependencies**: None
- **Acceptance Criteria**:
  - Variables defined in `index.css` under `:root`
  - Covers all 4 categories, 6 active statuses (Success/Error/Warning/Info/Running/Muted), 4 hierarchy levels
  - Existing component tokens unchanged

#### SB-122: useEventSource Hook (SSE Streaming)
Custom hook to connect to the backend SSE endpoint and parse chat stream events.
- Connects to `/api/v1/events/stream?channel={channel}` (channel naming convention TBD — likely `conversation:{id}` or global)
- Parses SSE events (7 types + aliases): `agent.message.chunk`, `agent.message.complete`, `agent.reasoning`/`thinking`, `agent.tool.start`/`tool_start`, `agent.tool.end`/`tool_end`, `done`, `agent.error`/`error`
- Returns `{ chunks, isConnected, error, reconnect }` — pushes parsed `StreamChunk` objects
- Handles reconnection with exponential backoff
- **Dependencies**: SB-120
- **Acceptance Criteria**:
  - Hook manages EventSource lifecycle (open/close/error)
  - Parses all 7 SSE event types (plus alias forms) into typed StreamChunk
  - `agent.message.complete` signals stream end with token counts
  - Auto-reconnects on disconnect (max 3 retries)
  - Cleans up on unmount

#### SB-123: useChatMessages Reducer
State management hook that reduces SSE chunks into a `ChatMessage[]` array.
- Accepts `StreamChunk` events from `useEventSource`
- Maintains message list with multi-part accumulation
- Handles: append text to current TextPart, create ThinkingPart, open/close ToolCallPart, create ErrorPart
- Supports optimistic user message insertion
- **Dependencies**: SB-120, SB-122
- **Acceptance Criteria**:
  - Text chunks accumulate into current TextPart (streaming)
  - Tool start creates new ToolCallPart in "running" state; tool end updates to "complete"/"failed"
  - Thinking chunks accumulate into ThinkingPart
  - User messages inserted immediately (optimistic)

---

### Layer 1: Chat Atoms

#### SB-124: ChatCodeBlock Atom
Syntax-highlighted code block for use inside chat messages.
- Renders multi-line code with optional language label and line numbers
- Uses existing Shiki infrastructure (`src/lib/shiki.ts`) for highlighting
- Left border gutter styling (matching CLI's `│` visual pattern via CSS)
- **Dependencies**: SB-121
- **Acceptance Criteria**:
  - Renders code with syntax highlighting via Shiki
  - Shows language label when provided
  - Optional line numbers
  - Uses `--chat-tool` token for gutter/border

#### SB-125: ChatSpinner Atom
Animated loading indicator for running operations.
- CSS animation (not JS interval) — rotating or pulsing indicator
- Accepts `label` prop for contextual text (e.g., "Running...")
- Small/inline variant for use inside status blocks
- **Dependencies**: SB-121
- **Acceptance Criteria**:
  - Smooth animation via CSS `@keyframes`
  - Accepts label prop displayed alongside spinner
  - Sizes: `sm` (inline) and `md` (standalone)

#### SB-126: ChatInlineCode Atom
Inline code span for flowing text within chat messages.
- Monospace font, subtle background, no line breaks
- Styled with `--chat-tool` tokens
- **Dependencies**: SB-121
- **Acceptance Criteria**:
  - Renders inline `<code>` with monospace font
  - Visually distinct from surrounding text
  - No line-break behavior

#### SB-127: ChatSeparator Atom
Horizontal rule divider for chat sections.
- Full-width line matching existing Separator patterns
- **Dependencies**: SB-121
- **Acceptance Criteria**:
  - Renders `<hr>` styled with `--chat-system` border token
  - Full width of chat container

---

### Layer 2: Chat Molecules

#### SB-128: ChatMarkdown Molecule
Markdown renderer for assistant message text parts.
- Parses markdown to React elements (headers, bold, italic, lists, links, inline code, code blocks)
- Uses `ChatCodeBlock` for fenced code blocks, `ChatInlineCode` for inline code
- Supports incremental/streaming text (renders partial markdown gracefully)
- **Dependencies**: SB-121, SB-124, SB-126
- **Acceptance Criteria**:
  - Renders H1-H3, bold, italic, unordered/ordered lists, links, inline code, fenced code blocks
  - Code blocks delegate to ChatCodeBlock with language detection
  - Handles incomplete markdown during streaming (unclosed blocks)
  - Uses chat design tokens for heading hierarchy

#### SB-129: ChatStatusBlock Molecule
Status indicator with spinner, verb label, and optional badges.
- Composes: ChatSpinner + text label + optional Badge (elapsed time) + optional Badge (count)
- Maps to CLI's StatusBlock: verb + elapsed + count
- **Dependencies**: SB-125, existing Badge atom
- **Acceptance Criteria**:
  - Renders spinner + verb text inline
  - Shows elapsed badge when provided
  - Shows count badge (e.g., "3/7") when provided
  - Responsive: hides badges at narrow widths

#### SB-130: ChatToolCallBlock Molecule
Tool invocation display with lifecycle states and expandable detail.
- Header: status icon + tool name badge + status label badge
- States: running (spinner + "running"), success (checkmark + "done"), error (X + "failed")
- Expandable body: input (ChatCodeBlock), output (ChatCodeBlock), error message
- Collapsed by default when complete, expanded when running
- **Dependencies**: SB-124, SB-125, existing Badge/Icon atoms
- **Acceptance Criteria**:
  - Three visual states matching CLI (running/success/error)
  - Click to expand/collapse input and output sections
  - Tool name displayed as filled badge
  - Error state shows error message prominently

#### SB-131: ChatDiffBlock Molecule
Inline unified diff display for file changes shown in chat.
- File header badge + colored diff lines (added/removed/context)
- Parses unified diff format into typed lines
- Green for additions, red for deletions, neutral for context
- **Dependencies**: SB-121, existing Badge atom
- **Acceptance Criteria**:
  - Parses unified diff string into typed lines
  - Color-coded: green (+), red (-), neutral (context)
  - File name displayed as header badge
  - Line prefixes (+/-/space) rendered

#### SB-132: ChatThinkingBlock Molecule
Collapsible display for assistant reasoning/thinking content.
- Collapsed: shows truncated preview (first ~60 chars + "...")
- Expanded: shows full thinking content (plain text, dimmed)
- Toggle via click
- **Dependencies**: SB-121
- **Acceptance Criteria**:
  - Default collapsed with truncated preview
  - Click toggles full content
  - Dimmed/tertiary styling to distinguish from main response
  - Label: "thinking..." or similar indicator

#### SB-133: ChatErrorBlock Molecule
Styled error message display for stream/API errors.
- Error icon + message text in error color
- Distinct from tool call errors (this is stream-level)
- **Dependencies**: SB-121, existing Icon atom
- **Acceptance Criteria**:
  - Renders error icon + message
  - Uses `--chat-error` token for styling
  - Visually distinct from assistant text

---

### Layer 3: Message Rendering

#### SB-134: MessagePart Dispatcher
Component that renders a single `ChatMessagePart` by dispatching to the correct molecule.
- Switch on `part.type`: text → ChatMarkdown, thinking → ChatThinkingBlock, toolCall → ChatToolCallBlock (with DisplayType routing to ChatDiffBlock for diffs), error → ChatErrorBlock
- Handles ToolCallPart.displayType: "diff" renders ChatDiffBlock for output, "code"/"bash" renders ChatCodeBlock, "generic" renders default
- **Dependencies**: SB-128, SB-130, SB-131, SB-132, SB-133
- **Acceptance Criteria**:
  - Correctly dispatches all 4 part types
  - ToolCall displayType "diff" renders diff output via ChatDiffBlock
  - Unknown part types render graceful fallback
  - Each part separated by appropriate spacing

#### SB-135: ChatMessageRow Component
Renders a single `ChatMessage` with role indicator and all its parts.
- Role-based layout: user (right-aligned or distinct style), assistant (left with "sb:" label), system (centered/italic)
- Iterates `message.parts` and renders via MessagePart dispatcher
- Streaming indicator: shows `ChatStatusBlock` when assistant message is still streaming
- **Dependencies**: SB-134, SB-129
- **Acceptance Criteria**:
  - Visual distinction between user/assistant/system roles
  - Renders all parts in sequence via dispatcher
  - Shows streaming status indicator for in-progress messages
  - Timestamp or metadata display (optional)

---

### Layer 4: Chat Input & Commands

#### SB-136: ChatInput Component
Enhanced text input with submit handling and slash command detection.
- Textarea with auto-resize, submit on Enter (Shift+Enter for newline)
- Detects `/` prefix to trigger autocomplete
- Emits: `onSubmit(text)`, `onSlashCommand(command)`
- **Dependencies**: SB-121
- **Acceptance Criteria**:
  - Auto-resizing textarea
  - Enter submits, Shift+Enter adds newline
  - Detects `/` at start of input
  - Disabled state during streaming

#### SB-137: SlashCommandAutocomplete Component
Dropdown autocomplete for slash commands in chat input.
- Fuzzy + prefix matching on command names
- Keyboard navigation (up/down, Tab, Enter to select, Esc to dismiss)
- Renders command name + description per suggestion
- Built-in commands: `/help`, `/clear`, `/agents`
- **Dependencies**: SB-136, SB-121
- **Acceptance Criteria**:
  - Shows dropdown when `/` typed in input
  - Fuzzy matching filters as user types
  - Keyboard navigation (arrows + Tab + Enter + Esc)
  - Max 6 visible suggestions

---

### Layer 5: Chat Organism

#### SB-138: ChatRoom Organism
Full chat experience replacing AgentPanel's message area.
- Composes: message list (ChatMessageRow[]), streaming status, ChatInput with autocomplete
- Manages scroll: auto-scroll on new messages, scroll-to-bottom button when scrolled up
- Wires `useChatMessages` reducer to `useEventSource` hook
- Header: conversation metadata (agent name, exchange count)
- **Dependencies**: SB-123, SB-135, SB-136, SB-137
- **Acceptance Criteria**:
  - Renders full message history with multi-part messages
  - Auto-scrolls on new content, manual scroll override
  - Input at bottom with slash command support
  - Header shows agent name and conversation info
  - Streaming messages update in real-time

#### SB-139: AgentPanel Migration
Replace AgentPanel internals with ChatRoom organism.
- AgentPanel retains its collapsible sidebar shell but delegates rendering to ChatRoom
- Remove mock message logic and plain text bubbles
- Wire to real conversation API: create conversation on first message, stream via SSE
- Quick action buttons become slash commands or preserved as UI shortcuts
- **Dependencies**: SB-138
- **Acceptance Criteria**:
  - AgentPanel renders ChatRoom inside its existing collapsible shell
  - Real conversation created via `/api/v1/conversations/` on first send
  - Messages streamed via SSE, not mocked
  - Existing toggle/collapse behavior preserved
  - Quick actions preserved or migrated to slash commands

---

## Build Order (Dependency Graph)

```
Layer 0 (parallel):
  SB-120 (types) ──┬──→ SB-122 (useEventSource) ──→ SB-123 (useChatMessages)
  SB-121 (tokens)  │
                   │
Layer 1 (parallel, after SB-121):
  SB-124 (CodeBlock) ──┐
  SB-125 (Spinner)     │
  SB-126 (InlineCode)  ├──→ Layer 2
  SB-127 (Separator)   │
                       │
Layer 2 (after Layer 1):
  SB-128 (Markdown) ────────┐
  SB-129 (StatusBlock)      │
  SB-130 (ToolCallBlock) ───┤
  SB-131 (DiffBlock)        ├──→ SB-134 (Dispatcher) → SB-135 (MessageRow)
  SB-132 (ThinkingBlock)    │
  SB-133 (ErrorBlock) ──────┘
                              
Layer 3-4 (sequential):
  SB-134 (Dispatcher) → SB-135 (MessageRow)
  SB-136 (ChatInput) → SB-137 (Autocomplete)

Layer 5 (after all above):
  SB-138 (ChatRoom) → SB-139 (AgentPanel Migration)
```

## Component Mapping Table

| CLI Component | Web Component | Issue | Layer |
|--------------|---------------|-------|-------|
| — | Chat TypeScript types | SB-120 | 0 |
| Theme tokens | CSS custom properties | SB-121 | 0 |
| SSE parser (`sse.go`) | `useEventSource` hook | SB-122 | 0 |
| Message model (`model.go`) | `useChatMessages` reducer | SB-123 | 0 |
| CodeBlock atom | ChatCodeBlock | SB-124 | 1 |
| Spinner atom | ChatSpinner | SB-125 | 1 |
| InlineCode atom | ChatInlineCode | SB-126 | 1 |
| Separator atom | ChatSeparator | SB-127 | 1 |
| MarkdownRenderer | ChatMarkdown | SB-128 | 2 |
| StatusBlock molecule | ChatStatusBlock | SB-129 | 2 |
| ToolCallBlock molecule | ChatToolCallBlock | SB-130 | 2 |
| DiffBlock molecule | ChatDiffBlock | SB-131 | 2 |
| ThinkingPart rendering | ChatThinkingBlock | SB-132 | 2 |
| ErrorPart rendering | ChatErrorBlock | SB-133 | 2 |
| Part dispatch (view.go) | MessagePart Dispatcher | SB-134 | 3 |
| Message rendering (view.go) | ChatMessageRow | SB-135 | 3 |
| Input prompt | ChatInput | SB-136 | 4 |
| Autocomplete | SlashCommandAutocomplete | SB-137 | 4 |
| Chat view | ChatRoom organism | SB-138 | 5 |
| — | AgentPanel migration | SB-139 | 5 |

## Scope Notes

- **Functional coverage first**: Each component must work correctly. Styling refinement (animations, polish, responsive breakpoints) is a follow-up concern.
- **TextBlock not needed**: The web doesn't need a TextBlock atom — HTML/CSS handles text styling natively. ChatMarkdown covers formatted text.
- **Badge/Icon reuse**: Existing frontend Badge and Icon atoms are used directly. No new atoms needed for these.
- **No backend changes required**: The SSE endpoint, conversation API, and PubSub system already exist. The `/send` endpoint placeholder will need Claude integration separately (out of scope for this epic).

## Explicitly Out of Scope

- **Conversation picker / history loading**: Loading past conversations or switching between them. The backend supports `GET /conversations/{id}` but UI for browsing/resuming is deferred.
- **Branch conversations**: The backend has a `/branch` endpoint and the CLI tracks `IsBranch`. Conversation branching UI is deferred.
- **Token usage display**: The backend returns `input_tokens`/`output_tokens` and the CLI tracks `ExchangeCount`. Token usage dashboard is deferred.
- **Claude integration**: The `/send` endpoint is a placeholder. Wiring to actual Claude API is a separate epic.
- **Advanced keyboard shortcuts**: CLI supports `ctrl+w` (delete word), `ctrl+u` (delete line), `alt+backspace`. These are deferred from ChatInput (SB-136) but noted for future parity.
