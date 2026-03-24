---
title: Add local_path and github_repo fields to Project model
number: SB-052
status: draft
epic: EP-005
depends_on: [SB-027, SB-028]
stack: dugshub/sb-052
stack_index: 1
---

# SB-052: Add local_path and github_repo fields to Project model

## Goal

Extend the Project model with `local_path` (directory where local .git lives) and `github_repo` (GitHub repo URL) fields. This enables the backend to serve files, diffs, and tree structure from the local git state, supporting the file viewer and future agent sandbox architecture.

## Why

**local_path:**
- Backend needs to access the local filesystem to read .git repository data
- Enables serving file diffs, tree views, and content from git state
- Supports the file viewer component which needs backend file serving

**github_repo:**
- Links the project to its GitHub repository for PR creation/updates
- Provides context for the three-tier architecture: local git → stack-bench workspace → GitHub
- Enables GitHub API operations (create PR, check status, etc.)

## Design Decisions

1. **Both fields required (MVP)** - We only support local repositories initially. Can become nullable later for cloud deployments.

2. **Validate local_path exists** - Directory must exist on filesystem at creation/update time. Prevents orphaned projects pointing to non-existent directories.

3. **github_repo format: `https://github.com/user/repo`** - Full HTTPS URL matching Workspace.repo_url convention. Simpler to work with directly in code and API calls.

4. **Index github_repo** - Recommended for frequent lookups (finding project by repo URL), common in GitHub integration workflows.

5. **Create proper Alembic migration** - Add columns to existing projects table with constraints and indexes.

## Implementation Breakdown

### Step 1: Update Project Model
**File:** `app/backend/src/features/projects/models.py`

Add two new fields to the Project model:
```python
local_path = Field(str, required=True, max_length=500)
github_repo = Field(str, required=True, max_length=500, index=True)
```

**Constraints:**
- Both strings with max_length=500 (matching Workspace conventions)
- Both required (MVP: no remote deployments)
- github_repo indexed for repo lookups

**Acceptance Criteria:**
- Fields defined with correct types and constraints
- Model still passes existing pattern-stack validations
- `__tablename__ = "projects"` unchanged

---

### Step 2: Update Input Schemas
**File:** `app/backend/src/features/projects/schemas/input.py`

Add fields to `ProjectCreate` and `ProjectUpdate`:

**ProjectCreate:**
```python
local_path: str = PydanticField(..., min_length=1, max_length=500)
github_repo: str = PydanticField(..., min_length=1, max_length=500)
```

**ProjectUpdate:**
```python
local_path: str | None = PydanticField(None, min_length=1, max_length=500)
github_repo: str | None = PydanticField(None, min_length=1, max_length=500)
```

**Validation:**
- Add custom validator `@field_validator("local_path")` to check directory exists
- Use `pathlib.Path(local_path).is_dir()` to validate
- Raise `ValueError` with descriptive message if directory doesn't exist
- github_repo validation: basic URL format check (must contain github.com and user/repo pattern)

**Acceptance Criteria:**
- ProjectCreate requires both fields (... notation)
- ProjectUpdate allows partial updates (None defaults)
- Validators execute and reject invalid paths
- Error messages are clear

---

### Step 3: Update Output Schema
**File:** `app/backend/src/features/projects/schemas/output.py`

Add fields to `ProjectResponse`:
```python
local_path: str
github_repo: str
```

**Acceptance Criteria:**
- Fields present in response model
- `from_attributes=True` still applies (SQLAlchemy integration)
- Type hints match model definitions

---

### Step 4: Create Alembic Migration
**File:** `app/backend/alembic/versions/<timestamp>_add_project_local_and_github.py`

Generate via: `cd app/backend && just migrate-gen "add project local_path and github_repo"`

The migration must:

**Upgrade:**
```sql
ALTER TABLE projects
ADD COLUMN local_path VARCHAR(500) NOT NULL;

ALTER TABLE projects
ADD COLUMN github_repo VARCHAR(500) NOT NULL;

CREATE INDEX ix_projects_github_repo ON projects(github_repo);
```

**Downgrade:**
```sql
DROP INDEX ix_projects_github_repo;
ALTER TABLE projects DROP COLUMN github_repo;
ALTER TABLE projects DROP COLUMN local_path;
```

**Constraints:**
- NOT NULL constraints required (MVP)
- Index on github_repo (for repo lookups)
- Safe downgrade path

**Acceptance Criteria:**
- Migration file created and named correctly
- Alembic revision head updated
- Upgrade and downgrade SQL correct
- `just migrate` runs without errors
- Rollback via `just migrate-rollback` works

---

### Step 5: Update Tests
**File:** `app/backend/__tests__/features/test_projects.py`

Add new test cases (all `@pytest.mark.unit`):

1. **test_project_model_has_local_path_field** — Verify `hasattr(Project, "local_path")`
2. **test_project_model_has_github_repo_field** — Verify `hasattr(Project, "github_repo")`
3. **test_project_create_requires_local_path** — `ProjectCreate(name="x", github_repo="...")` raises ValidationError
4. **test_project_create_requires_github_repo** — `ProjectCreate(name="x", local_path="/path")` raises ValidationError
5. **test_project_create_validates_local_path_exists** — Invalid path `/nonexistent/path` raises ValidationError with "directory does not exist" message
6. **test_project_create_validates_local_path_is_directory** — Path to a file (not dir) raises ValidationError
7. **test_project_create_validates_github_repo_format** — Invalid URLs like "invalid", "http://gitlab.com/x" raise ValidationError
8. **test_project_create_with_valid_paths** — `ProjectCreate(name="x", local_path="/tmp", github_repo="https://github.com/user/repo")` succeeds
9. **test_project_update_allows_partial_local_path** — `ProjectUpdate(local_path="/new/path")` succeeds
10. **test_project_update_allows_partial_github_repo** — `ProjectUpdate(github_repo="https://github.com/org/newrepo")` succeeds
11. **test_project_create_rejects_empty_local_path** — `ProjectCreate(name="x", local_path="", github_repo="...")` raises ValidationError
12. **test_project_create_rejects_empty_github_repo** — `ProjectCreate(name="x", local_path="/tmp", github_repo="")` raises ValidationError

**Test Fixture:**
Create a temp directory fixture for valid path validation:
```python
import tempfile
import pytest

@pytest.fixture
def temp_git_dir():
    """Create a temporary directory for testing local_path validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
```

**Acceptance Criteria:**
- All 12 tests pass
- Validators catch invalid inputs
- Valid inputs accepted
- Error messages are descriptive
- Fixture cleanup works

---

### Step 6: Verify pts sync Type Generation
**Command:** `cd app && pts sync generate`

Verify that `app/frontend/src/generated/` contains updated types:

**Expected Changes:**
- `ProjectResponse` schema includes `local_path: string` and `github_repo: string`
- Zod schema includes validators for new fields
- TanStack Query hooks use updated types
- TypeScript compilation succeeds with no new errors

**Acceptance Criteria:**
- pts sync completes without errors
- Frontend types updated correctly
- No TypeScript compilation errors in frontend
- IDE autocomplete includes new fields in ProjectResponse

---

## Integration Notes

- **No API changes needed** - Router already exposes ProjectCreate/ProjectUpdate via POST/PATCH
- **No service changes needed** - ProjectService.create/update already uses schemas
- **No router changes needed** - Existing /api/v1/projects endpoints automatically support new fields
- **Backward compatibility** - Existing projects in DB will have NULL for new columns initially (migration doesn't set defaults). A data migration may be needed later to populate real values.

---

## Acceptance Criteria (Overall)

- [ ] Project model has `local_path` and `github_repo` fields
- [ ] Input schemas (ProjectCreate/ProjectUpdate) include validation
- [ ] Output schema (ProjectResponse) includes new fields
- [ ] local_path validation checks directory exists
- [ ] github_repo validation checks URL format
- [ ] Alembic migration creates columns with constraints
- [ ] All 12 new tests pass
- [ ] pts sync generates updated types with no errors
- [ ] Frontend can access new fields via TypeScript types
- [ ] Existing tests still pass

---

## Files Modified/Created

### New Files
- `app/backend/alembic/versions/<timestamp>_add_project_local_and_github.py`

### Modified Files
- `app/backend/src/features/projects/models.py`
- `app/backend/src/features/projects/schemas/input.py`
- `app/backend/src/features/projects/schemas/output.py`
- `app/backend/__tests__/features/test_projects.py`

### Generated Files (via pts sync)
- `app/frontend/src/generated/` (types, schemas, hooks)

---

## Testing Strategy

All tests are `@pytest.mark.unit` — no database required.

- **Model tests** — Field existence, type assertions
- **Schema tests** — Pydantic validation, error messages
- **Validator tests** — Directory existence, URL format
- **Integration test** — Full ProjectCreate with valid inputs

Run: `cd app/backend && just test`

---

## Related Issues

- **SB-027** — Original Project domain spec (already implemented)
- **SB-028** — Workspace domain (already has local_path)
- **SB-039** — Diff review panel (uses file viewer, which will use these fields)
- **Future** — Agent sandbox architecture (will use local_path for file access)

---

## Open Questions Resolved

1. ✅ **local_path required** — Yes, MVP local-only
2. ✅ **Validate directory exists** — Yes, in ProjectCreate validator
3. ✅ **github_repo indexing** — Yes, index=True for repo lookups
4. ✅ **Format** — Full HTTPS URL: `https://github.com/user/repo`
5. ✅ **Migration** — Create proper Alembic migration with constraints

---

## Next Steps (for builder)

1. Implement Step 1-3 (model + schemas)
2. Run Step 4 (migration generation)
3. Implement Step 5 (tests)
4. Run Step 6 (pts sync)
5. Verify all acceptance criteria
