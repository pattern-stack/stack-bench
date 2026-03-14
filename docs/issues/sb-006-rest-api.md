---
id: SB-006
title: REST API organisms
status: draft
epic: EP-001
depends_on: [SB-005]
branch:
pr:
stack:
stack_index:
created: 2026-03-14
---

# REST API Organisms

## Summary

FastAPI routers consuming the ConversationAPI facade from SB-005. **Maximally thin** — routers do DI, call facade methods, translate exceptions to HTTP status codes. No business logic. No direct service access.

The facade is the boundary. Routers are just HTTP bindings over it.

## Scope

What's in:
- Conversations router: create, list, get, send, delete → delegates to ConversationAPI facade
- Agents router: list available, get detail → delegates to ConversationAPI facade
- Dependencies: get_db, get_conversation_api (facade factory)
- Error translation map: molecule exceptions → HTTP status codes
- Updated app.py: register routers
- Integration tests with httpx AsyncClient

What's out:
- Job/webhook/execution routers (deferred — not MVP)
- Auth/permissions (single user, facade handles this later)
- Streaming endpoint (add after basic send works)
- CLI organisms (future — will also consume the facade)

## Implementation

```
organisms/
├── api/
│   ├── app.py              # Register routers
│   ├── dependencies.py     # get_db, get_conversation_api
│   └── routers/
│       ├── __init__.py
│       ├── conversations.py  # Thin: DI → facade call → return
│       └── agents.py         # Thin: DI → facade call → return
```

### Router Pattern

Routers are thin. Every handler follows the same shape:

```python
@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(data: CreateConversationRequest, api: ConversationAPIDep):
    return await api.create(data.agent_name, data.model)
```

No service calls, no entity calls, no business logic. Just facade.

### Dependencies

```python
# The facade is the DI boundary
def get_conversation_api(db: DatabaseSession) -> ConversationAPI:
    return ConversationAPI(db)

ConversationAPIDep = Annotated[ConversationAPI, Depends(get_conversation_api)]
```

### Endpoints

| Method | Path | Facade Method |
|--------|------|---------------|
| POST | /api/v1/conversations/ | api.create(agent_name, model?) |
| GET | /api/v1/conversations/ | api.list() |
| GET | /api/v1/conversations/{id} | api.get(id) |
| POST | /api/v1/conversations/{id}/send | api.send(id, message) |
| DELETE | /api/v1/conversations/{id} | api.delete(id) |
| GET | /api/v1/agents/ | api.list_agents() |
| GET | /api/v1/agents/{name} | api.get_agent(name) |

### Error Translation

```python
EXCEPTION_MAP = {
    ConversationNotFoundError: (404, "Conversation not found"),
    AgentNotFoundError: (404, "Agent not found"),
    InvalidStateTransitionError: (409, "Invalid state transition"),
}
```

## Verification

- [ ] POST /api/v1/conversations/ returns 201 with ConversationResponse
- [ ] POST /api/v1/conversations/{id}/send returns response with assistant message
- [ ] GET /api/v1/agents/ returns list of seeded agent names
- [ ] 404 on nonexistent conversation/agent
- [ ] 409 on invalid state transition
- [ ] Routers contain zero business logic (only DI + facade + error translation)
- [ ] Tests pass

## Notes

Source: Adapted from `agentic_patterns/app/orchestrator/routers/{conversations,agents}.py`.
When CLI is added (future), it will also consume ConversationAPI — same facade, different interface.
