---
title: Git Synced Entities
date: 2026-03-22
status: draft
branch:
depends_on: []
adrs: []
---

# Git Synced Entities

## Goal

Model file diffs, file trees, and file content as read-through views served via the GitHub REST API, replacing the hardcoded mock data in the frontend. This follows the same protocol/adapter pattern used for stack operations: define canonical protocol DTOs and a `GitHubAdapter` in `molecules/providers/`, and expose the data through API endpoints that the frontend hooks already expect.

## Architecture Decision

### What NOT to persist

Diffs, file trees, and file content are **derived data** -- they are computed from git objects that already have a permanent, content-addressed store (GitHub's git database). Persisting them in Postgres would create a stale-data problem with no benefit. These are fundamentally different from tasks or pull requests, which are mutable state that must be tracked.

### The right pattern: Protocol DTOs + GitHubAdapter + Cache

Instead of Feature-layer database models, we use:

1. **Protocol DTOs + Protocol** (Pydantic models and Protocol class in `molecules/providers/github_adapter.py`) -- define the canonical shapes for diff, file tree, and file content data alongside the adapter, following the `stack_provider.py` precedent where DTOs (`StackResult`, `BranchInfo`, `StackInfo`) and the `StackProvider` protocol live in the same file.

2. **GitHubAdapter** (in `molecules/providers/github_adapter.py`) -- implements the protocol by calling GitHub REST API endpoints via `httpx`. Lives alongside `StackProvider` and `StackCLIAdapter`.

3. **Cache layer** -- TTL-based caching keyed on `(owner/repo, commit_sha, ...)`. Since git SHAs are content-addressed, cached data for a given SHA never goes stale. Cache invalidation happens naturally via TTL expiry. **Note:** The pattern-stack cache subsystem is available but not yet configured in this project. Phase 1 should verify/configure it (Redis or in-memory) before using it. If setup is nontrivial, start with a simple `dict`-based TTL cache in the adapter and migrate to the subsystem later.

4. **API endpoints** -- thin routes on the stacks router that resolve branch -> workspace -> `repo_url` -> GitHub API calls.

### Why not Feature-layer models?

The Feature layer is for **single-model database entities**. Diffs and file trees fail the test:

- They have no independent lifecycle (no create/update/delete)
- They have no state transitions
- They are fully derivable from existing data (git SHAs + repo URL)
- Storing them would require a sync mechanism to keep them fresh, solving a problem that does not exist (GitHub already stores them)

The Branch model already has `head_sha`. The Workspace model already has `repo_url`. The data we need is a **read-through view** of git state, not a synced entity.

### Why GitHub REST API instead of local git CLI?

The previous version of this spec proposed shelling out to the local git CLI via `asyncio.create_subprocess_exec`. The GitHub REST API approach is better because:

- **No `local_path` dependency**: The Workspace model has `repo_url` (e.g., `https://github.com/pattern-stack/stack-bench`), which is always populated. The `local_path` field is nullable and requires the repo to be cloned locally. Using GitHub API removes this requirement entirely, making SB-052 unnecessary for this feature.
- **No subprocess management**: No need to manage async subprocesses, handle git binary availability, or scope `cwd` per repo.
- **Works in any deployment**: Not tied to the server having the repo cloned locally.
- **Simpler parsing**: GitHub API returns structured JSON. No unified diff parsing needed for file lists and stats.

The tradeoff is API rate limits (5,000/hour authenticated) and needing a `GITHUB_TOKEN`. For a single-user developer workbench, rate limits are not a concern.

### What about the "synced entity" framing?

The synced entity pattern (IntegrationMixin + SyncRecord + IntegrationAdapter) is designed for **bidirectional sync** between our database and an external system. Git data is **read-only** from our perspective -- we never push diffs back to git. The right abstraction is a **read adapter** with caching, not a sync loop.

## Domain Model

```
Workspace (existing)          Branch (existing)
  - repo_url ────────┐         - head_sha ──────┐
                     │         - stack_id        │
                     │                           │
                     ▼                           ▼
              GitHubAdapter (new)
              derives owner/repo from repo_url, then calls:
              - GET /repos/{o}/{r}/compare/{base}...{head}  -> DiffData
              - GET /repos/{o}/{r}/git/trees/{sha}?recursive=1 -> FileTreeNode
              - GET /repos/{o}/{r}/contents/{path}?ref={sha}   -> FileContent
                     │
                     ▼
              Cache (pattern-stack subsystem or dict fallback)
              key: (owner/repo, sha, operation, path?)
              TTL: long (SHA-addressed = immutable)
                     │
                     ▼
              API endpoints (new)
              GET /stacks/{id}/branches/{id}/diff
              GET /stacks/{id}/branches/{id}/tree
              GET /stacks/{id}/branches/{id}/files/{path}
```

### Protocol DTOs

These are **not** database models. They are Pydantic schemas defining the canonical data shapes, mirroring the TypeScript types the frontend already uses.

| DTO | Purpose | Source |
|-----|---------|--------|
| `DiffLine` | Single line in a diff | GitHub compare API patch parsing |
| `DiffHunk` | Group of contiguous changes | GitHub compare API patch parsing |
| `DiffFile` | One file's diff with hunks | GitHub compare API `files[]` |
| `DiffData` | Complete diff between two refs | GitHub compare API response |
| `FileTreeNode` | Recursive directory tree | GitHub git trees API |
| `FileContent` | File content at a commit | GitHub contents API |

### GitHubAdapter Protocol

```python
class GitRepoProtocol(Protocol):
    """Read-only access to git repository data via GitHub API."""

    async def get_diff(
        self, owner: str, repo: str, base_ref: str, head_ref: str
    ) -> DiffData: ...

    async def get_file_tree(
        self, owner: str, repo: str, ref: str
    ) -> FileTreeNode: ...

    async def get_file_content(
        self, owner: str, repo: str, ref: str, path: str
    ) -> FileContent: ...
```

### GitHub API Endpoints Used

| Operation | GitHub API Endpoint | Notes |
|-----------|-------------------|-------|
| Diff between refs | `GET /repos/{owner}/{repo}/compare/{base}...{head}` | Returns file list with patches, stats |
| File tree at ref | `GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1` | Returns flat list, we build tree |
| File content at ref | `GET /repos/{owner}/{repo}/contents/{path}?ref={sha}` | Returns base64-encoded content |
| PR status (future) | `GET /repos/{owner}/{repo}/pulls/{number}` | Not needed for Phase 1 |

### Authentication

GitHub API requires a personal access token for authenticated requests (5,000 req/hour vs 60 unauthenticated). Configuration:

- Add `GITHUB_TOKEN: str = Field(default="")` to `AppSettings` in `config/settings.py`
- The adapter reads the token from settings and passes it as `Authorization: Bearer {token}` header
- If no token is configured, requests go unauthenticated (60 req/hour -- acceptable for dev but not recommended)

## File Tree

```
app/backend/src/
  config/
    settings.py                       # MODIFY -- add GITHUB_TOKEN field

  molecules/
    providers/
      github_adapter.py               # NEW -- DTOs + Protocol + GitHubAdapter
      stack_provider.py                # EXISTING (unchanged, pattern reference)
      stack_cli_adapter.py             # EXISTING (unchanged)

    entities/
      stack_entity.py                  # MODIFY -- add get_branch_repo_context method
                                      #   (needs WorkspaceService import)

    apis/
      stack_api.py                    # MODIFY -- add diff/tree/content methods,
                                      #   accept GitHubAdapter via constructor

  organisms/
    api/
      dependencies.py                 # MODIFY -- wire GitHubAdapter into StackAPI
      routers/
        stacks.py                     # MODIFY -- add 3 new endpoints

app/frontend/src/
  hooks/
    useBranchDiff.ts                  # MODIFY -- add stackId param, replace mock with fetch
    useFileTree.ts                    # MODIFY -- add stackId param, replace mock with fetch
    useFileContent.ts                 # MODIFY -- add stackId param, replace mock with fetch
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | DTOs + Protocol + GitHubAdapter | -- |
| 2 | StackEntity + StackAPI integration | Phase 1 |
| 3 | API endpoints + dependency wiring | Phase 2 |
| 4 | Frontend hook wiring | Phase 3 |

## Phase Details

### Phase 1: DTOs + Protocol + GitHubAdapter

**`app/backend/src/config/settings.py`**

Add the GitHub token field:

```python
GITHUB_TOKEN: str = Field(default="")
```

**`app/backend/src/molecules/providers/github_adapter.py`**

This file contains everything: DTOs, protocol, and adapter implementation. This follows the `stack_provider.py` pattern where `StackResult`, `BranchInfo`, `StackInfo` dataclasses and the `StackProvider` protocol all live in one file.

DTOs (Pydantic models matching the frontend TypeScript types exactly):

```python
from pydantic import BaseModel

class DiffLine(BaseModel):
    type: str  # "context" | "add" | "del" | "hunk"
    old_num: int | None = None
    new_num: int | None = None
    content: str

class DiffHunk(BaseModel):
    header: str
    lines: list[DiffLine]

class DiffFile(BaseModel):
    path: str
    change_type: str  # "added" | "modified" | "deleted" | "renamed"
    additions: int
    deletions: int
    hunks: list[DiffHunk]

class DiffData(BaseModel):
    files: list[DiffFile]
    total_additions: int
    total_deletions: int

class FileTreeNode(BaseModel):
    name: str
    path: str
    type: str  # "file" | "dir"
    children: list["FileTreeNode"] | None = None
    size: int | None = None

class FileContent(BaseModel):
    path: str
    content: str
    size: int
    language: str | None = None
    lines: int
    truncated: bool = False
```

Protocol:

```python
from typing import Protocol

class GitRepoProtocol(Protocol):
    async def get_diff(self, owner: str, repo: str, base_ref: str, head_ref: str) -> DiffData: ...
    async def get_file_tree(self, owner: str, repo: str, ref: str) -> FileTreeNode: ...
    async def get_file_content(self, owner: str, repo: str, ref: str, path: str) -> FileContent: ...
```

GitHubAdapter implementation:

```python
import httpx

class GitHubAdapter:
    """Implements GitRepoProtocol using GitHub REST API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str = "") -> None:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, headers=headers)
```

Key implementation details:

- **`get_diff`**: Calls `GET /repos/{owner}/{repo}/compare/{base}...{head}`. The response `files` array contains `filename`, `status` (added/modified/removed/renamed), `additions`, `deletions`, and `patch` (unified diff string). Parse the `patch` field into `DiffHunk`/`DiffLine` objects. Map GitHub's `status` values to our `change_type` enum (`"removed"` -> `"deleted"`).

- **`get_file_tree`**: Calls `GET /repos/{owner}/{repo}/git/trees/{ref}?recursive=1`. Returns a flat `tree` array with `path`, `type` (`blob`/`tree`), and `size`. Build the recursive `FileTreeNode` structure by splitting paths on `/` and nesting. Map `blob` -> `"file"`, `tree` -> `"dir"`.

- **`get_file_content`**: Calls `GET /repos/{owner}/{repo}/contents/{path}?ref={ref}`. Returns base64-encoded `content`, `size`, and `encoding`. Decode the content, detect language from file extension, count lines. Truncate at 100KB with `truncated=True`.

- **`parse_owner_repo(repo_url: str) -> tuple[str, str]`**: Static/class method that extracts `(owner, repo)` from a URL like `https://github.com/pattern-stack/stack-bench`. Used by the entity layer to convert `workspace.repo_url` into API parameters.

- **Error handling**: Raise specific exceptions for 404 (ref/path not found), 403 (rate limited), and other HTTP errors. These propagate as 404/429/502 from the API layer.

Caching strategy:
```python
# Diffs: cache key = f"github:diff:{owner}/{repo}:{base_ref}:{head_ref}"
# Trees: cache key = f"github:tree:{owner}/{repo}:{ref}"
# Files: cache key = f"github:file:{owner}/{repo}:{ref}:{path}"
# TTL: 3600s (1 hour) -- SHA-addressed data is immutable, TTL is just memory management
#
# NOTE: Verify pattern-stack cache subsystem is configured (Redis URL in settings).
# If not yet set up, use a simple dict-based TTL cache as a fallback and migrate later.
```

### Phase 2: StackEntity + StackAPI Integration

**Modify `app/backend/src/molecules/entities/stack_entity.py`**

Add `WorkspaceService` import and a method to resolve a branch to its GitHub repo context:

```python
from features.workspaces.service import WorkspaceService

# In __init__:
self.workspace_service = WorkspaceService()
```

```python
async def get_branch_repo_context(self, branch_id: UUID) -> tuple[str, str, str, str]:
    """Resolve branch -> workspace -> repo_url, plus base/head refs.

    Returns (owner, repo, base_ref, head_ref) where:
    - owner: GitHub org/user (from workspace.repo_url)
    - repo: GitHub repo name (from workspace.repo_url)
    - base_ref: the parent branch name or trunk (for diff base)
    - head_ref: branch head_sha if available, otherwise branch name
    """
```

This method walks:
- Branch -> `workspace_id` -> Workspace -> `repo_url` -> parse `owner/repo`
- Branch -> `stack_id` -> Stack -> `trunk` for position-1 branches
- Branch -> `stack_id` -> previous Branch (position N-1) for the base ref
- Branch -> `head_sha` (preferred) or `name` (fallback when `head_sha` is null) for the head ref

**Modify `app/backend/src/molecules/apis/stack_api.py`**

Accept `GitHubAdapter` via constructor alongside the db session:

```python
class StackAPI:
    def __init__(self, db: AsyncSession, github: GitHubAdapter) -> None:
        self.db = db
        self.entity = StackEntity(db)
        self.github = github
```

Add three new methods:

```python
async def get_branch_diff(self, stack_id: UUID, branch_id: UUID) -> DiffData:
    """Get diff for a branch relative to its base."""
    owner, repo, base_ref, head_ref = await self.entity.get_branch_repo_context(branch_id)
    return await self.github.get_diff(owner, repo, base_ref, head_ref)

async def get_branch_tree(self, stack_id: UUID, branch_id: UUID) -> FileTreeNode:
    """Get file tree at branch head."""
    owner, repo, _, head_ref = await self.entity.get_branch_repo_context(branch_id)
    return await self.github.get_file_tree(owner, repo, head_ref)

async def get_branch_file(self, stack_id: UUID, branch_id: UUID, path: str) -> FileContent:
    """Get file content at branch head."""
    owner, repo, _, head_ref = await self.entity.get_branch_repo_context(branch_id)
    return await self.github.get_file_content(owner, repo, head_ref, path)
```

Each method delegates to `StackEntity` for context resolution and `GitHubAdapter` for the actual API call. The protocol DTOs are returned directly (Pydantic models serialize to JSON automatically).

### Phase 3: API Endpoints + Dependency Wiring

**Modify `app/backend/src/organisms/api/dependencies.py`**

Wire `GitHubAdapter` into `StackAPI`:

```python
from config.settings import get_settings
from molecules.providers.github_adapter import GitHubAdapter

def get_github_adapter() -> GitHubAdapter:
    settings = get_settings()
    return GitHubAdapter(token=settings.GITHUB_TOKEN)

GitHubAdapterDep = Annotated[GitHubAdapter, Depends(get_github_adapter)]

def get_stack_api(db: DatabaseSession, github: GitHubAdapterDep) -> StackAPI:
    return StackAPI(db, github)
```

**Modify `app/backend/src/organisms/api/routers/stacks.py`**

Add three endpoints nested under the branch. Import the response DTOs from the adapter module:

```python
from molecules.providers.github_adapter import DiffData, FileTreeNode, FileContent
```

```
GET /stacks/{stack_id}/branches/{branch_id}/diff
  -> DiffData JSON

GET /stacks/{stack_id}/branches/{branch_id}/tree
  -> FileTreeNode JSON

GET /stacks/{stack_id}/branches/{branch_id}/files/{path:path}
  -> FileContent JSON
```

The `{path:path}` syntax in FastAPI captures the full remaining path including slashes, so `files/app/backend/src/main.py` works correctly.

Example endpoint:

```python
@router.get(
    "/{stack_id}/branches/{branch_id}/diff",
    response_model=DiffData,
)
async def get_branch_diff(
    stack_id: UUID, branch_id: UUID, api: StackAPIDep
) -> DiffData:
    """Get diff for a branch relative to its parent in the stack."""
    return await api.get_branch_diff(stack_id, branch_id)
```

### Phase 4: Frontend Hook Wiring

All three hooks need a `stackId` parameter added. The current hooks only take `branchId`, but the API endpoints are nested under `/stacks/{stackId}/branches/{branchId}/...`. The frontend already has the stack context from the sidebar selection.

Replace mock data with real API calls in all three hooks:

**`useBranchDiff.ts`**:
```typescript
export function useBranchDiff(stackId: string | undefined, branchId: string | undefined): UseBranchDiffResult {
  // fetch from GET /api/stacks/{stackId}/branches/{branchId}/diff
}
```

**`useFileTree.ts`**:
```typescript
export function useFileTree(stackId: string | undefined, branchId?: string): UseFileTreeResult {
  // fetch from GET /api/stacks/{stackId}/branches/{branchId}/tree
}
```

**`useFileContent.ts`**:
```typescript
export function useFileContent(stackId: string | undefined, branchId: string | undefined, path: string | null): UseFileContentResult {
  // fetch from GET /api/stacks/{stackId}/branches/{branchId}/files/{path}
}
```

Each hook follows the same pattern:
- Use `useEffect` + `fetch` (or whatever data fetching pattern the app uses)
- Return `{ data, loading, error }` (same interface as today)
- Skip fetch when `stackId` or `branchId` is undefined
- Cache responses client-side by branch ID + SHA (optional, server cache handles most of it)
- Callers must be updated to pass `stackId` in addition to `branchId`

## Key Design Decisions

### 1. DTOs and Protocol live in the adapter file, not a new `protocols/` directory

Following the `stack_provider.py` precedent: `StackResult`, `BranchInfo`, `StackInfo`, and `StackProvider` protocol all live in the same file. This keeps related types colocated and avoids creating a new top-level module. The DTOs are importable from `molecules.providers.github_adapter`.

### 2. GitHubAdapter lives in `molecules/providers/`

Alongside `StackCLIAdapter` and `StackProvider` which follow the same pattern: protocol + adapter for an external system. Stays in stack-bench for now at `app/backend/src/molecules/providers/github_adapter.py` -- it is reusable but we will extract to agentic-patterns later.

### 3. GitHub REST API instead of local git CLI

This removes the need for SB-052 entirely for this feature. The adapter only needs `repo_url` (always populated on Workspace) to derive `owner/repo`. No `local_path` dependency, no subprocess management, no git binary requirement. The Workspace model already stores `repo_url` (e.g., `https://github.com/pattern-stack/stack-bench`).

### 4. No new database migrations

This spec adds zero database tables. All data is read from GitHub API and cached in memory/Redis via the cache subsystem (or dict fallback).

### 5. Base ref resolution for diffs

For a branch at position N in a stack, the diff base is:
- Position 1: the stack's `trunk` (e.g., `"main"`)
- Position N>1: the branch name at position N-1

This matches how stacked PRs work: each branch's diff is relative to the branch below it in the stack.

### 6. Null `head_sha` fallback

When `branch.head_sha` is `None` (branch created but not yet pushed), the adapter falls back to using `branch.name` as the head ref. GitHub API accepts both SHAs and branch names as ref parameters. Using SHAs is preferred when available because they are immutable and cache-friendly.

### 7. Dependency injection via FastAPI Depends

The `GitHubAdapter` is constructed in `dependencies.py` using `get_settings().GITHUB_TOKEN` and injected into `StackAPI` via its constructor. This keeps the adapter stateless per-request and testable via constructor injection in tests.

### 8. Max file size for content endpoint

Cap at 100KB. Files larger than this return truncated content with `truncated: true`. GitHub's contents API itself has a 100MB limit but returns base64, so we decode and truncate. This prevents massive payloads for minified files or binaries.

### 9. Diff context lines

The GitHub compare API returns patches with 3 lines of context by default. We accept this as-is. No query param needed initially.

### 10. Binary files in diffs

Include in the file list with correct `change_type` but empty `hunks` array. The GitHub API sets `patch` to `undefined` for binary files, which naturally maps to an empty hunks list.

## Testing Strategy

### Unit tests for GitHubAdapter

- **Response parsing**: Feed known GitHub API response JSON into the adapter's parsing methods, assert correct DTO structures
- **Diff parsing**: Test `patch` string parsing into `DiffHunk`/`DiffLine` objects
- **Tree building**: Test flat `tree[]` array conversion into recursive `FileTreeNode`
- **Content decoding**: Test base64 decode, language detection, truncation logic
- **Owner/repo parsing**: Test `parse_owner_repo` with various URL formats (`https://github.com/org/repo`, `https://github.com/org/repo.git`, etc.)
- **Error handling**: Mock 404, 403, 422 responses and assert correct exception types

Use `httpx.MockTransport` or `respx` to mock GitHub API responses. No real HTTP calls in unit tests.

Marker: `@pytest.mark.unit` (no database, no network)

### Integration tests for API endpoints

- **Diff endpoint**: Create stack + branch + workspace in DB, mock GitHubAdapter, hit endpoint, assert shape matches `DiffData`
- **Tree endpoint**: Same setup, assert recursive tree structure
- **File endpoint**: Same setup, assert content + metadata
- **Missing branch**: Assert 404 for nonexistent branch
- **Null head_sha**: Assert fallback to branch name works

The GitHubAdapter should be injected via FastAPI dependency override in integration tests, using a mock that returns known data.

Marker: `@pytest.mark.integration` (needs database, no network)

### Frontend

- Verify hooks accept `stackId` + `branchId` parameters
- Verify hooks fetch from correct URLs
- Verify loading/error states render correctly
- Can be tested with MSW (Mock Service Worker) intercepting fetch calls

## Related Issues

- **SB-052** (Add local_path/github_repo to Project): **No longer a prerequisite** for this feature. The GitHubAdapter derives `owner/repo` from `workspace.repo_url`, which is already populated. SB-052 may still be useful for other features but is not blocked on or blocking this spec.
