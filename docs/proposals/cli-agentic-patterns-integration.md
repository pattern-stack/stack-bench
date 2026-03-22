# Proposal: CLI ↔ Agentic-Patterns Integration

**Date:** 2026-03-22
**Author:** Dug + Claude
**Status:** exploring

## Context

The CLI has a component system (atoms/molecules), a goldmark markdown renderer, syntax highlighting, table rendering, viewport scrolling, and a clean app/chat layout split. The backend (agentic-patterns) has conversation runtime, agent definitions, SSE streaming, and tool execution.

The CLI currently connects via `api.Client` interface with HTTP+SSE. The chat model handles `Message{Role, Content}` — flat text only. To support real agent workflows, the CLI needs to render structured agent output (tool calls, thinking, approvals) and support human-in-the-loop interaction.

## Idea

### What the CLI needs to render

1. **Tool calls** — agent invokes a tool (file read, bash, edit). Show tool name, status (running/success/error), collapsible input/output. This is `ToolCallBlock` from the component spec.

2. **Thinking blocks** — agent's chain-of-thought. Collapsible, dimmed, separate from main output.

3. **Approval flow** — agent wants to do something dangerous. Show what it wants to do, wait for user confirmation (y/n/edit). This is `ConfirmPrompt` from the spec.

4. **Structured messages** — the `Message` model needs to carry `[]MessagePart` (text, tool_call, tool_result, thinking) instead of flat `Content string`. The backend API already has this shape.

5. **Multi-agent context** — when agents delegate to sub-agents, show the delegation chain. Badge the active agent.

### What the CLI needs for interaction

1. **Slash commands for agent control** — `/approve`, `/reject`, `/edit`, `/retry`, `/stop`
2. **Keyboard shortcuts** — `y` to approve, `n` to reject during confirmation prompts
3. **Tool call drill-down** — click or enter on a tool call to expand its input/output

### Integration path

1. Upgrade `Message` to carry `[]MessagePart` instead of flat `Content`
2. Build ToolCallBlock, ConfirmPrompt, StatusBlock (Spinner + verb)
3. Update `renderMessage` to dispatch on part types
4. Add SSE event types for tool_start/tool_end/thinking/approval_request
5. Wire approval flow into the Bubble Tea message loop

### What already works

- `api.StreamChunk` already has `Type` field (text, thinking, tool_start, tool_end)
- `api.Client` interface has the right shape
- Theme token system covers all the semantic dimensions needed (CatTool for tools, Status for running/success/error)
- Component system enforces clean rendering through atoms

## Open Questions

- How does the approval flow interact with streaming? Does the agent pause and wait, or is it a separate message type?
- Should tool call rendering be inline (within the message flow) or in a side panel?
- How do we handle long-running tools (minutes)? Progress indication?
- Do we need a separate "agent activity" view vs the chat view?

## Related

- `docs/specs/2026-03-21-cli-component-system.md` — Phase 4 (Spinner, StatusBlock) and Phase 6 (ToolCallBlock, ConfirmPrompt, DiffBlock)
- `docs/adrs/adr-001-cli-framework.md` — Go/Bubble Tea decision
- Backend conversation runtime (agentic-patterns)
