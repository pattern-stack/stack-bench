# Python Language Primitive

Instructions for Python-specific workflows in a pattern-stack project.

## File Patterns

- Source: `**/*.py`
- Tests: `**/test_*.py`, `**/*_test.py`
- Config: `pyproject.toml`, `patterns.yaml`, `alembic.ini`

## Toolchain

| Tool | Command | Purpose |
|------|---------|---------|
| Runtime | `python 3.12` via `mise` | Python version management |
| Packages | `uv` | Dependency management (fast pip replacement) |
| Format | `ruff format` | Code formatting |
| Lint | `ruff check` | Linting |
| Typecheck | `mypy` | Type checking |
| Test | `pytest` | Test runner |
| Quality Gate | `make ci` | Format + lint + typecheck + test (80%+ coverage) |

## Conventions

- Use type hints for all function signatures and return types
- Prefer `pathlib.Path` over `os.path`
- Use Pydantic `BaseModel` for schemas (input/output)
- Follow PEP 8 naming conventions
- Always use `async def` — the framework is async-first
- Use `Field()` for SQLAlchemy model fields, never raw `mapped_column()`

## Pattern-Stack Specifics

### Field() System

```python
# Always use Field(), never mapped_column()
class MyModel(EventPattern):
    __tablename__ = "my_models"
    name = Field(String, max_length=255)
    status = Field(String, max_length=50, default="draft")
    description = Field(Text, nullable=True)
```

### Pattern Types

| Pattern | Use For |
|---------|---------|
| `BasePattern` | Simple data with CRUD, no state machine |
| `EventPattern` | Entities with state machines (status transitions) |
| `ActorPattern` | Active entities that perform actions |
| `CatalogPattern` | Reference/lookup data (tags, categories) |
| `RelationalPattern` | Join/relationship models |

### Service Inheritance

```python
# Inherit, don't reimplement
class MyService(BaseService[MyModel, MyCreate, MyUpdate]):
    model = MyModel
    # Only add custom methods — CRUD is inherited
```

### Atomic Architecture Layers

```
atoms/        # Framework primitives (pattern-stack provides these)
features/     # Single-model data services (models + schemas + service)
molecules/    # Multi-feature business logic (entities, workflows, api facades)
organisms/    # Thin interface layer (API routers, CLI commands)
```

Import rules:
- Features only import from atoms (framework)
- Molecules import from features + atoms
- Organisms import from molecules + features + atoms
- **Never** import upward (features cannot import molecules)
- **Never** cross-import features (compose via molecules)

## Strategy Considerations

When planning Python implementations:
- Check for existing patterns (models, services, schemas)
- Identify virtual environment and dependency management approach (`uv`)
- Note Python version constraints from `pyproject.toml`
- Check `patterns.yaml` for project configuration
- Follow pattern-stack conventions for model definitions
- Use `make ci` as the quality gate before committing
