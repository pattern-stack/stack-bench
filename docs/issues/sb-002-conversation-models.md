---
id: SB-002
title: Conversation domain features
status: draft
epic: EP-001
depends_on: [SB-001]
branch:
pr:
stack:
stack_index:
created: 2026-03-14
parallel_with: [SB-003, SB-004]
---

# Conversation Domain Features

## Summary

Four pattern-stack features for the conversation domain: Conversation, Message, MessagePart, ToolCall. Each built with proper Field() system and Pattern class. Services are minimal — inherit BaseService, add custom queries only when molecules need them (SB-005).

**Parallel:** This can be developed in a worktree alongside SB-003 and SB-004 after SB-001 merges.

## Scope

What's in:
- Conversation(EventPattern) — states: created → active → completed → failed
- Message(BasePattern) — kind (request/response), sequence, token tracking
- MessagePart(BasePattern) — part_type, content, tool_call fields
- ToolCall(EventPattern) — states: pending → executed → failed, duration tracking
- Pydantic input/output schemas for each
- Minimal services: inherit BaseService, no custom queries yet (add in SB-005 as needed)
- Alembic migration for all 4 tables
- Unit tests: model creation, state machines

What's out:
- Custom service queries (added as-needed when SB-005 molecule consumes them)
- REST endpoints (SB-006)
- ConversationEntity molecule (SB-005)
- Any agent/execution models (SB-003, SB-004 — parallel)

## Implementation

```
features/
├── conversations/
│   ├── __init__.py
│   ├── models.py           # Conversation(EventPattern)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── input.py        # ConversationCreate, ConversationUpdate
│   │   └── output.py       # ConversationResponse
│   └── service.py          # ConversationService(BaseService) — inherited CRUD only
├── messages/
│   ├── __init__.py
│   ├── models.py           # Message(BasePattern)
│   ├── schemas/...
│   └── service.py          # MessageService(BaseService) — inherited CRUD only
├── message_parts/
│   ├── __init__.py
│   ├── models.py           # MessagePart(BasePattern)
│   ├── schemas/...
│   └── service.py          # MessagePartService(BaseService) — inherited CRUD only
└── tool_calls/
    ├── __init__.py
    ├── models.py           # ToolCall(EventPattern)
    ├── schemas/...
    └── service.py          # ToolCallService(BaseService) — inherited CRUD only
```

### Key Model Fields (adapted from existing)

**Conversation:** agent_name, model, state, error_message, metadata_ (JSON), agent_config (JSON), exchange_count, total_input_tokens, total_output_tokens, branched_from_id (self-FK), branched_at_sequence

**Message:** conversation_id (FK), kind (request/response), sequence, run_id, input_tokens, output_tokens. Unique constraint: (conversation_id, sequence)

**MessagePart:** message_id (FK), position, part_type, content, tool_call_id, tool_name, tool_arguments (JSON). Unique constraint: (message_id, position)

**ToolCall:** conversation_id (FK), tool_call_id, tool_name, arguments (JSON), result, error, state, duration_ms, request_part_id (FK), response_part_id (FK)

## Verification

- [ ] Migration creates 4 tables with correct columns
- [ ] Conversation state machine: created → active, active → completed, active → failed
- [ ] ToolCall state machine: pending → executed, pending → failed
- [ ] BaseService inherited CRUD works (create, get, list) for all 4
- [ ] Tests pass

## Notes

Source: `agentic_patterns/app/db/models/{conversation,message,message_part,tool_call}.py`
These were plain SQLAlchemy Base models — we rebuild as BasePattern/EventPattern with Field().
Custom service methods (get_by_conversation, get_ordered, etc.) added in SB-005 when the molecule needs them.
