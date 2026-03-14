# Framework: Pattern Stack

Pattern-stack is a Python framework for building backend services using atomic architecture with SQLAlchemy patterns, Pydantic schemas, and async-first conventions.

## Atomic Architecture v2.1

### Layer Hierarchy

```
atoms/        # Framework primitives (provided by pattern-stack)
features/     # Single-model data services
molecules/    # Multi-feature business logic
organisms/    # Thin interface layer (API, CLI)
```

### Import Rules (Strict)

| Layer | Can Import From | Cannot Import From |
|-------|-----------------|-------------------|
| atoms | (stdlib, third-party) | features, molecules, organisms |
| features | atoms | other features, molecules, organisms |
| molecules | features, atoms | other molecules (peer), organisms |
| organisms | molecules, features, atoms | — |

**Critical:** Never import upward. Never cross-import features. Compose via molecules.

## Pattern Types

| Pattern | Use For | Has State Machine | Example |
|---------|---------|-------------------|---------|
| `BasePattern` | Simple CRUD data | No | Message, StackBranch |
| `EventPattern` | Stateful entities | Yes | Task, Job, Review |
| `ActorPattern` | Active performers | Yes | Agent, Worker |
| `CatalogPattern` | Reference/lookup data | No | Project (lightweight) |
| `RelationalPattern` | Join/relationship models | No | TaskRelation |

### Pattern Definition

```python
class MyModel(EventPattern):
    __tablename__ = "my_models"

    class Pattern:
        entity = "my_model"
        states = ["draft", "active", "completed"]
        initial_state = "draft"
        transitions = {
            "draft": ["active"],
            "active": ["completed"],
        }

    # Fields — always use Field(), never raw mapped_column()
    name = Field(String, max_length=255)
    status = Field(String, max_length=50, default="draft")
    description = Field(Text, nullable=True)
    config = Field(JSON, default=dict)
```

## Field() System

**Always** use `Field()` for model fields. Never use raw `mapped_column()`.

```python
# Correct
name = Field(String, max_length=255)
count = Field(Integer, default=0)
data = Field(JSON, nullable=True)
parent_id = Field(ForeignKey("parents.id"), nullable=True)

# Wrong - never do this
name = mapped_column(String(255))
```

## Project Structure

### Feature (Single Model)

```
features/{name}/
├── __init__.py
├── models.py          # SQLAlchemy model (one pattern per feature)
├── schemas/
│   ├── __init__.py
│   ├── input.py       # Pydantic create/update schemas
│   └── output.py      # Pydantic response schemas
├── service.py         # BaseService subclass
└── tests/
    ├── test_models.py
    └── test_service.py
```

### Molecule (Multi-Feature Logic)

```
molecules/{name}/
├── entities/          # Domain aggregates (compose multiple services)
├── workflows/         # Multi-step processes
└── apis/              # Permission facades (consumed by organisms)
```

### Organism (Interface Layer)

```
organisms/
├── api/
│   ├── app.py         # FastAPI create_app() factory
│   └── routers/       # Thin HTTP handlers
└── cli/               # Thin CLI commands
```

## Service Inheritance

```python
# Inherit from BaseService — CRUD is provided for free
class TaskService(BaseService[Task, TaskCreate, TaskUpdate]):
    model = Task
    # Only add custom business methods

# For state machines, use EventService
class ReviewService(EventService[Review, ReviewCreate, ReviewUpdate]):
    model = Review
    # Transitions are validated automatically
```

**Never** reimplement BaseService CRUD methods (create, get, update, delete, list).

## Key Rules

1. **Commit in organisms/facades, not entities** — database commits happen at the API/facade boundary, not deep in business logic
2. **Async-first** — all service methods are `async def`, all DB operations use `await`
3. **No Celery** — use the built-in Jobs subsystem for background work
4. **Schemas are Pydantic** — `input.py` for create/update, `output.py` for responses
5. **Thin organisms** — routers/CLI delegate immediately to molecules/features, no business logic
6. **Factories for subsystems** — `get_X()`, `configure_X()`, `reset_X()` pattern

## Quality Gates

```bash
make ci          # All gates in one command
# Equivalent to:
make format      # ruff format
make lint        # ruff check
make typecheck   # mypy
make test        # pytest --cov (80%+ coverage)
```

## Reference

Pattern-stack skill docs with detailed guidance for each layer:
- `.claude/skills/pattern-stack/SKILL.md` — overview
- `.claude/skills/pattern-stack/patterns-and-fields.md` — model patterns
- `.claude/skills/pattern-stack/building-features.md` — feature layer
- `.claude/skills/pattern-stack/building-molecules.md` — molecule layer
- `.claude/skills/pattern-stack/building-organisms.md` — organism layer
- `.claude/skills/pattern-stack/testing-patterns.md` — test conventions
- `.claude/skills/pattern-stack/infrastructure-subsystems.md` — jobs, cache, events
