---
id: SB-008
title: Backend conversation runtime (ConversationRunner + SSE)
status: in-progress
epic: EP-002
depends_on: []
branch: dugshub/sb-backend-runtime/1-backend-conversation-runtime
pr: 16
stack: sb-backend-runtime
stack_index: 1
created: 2026-03-14
---

# Backend Conversation Runtime

## Summary

Wire `POST /conversations/{id}/send` to call Claude via agentic-patterns AgentRunner, streaming the response as SSE. Build ConversationRunner bridge and AgentFactory.

## Scope

What's in:
- `ConversationRunner` molecule — loads history, assembles agent, calls runner, yields events
- `AgentFactory` — converts DB AgentConfig → agentic-patterns Agent
- SSE streaming endpoint replacing `/send` stub
- PersistenceExporter wiring
- Integration test with MockRunner

What's out:
- Go CLI (SB-009/SB-010)
- Runtime manager (SB-011)

## Implementation

```
backend/molecules/runtime/conversation_runner.py
backend/molecules/runtime/agent_factory.py
backend/organisms/api/routers/conversations.py
backend/tests/molecules/test_conversation_runner.py
```

## Verification

- [ ] `POST /conversations/{id}/send` returns `text/event-stream`
- [ ] Messages + parts + tool calls persisted to DB
- [ ] Conversation state transitions work
- [ ] `pts test` passes

## Notes

GH: #10
