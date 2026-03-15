---
id: EP-002
title: CLI Chat + Agent Runtime
status: active
created: 2026-03-14
target:
---

# CLI Chat + Agent Runtime

## Objective

Wire the Go CLI to the Python backend so users can have real conversations with Claude-backed agents. Build the runtime primitives (ConversationRunner, AgentNode) that support single-agent chat now and multi-agent orchestration next.

## Issues

| ID | Title | Status | Depends On | GH |
|----|-------|--------|------------|-----|
| SB-008 | Backend conversation runtime (ConversationRunner + SSE) | in-progress | — | #10 / PR #16 |
| SB-009 | CLI chat mode (restructure + clean UI) | in-progress | — | #11 / PR #17 |
| SB-010 | Wire CLI chat to backend (HTTP client + SSE) | in-progress | SB-008, SB-009 | #12 / PR #18 |
| SB-011 | Go runtime manager (AgentNode + LocalNode) | in-progress | SB-010 | #13 / PR #19 |
| SB-012 | Conversation recall, restore, branch | in-progress | SB-011 | #14 / PR #20 |
| SB-013 | Streaming markdown renderer (Bubble Tea component) | in-progress | — | #15 / PR #18 |

## Dependency Graph

```
SB-008 (backend) ──┐
                    ├──→ SB-010 (wire) ──→ SB-011 (runtime) ──→ SB-012 (recall)
SB-009 (CLI)     ──┘
SB-013 (markdown) ──→ SB-010 (bundled in same PR)
```

## Stacking Strategy

Two stacks with diamond dependency:

```
sb-backend-runtime:  SB-008
sb-cli-chat:         SB-009 → SB-010 → SB-011 → SB-012
```

SB-008 merges to main first. SB-010 rebases onto main (which now has SB-008).

## Acceptance Criteria

- [ ] `just dev` in CLI auto-starts backend, opens chat
- [ ] User can select an agent and have a real conversation with Claude
- [ ] Messages, tool calls, and conversation state persisted to Postgres
- [ ] Agent responses stream in real-time (SSE → TUI)
- [ ] User can list past conversations, continue, or branch from history
- [ ] `AgentNode` interface ready for multi-agent extension

## Specs

- `docs/specs/2026-03-14-conversation-runtime.md`
- `docs/specs/2026-03-14-agent-node-extraction.md`
