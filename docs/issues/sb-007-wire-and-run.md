---
id: SB-007
title: Integration wiring + seed + run
status: draft
epic: EP-001
depends_on: [SB-006]
branch:
pr:
stack:
stack_index:
created: 2026-03-14
---

# Integration Wiring + Seed + Run

## Summary

The "it works" issue. Wire up the full lifespan (DB init, EventBus, PersistenceExporter), seed the database with SDLC agents, and verify end-to-end: start backend → create conversation → send message → get Claude response → see it persisted in Postgres.

## Scope

What's in:
- App lifespan: DB engine init, EventBus singleton, PersistenceExporter registration
- Seed command: `make seed` loads 5 SDLC role templates + agent definitions
- Updated docker-compose: Postgres + optional Jaeger
- End-to-end test: create conversation → send → verify persistence

What's out:
- Go CLI (separate epic)
- React workbench (separate epic)
- DevelopWorkflow / job execution pipeline (separate epic)
- Worker process (separate epic)

## Implementation

```
organisms/
└── api/
    └── app.py              # Full lifespan: DB init, EventBus, PersistenceExporter

seeds/
├── __init__.py
└── agents.py               # Load SDLC roles + definitions from YAML or inline

docker-compose.yml          # Updated with Jaeger (optional)
Makefile                    # Add seed target
```

### Lifespan Wiring

```python
async def lifespan(app):
    # Startup
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine)
    event_bus = AgentEventBus()
    # Register PersistenceExporter on event bus
    # Store in app.state
    yield
    # Shutdown
    await engine.dispose()
```

## Verification

- [ ] `docker compose up -d && make migrate && make seed && make dev` → running backend
- [ ] `curl -X POST /api/v1/conversations/ -d '{"agent_name":"understander"}'` → 201
- [ ] `curl -X POST /api/v1/conversations/{id}/send -d '{"message":"hello"}'` → Claude response
- [ ] Conversation + messages visible in Postgres (psql or pgAdmin)
- [ ] `make test` passes (including e2e test)

## Notes

This is MVP. After this, a user can interact with agents through the REST API. CLI and UI come next as separate epics.
