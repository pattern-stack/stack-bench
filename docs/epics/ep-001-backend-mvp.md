---
id: EP-001
title: Backend MVP — Single-User Conversation API
status: active
created: 2026-03-14
target: 2026-03-14
---

# Backend MVP — Single-User Conversation API

## Objective

Stand up the pattern-stack Python backend in stack-bench with working conversation, agent, and execution domains. A user can create a conversation, send messages to a Claude-backed agent, and see everything persisted. All features built properly on pattern-stack (EventPattern, BasePattern, Field system, BaseService).

## Dependency Graph

```
SB-001 (bootstrap)
├── SB-002 (conversations) ──┐
├── SB-003 (agents) ──────────┼── SB-005 (molecule+facade) → SB-006 (REST) → SB-007 (wire)
└── SB-004 (execution) ·······
                         (independent, merges whenever)
```

**Critical path:** SB-001 → SB-002 → SB-005 → SB-006 → SB-007
**Parallel work:** SB-002, SB-003, SB-004 can be developed simultaneously in worktrees after SB-001 merges.

## Stacking Strategy

Not one linear stack — multiple stacks to enable parallel development:

| Stack | Issues | Notes |
|-------|--------|-------|
| `sb-bootstrap` | SB-001 | Foundation. Merges first. |
| `sb-conversations` | SB-002 → SB-005 → SB-006 → SB-007 | Critical path after bootstrap merges |
| `sb-agents` | SB-003 | Parallel. Worktree. Merges before SB-005 starts. |
| `sb-execution` | SB-004 | Parallel. Worktree. Independent, merges whenever. |

This tests the stack CLI's worktree support and parallel development workflow.

## Issues

| ID | Title | Status | Stack | Parallel? |
|----|-------|--------|-------|-----------|
| SB-001 | Project bootstrap | draft | sb-bootstrap | — |
| SB-002 | Conversation domain features | draft | sb-conversations | with SB-003, SB-004 |
| SB-003 | Agent domain features | draft | sb-agents | with SB-002, SB-004 |
| SB-004 | Execution domain features | draft | sb-execution | with SB-002, SB-003 |
| SB-005 | Conversation molecule + facade | draft | sb-conversations | after SB-002+003 merge |
| SB-006 | REST API organisms | draft | sb-conversations | after SB-005 |
| SB-007 | Integration wiring + seed + run | draft | sb-conversations | after SB-006 |

## Acceptance Criteria

- [ ] `make dev` starts backend with health endpoint
- [ ] POST /api/v1/conversations/ creates a conversation with a named agent
- [ ] POST /api/v1/conversations/{id}/send returns a Claude response
- [ ] Conversation, messages, parts, and tool calls persisted in Postgres
- [ ] All features use pattern-stack Field(), Pattern class, BaseService
- [ ] Routers consume API facade (not services directly)
- [ ] Tests pass with `make test`

## Notes

Source code adapted from agentic-patterns (app/backend/ and app/api/). Models rebuilt to follow pattern-stack conventions. Services added as-needed (minimal in features, custom queries added when molecules consume them).

Key pattern-stack layers: Features (models+schemas+minimal service) → Molecules (entities+facades) → Organisms (routers+CLI). The API facade in molecules is the interface boundary — REST and CLI both consume it.
