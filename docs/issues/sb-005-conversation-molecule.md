---
id: SB-005
title: Conversation molecule + agent assembly + API facade
status: draft
epic: EP-001
depends_on: [SB-002, SB-003]
branch:
pr:
stack:
stack_index:
created: 2026-03-14
---

# Conversation Molecule + Agent Assembly + API Facade

## Summary

The core molecule layer. Three components:

1. **ConversationEntity** (entity) — domain aggregate composing all 4 conversation feature services. Business logic: create conversation, send message, persist response with parts and tool calls.
2. **AgentAssembler** (agent) — hydrates DB agent definitions into runnable Agent instances. Composes RoleTemplate + AgentDefinition services.
3. **ConversationAPI** (API facade) — permission-aware response layer consumed by both REST routers and future CLI. Returns Pydantic response schemas. This is where permissions will live when we add auth.

Also adds custom service queries to SB-002/SB-003 features as the entity/assembler needs them.

## Scope

What's in:
- **ConversationEntity** (molecules/entities/)
  - create_conversation(agent_name, model) → Conversation
  - send(conversation_id, message) → SendResult
  - send_stream(conversation_id, message) → AsyncIterator[StreamEvent]
  - get_with_messages(conversation_id) → conversation + messages + parts
- **AgentAssembler** (molecules/agents/)
  - assemble(agent_name, model_override?) → Agent
  - list_available() → list[str]
- **ConversationAPI** (molecules/apis/) — facade consumed by REST + CLI
  - create(agent_name, model?) → ConversationResponse
  - send(conversation_id, message) → SendResponse
  - get(conversation_id) → ConversationDetailResponse
  - list() → list[ConversationResponse]
  - delete(conversation_id) → None
  - list_agents() → list[str]
  - get_agent(name) → AgentDetailResponse
- **Custom service queries** added to features as needed:
  - MessageService.get_by_conversation(conversation_id) — ordered by sequence
  - MessagePartService.get_by_message(message_id) — ordered by position
  - ToolCallService.get_by_conversation(conversation_id)
  - AgentDefinitionService.get_by_name(name), list_active() (if not already in SB-003)
- Molecule exceptions (ConversationNotFoundError, AgentNotFoundError)
- Unit tests with mocked runners

What's out:
- PersistenceExporter wiring (SB-007)
- REST/CLI organisms (SB-006) — they consume the API facade
- DevelopWorkflow and execution molecules (deferred)
- Auth/permission logic in facade (single user MVP — add later)

## Implementation

```
molecules/
├── __init__.py
├── exceptions.py               # ConversationNotFoundError, AgentNotFoundError, etc.
├── entities/
│   ├── __init__.py
│   └── conversation_entity.py  # Domain aggregate — business logic
├── agents/
│   ├── __init__.py
│   └── assembler.py            # DB → hydrate atoms → build Agent
└── apis/
    ├── __init__.py
    └── conversation_api.py     # API facade — returns response schemas
```

### Layer responsibilities

```
Feature Services (CRUD)
    ↓ composed by
ConversationEntity (business logic, domain aggregate)
    ↓ consumed by
ConversationAPI (facade — permissions, response schemas)
    ↓ consumed by
REST routers + CLI (organisms — thin, DI only)
```

### ConversationAPI Facade

```python
class ConversationAPI:
    """API facade for conversation domain. Both REST and CLI consume this.
    Permissions will be added here when auth is implemented."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.entity = ConversationEntity(db)
        self.assembler = AgentAssembler(db)

    async def create(self, agent_name: str, model: str | None = None) -> ConversationResponse:
        conv = await self.entity.create_conversation(agent_name, model)
        await self.db.commit()
        return ConversationResponse.model_validate(conv)

    async def send(self, conversation_id: UUID, message: str) -> SendResponse:
        result = await self.entity.send(conversation_id, message)
        await self.db.commit()
        return SendResponse(...)  # Transform to response schema

    async def list_agents(self) -> list[str]:
        return await self.assembler.list_available()
```

## Verification

- [ ] ConversationEntity.create_conversation() persists conversation record
- [ ] ConversationEntity.send() creates request + response messages with parts
- [ ] Tool calls tracked with state transitions (pending → executed)
- [ ] AgentAssembler.assemble("understander") returns configured Agent
- [ ] ConversationAPI.create() returns ConversationResponse schema (not ORM object)
- [ ] ConversationAPI.send() commits and returns SendResponse schema
- [ ] ConversationAPI.list_agents() returns seeded agent names
- [ ] Tests pass with mocked runners

## Notes

Source: Adapted from `agentic_patterns/app/api/conversation_service.py` (241 LOC) + `features/agents/assembler.py`.

The API facade pattern is critical — it's the single interface that both REST routers and CLI commands consume. When we add auth, permissions checks go in the facade (not in routers or entities). For single-user MVP the facade is thin, but the layer exists for the right reasons.
