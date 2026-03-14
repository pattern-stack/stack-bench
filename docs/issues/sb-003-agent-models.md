---
id: SB-003
title: Agent domain features
status: draft
epic: EP-001
depends_on: [SB-001]
branch:
pr:
stack:
stack_index:
created: 2026-03-14
parallel_with: [SB-002, SB-004]
---

# Agent Domain Features

## Summary

Two pattern-stack features for agent configuration: RoleTemplate and AgentDefinition. Adapted from agentic_patterns/app/features/{roles,agents}/ with proper Field() system.

**Parallel:** This can be developed in a worktree alongside SB-002 and SB-004 after SB-001 merges.

## Scope

What's in:
- RoleTemplate(BasePattern) — name, source, archetype, default_model, persona (JSON), judgments, responsibilities
- AgentDefinition(BasePattern) — name, role_template_id (FK), model_override, mission, background, awareness, is_active
- Minimal services: inherit BaseService, custom queries (get_by_name, list_active) since they're simple and needed for seed verification
- Pydantic schemas
- Alembic migration for 2 tables
- Seed data file with 5 SDLC roles + definitions
- Unit tests

What's out:
- AgentAssembler (SB-005 — molecule layer, composes role + definition into runnable Agent)
- REST endpoints (SB-006)
- API facade (SB-005)

## Implementation

```
features/
├── role_templates/
│   ├── __init__.py
│   ├── models.py           # RoleTemplate(BasePattern)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── input.py
│   │   └── output.py
│   └── service.py          # RoleTemplateService + get_by_name()
└── agent_definitions/
    ├── __init__.py
    ├── models.py           # AgentDefinition(BasePattern)
    ├── schemas/
    │   ├── __init__.py
    │   ├── input.py
    │   └── output.py
    └── service.py          # AgentDefinitionService + get_by_name(), list_active()

seeds/
└── agents.yaml             # 5 SDLC role templates + agent definitions
```

## Verification

- [ ] Migration creates 2 tables
- [ ] RoleTemplateService.get_by_name("understander") works
- [ ] AgentDefinitionService.list_active() returns only is_active=True
- [ ] Seed data loads 5 roles + 5 definitions
- [ ] Tests pass

## Notes

Source: `agentic_patterns/app/features/{agents,roles}/`
get_by_name() and list_active() are included because they're trivial and needed to verify seed data.
