---
title: LocalGitAdapter — Read Diffs, Trees, and Files from Local Git Clones
status: in-progress
created: 2026-04-09
depends_on: []
---

# LocalGitAdapter

## Goal

Build a `LocalGitAdapter` that implements `GitRepoProtocol` by running `git` commands against a local clone on disk, so stack-bench can serve diffs, file trees, and file content for workspaces that have a `local_path` without needing a GitHub token or API access. This enables reviewing stacks for work repos where the GitHub App is not installed.

## Context

### What exists

- `GitRepoProtocol` (4 read-only methods) — `molecules/providers/github_adapter.py:65-74`
- `GitHubAdapter` implements the protocol via GitHub REST API — same file, line 310+
- Data models (`DiffData`, `DiffFile`, `DiffHunk`, `DiffLine`, `FileTreeNode`, `FileContent`) — same file, lines 17-56
- `_parse_patch()` — unified-diff parser already works with raw git output (same file, line 166)
- `_build_file_tree()` — builds recursive tree from flat entries (same file, line 202)
- `_detect_language()` — extension-based language detection (same file, line 142)
- `Workspace.local_path` field — `features/workspaces/models.py:38`
- `StackAPI.__init__` takes `github: GitHubAdapter | None` — `molecules/apis/stack_api.py:49`
- `StackEntity.get_branch_repo_context()` returns `(owner, repo, base_ref, head_ref)` — `molecules/entities/stack_entity.py:193`
- `dependencies.py` creates `GitHubAdapter` concretely — `organisms/api/dependencies.py:89-141`
- `CloneManager` and `GitOperations` use `asyncio.create_subprocess_exec` pattern — `molecules/services/clone_manager.py`
- Backend runs locally (not Docker), so direct filesystem access to local clones is available

### What's missing

1. A `LocalGitAdapter` class that implements `GitRepoProtocol` via local `git` subprocess calls
2. Shared location for data models (currently co-located with `GitHubAdapter`)
3. Adapter selection logic at the DI layer — choose local vs. GitHub based on workspace config
4. Type annotations updated from concrete `GitHubAdapter` to `GitRepoProtocol`
5. Error types for local git failures (separate from GitHub API errors)

### Design constraints

- The 4 protocol methods accept `owner`/`repo` params. The local adapter ignores them (it already knows the repo path). This preserves the protocol contract without change.
- Write operations (`create_pull_request`, `merge_pr`, `mark_pr_ready`, `update_pull_request`, `create_review_comment`, `list_review_comments`, `hydrate_stack`) are GitHub-only. The local adapter does not need them. `StackAPI` already guards these with `if self.github is None` checks and the type annotations use `GitHubAdapter` specifically for write paths.
- The `_parse_patch` function already handles standard unified-diff format. `git diff` produces the same format as GitHub's patch field, so we reuse it directly.

## Plan

### Phase 1: Extract shared models into `git_types.py`

**Files**:
- New: `app/backend/src/molecules/providers/git_types.py`
- Modified: `app/backend/src/molecules/providers/github_adapter.py`
- Modified: all files that import DTOs from `github_adapter`

**Changes**:

Move these out of `github_adapter.py` into a new `git_types.py`:
- `DiffLine`, `DiffHunk`, `DiffFile`, `DiffData`
- `FileTreeNode`, `FileContent`
- `GitRepoProtocol`
- `_EXTENSION_LANGUAGE_MAP`, `_detect_language()`
- `_parse_patch()`, `_HUNK_HEADER_RE`
- `_build_file_tree()`
- `_MAX_CONTENT_SIZE` constant

`github_adapter.py` re-imports them from `git_types.py` for backward compatibility. The existing public API surface does not change — `from molecules.providers.github_adapter import DiffData` keeps working via re-export.

**Why**: These types are protocol-level, not GitHub-specific. Keeping them in `github_adapter.py` would force `LocalGitAdapter` to import from a GitHub-named module. The shared module clarifies the boundary: types and parsing utilities are adapter-agnostic.

**Import updates** (8 files):
| File | Currently imports | Change to |
|------|------------------|-----------|
| `organisms/api/routers/stacks.py` | `DiffData, FileContent, FileTreeNode` from `github_adapter` | from `git_types` (or keep via re-export) |
| `molecules/apis/stack_api.py` | `DiffData, FileContent, FileTreeNode, GitHubAdapter` (TYPE_CHECKING) | `DiffData, FileContent, FileTreeNode` from `git_types`; keep `GitHubAdapter` |
| `molecules/apis/stack_api.py` | `parse_owner_repo` from `github_adapter` | stays (that function stays in `github_adapter`) |
| `molecules/entities/stack_entity.py` | `parse_owner_repo, GitHubAdapter` | stays |
| `organisms/api/error_handlers.py` | `GitHubAPIError, GitHubNotFoundError, GitHubRateLimitError` | stays (these are GitHub-specific) |
| `organisms/api/app.py` | `GitHubAPIError` | stays |
| `__tests__/molecules/test_github_adapter.py` | everything | most can come from `git_types`; `GitHubAdapter` and errors stay |
| `__tests__/molecules/test_needs_restack.py` | `GitHubAdapter` | stays |

Decision: Use re-exports in `github_adapter.py` so no import changes are required. Downstream code can optionally migrate to `git_types` imports over time, but nothing breaks either way.

### Phase 2: Create `LocalGitAdapter`

**Files**:
- New: `app/backend/src/molecules/providers/local_git_adapter.py`

**Class design**:

```python
class LocalGitError(Exception):
    """Base error for local git operations."""
    def __init__(self, message: str, returncode: int = 1):
        super().__init__(message)
        self.returncode = returncode

class LocalGitRefNotFoundError(LocalGitError):
    """A requested ref (branch, SHA) does not exist in the local repo."""

class LocalGitAdapter:
    """Implements GitRepoProtocol using local git subprocess calls."""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path  # absolute path to the .git repo

    async def _run(self, *args: str) -> str:
        """Run a git command, return stdout. Raise LocalGitError on failure."""

    # --- Protocol methods ---
    async def get_diff(self, owner, repo, base_ref, head_ref) -> DiffData: ...
    async def get_file_tree(self, owner, repo, ref) -> FileTreeNode: ...
    async def get_file_content(self, owner, repo, ref, path) -> FileContent: ...
    async def get_behind_count(self, owner, repo, base_ref, head_ref) -> int: ...
```

**Git command mappings**:

| Protocol method | Git command | Notes |
|----------------|-------------|-------|
| `get_diff` | `git diff base_ref...head_ref` | Produces unified diff. Parse with `_parse_patch`. Use `--numstat` for per-file additions/deletions. Use `--diff-filter` + `--name-status` for change types. |
| `get_file_tree` | `git ls-tree -r --long ref` | Outputs `mode type hash size\tpath` per line. Map `blob` to `file`, `tree` to `dir`. |
| `get_file_content` | `git show ref:path` | Outputs raw file content. Check size with `git cat-file -s ref:path` first. |
| `get_behind_count` | `git rev-list --count head_ref..base_ref` | Count of commits on base not on head. Note: `a..b` means "commits reachable from b but not a". |

**Detailed implementation for each method**:

#### `get_diff(owner, repo, base_ref, head_ref)`

This needs three git commands to fully match GitHub's compare API output:

1. `git diff --name-status base_ref...head_ref` — produces change types per file:
   - `A` = added, `M` = modified, `D` = deleted, `R###` = renamed (with similarity %)
2. `git diff --numstat base_ref...head_ref` — produces per-file `additions\tdeletions\tpath`
   - Binary files show `-\t-\tpath` (handle gracefully: 0 additions, 0 deletions)
3. `git diff base_ref...head_ref` — full unified diff, split by file header (`diff --git a/... b/...`)

The three-dot `...` syntax is crucial: it means "diff between head_ref and the merge-base of base_ref and head_ref", which matches what GitHub shows for a PR diff. For a local two-dot diff, use `base_ref..head_ref` instead — but three-dot matches GitHub's behavior.

Alternatively, combine into two commands:
1. `git diff --numstat --diff-filter=ACDMRT base_ref...head_ref` (gives additions/deletions/change-type info via `--diff-filter`)
2. `git diff base_ref...head_ref` (full patch)

Actually the simplest approach is a single `git diff` call with combined flags, then parse the output:

1. `git diff --name-status base_ref...head_ref` — for change types
2. `git diff base_ref...head_ref` — for the full patch

Parse the full patch by splitting on `diff --git a/... b/...` boundaries. For each file, extract the patch portion and pass it to the existing `_parse_patch()`. For binary files, there will be no patch text — produce empty hunks.

For additions/deletions counts, rather than running `--numstat`, count from the parsed hunks (lines with `type="add"` and `type="del"`). This avoids a third subprocess call and the data is already parsed.

**Edge cases**:
- **Binary files**: `git diff` emits `Binary files a/X and b/X differ` instead of a patch. Detect this line, set additions=0, deletions=0, hunks=[].
- **Renamed files**: `--name-status` outputs `R100\told\tnew`. Map to `change_type="renamed"`, use the new path.
- **Large diffs**: Git output can be arbitrarily large. Set a reasonable buffer size or stream-parse. For MVP, read full output into memory (matching GitHub adapter behavior).
- **Missing refs**: If a branch hasn't been fetched, `git diff` fails with exit code 128. Catch this and raise `LocalGitRefNotFoundError`.
- **Empty diffs**: `git diff` produces no output when there are no changes. Return `DiffData(files=[], total_additions=0, total_deletions=0)`.

#### `get_file_tree(owner, repo, ref)`

Single command: `git ls-tree -r --long ref`

Output format per line: `<mode> <type> <hash> <size>\t<path>`

Example:
```
100644 blob abc1234    150	src/main.py
100644 blob def5678     42	README.md
```

Note: `-r` recurses into subtrees but only lists blobs (not tree entries). Directories are implied by paths. This is similar to how GitHub's flat tree array works — use `_build_file_tree()` directly. But we need to produce the same entry format:

```python
entries = [{"path": path, "type": "blob", "size": size} for each line]
```

Then call `_build_file_tree(entries)` which already handles implicit parent directory creation.

**Edge cases**:
- **Empty repo / empty tree at ref**: `git ls-tree` returns nothing. Return root node with empty children.
- **Submodules**: `ls-tree` shows them as `commit` type (mode 160000). Skip these or represent as a special node. For MVP, skip.
- **Symlinks**: mode 120000 — include as regular files.

#### `get_file_content(owner, repo, ref, path)`

Two commands:
1. `git cat-file -s ref:path` — get size in bytes (before reading content, to check against `_MAX_CONTENT_SIZE` and detect missing files)
2. `git show ref:path` — get raw content

**Edge cases**:
- **Binary files**: `git show` outputs raw binary. Detect via null bytes in first 8KB, or by checking if the file is in `.gitattributes` as binary. For MVP, attempt UTF-8 decode with `errors="replace"`.
- **Large files**: If `cat-file -s` returns size > `_MAX_CONTENT_SIZE`, still read but truncate to the constant (matching GitHub adapter behavior).
- **Missing path**: `git show ref:path` exits with code 128. Raise `LocalGitRefNotFoundError`.
- **Empty files**: Return `FileContent(path=path, content="", size=0, language=..., lines=0, truncated=False)`.

#### `get_behind_count(owner, repo, base_ref, head_ref)`

Single command: `git rev-list --count head_ref..base_ref`

This counts commits reachable from `base_ref` but not from `head_ref`, which is exactly GitHub's `behind_by` metric.

**Edge cases**:
- **Same ref**: Returns "0". Handle normally.
- **Unrelated histories**: `rev-list` still works, just shows all commits on base. Acceptable behavior.
- **Missing ref**: Exit code 128. Raise `LocalGitRefNotFoundError`.

**Caching**: Unlike the GitHub adapter, the local adapter should NOT cache aggressively. Local files change in real-time. However, we can cache based on ref SHA (if the ref is a full SHA, the content is immutable). For branch names, skip caching or use a very short TTL (e.g., 5 seconds). For MVP, no caching — local git commands are fast (sub-100ms).

### Phase 3: Update type annotations to use the protocol

**Files**:
- Modified: `app/backend/src/molecules/apis/stack_api.py`
- Modified: `app/backend/src/molecules/entities/stack_entity.py`

**Changes in `stack_api.py`**:

The `StackAPI` class has two distinct dependency needs:
1. **Read operations** (`get_branch_diff`, `get_branch_tree`, `get_branch_file`, `get_stack_detail`): Need `GitRepoProtocol` — either adapter works.
2. **Write operations** (`submit_stack`, `ready_stack`, `merge_stack`): Need `GitHubAdapter` specifically — only GitHub can create/merge PRs.

Refactor `StackAPI.__init__` to accept both:

```python
def __init__(
    self,
    db: AsyncSession,
    git_reader: GitRepoProtocol | None = None,
    github: GitHubAdapter | None = None,
) -> None:
```

Where:
- `git_reader` is used by all read operations (diff, tree, file, behind_count)
- `github` is used by write operations (submit, ready, merge, create_review_comment)
- If only `github` is provided (backward-compatible path), use it as both reader and writer
- If only `git_reader` is provided, reads work but writes raise RuntimeError

Alternatively (simpler and less disruptive): keep a single `github` param but change its type annotation:

```python
def __init__(
    self,
    db: AsyncSession,
    github: GitRepoProtocol | None = None,
) -> None:
```

Read operations use `self.github` through the protocol interface. Write operations do a runtime `isinstance(self.github, GitHubAdapter)` check. This keeps the constructor signature change minimal.

**Decision**: Use the two-param approach. It is more explicit, makes the read-vs-write capability visible in the type system, and does not require `isinstance` checks. However, to minimize disruption in Phase 3, start with the simpler single-param approach and upgrade to two-param in a follow-up if needed.

Actually, the cleanest approach for Phase 3:

1. Add a `git_reader` property that returns whichever adapter is available for reading.
2. Keep `github` for writes, with its concrete type.

```python
class StackAPI:
    def __init__(
        self,
        db: AsyncSession,
        github: GitHubAdapter | None = None,
        git_reader: GitRepoProtocol | None = None,
    ) -> None:
        self.db = db
        self.entity = StackEntity(db)
        self.github = github
        self._git_reader = git_reader
        self._comment_svc = ReviewCommentService()

    @property
    def reader(self) -> GitRepoProtocol | None:
        """Resolve the best available reader: explicit reader, or fall back to github."""
        return self._git_reader or self.github
```

Then read methods use `self.reader` instead of `self.github`. Write methods continue using `self.github`. Error messages update: "Git reader not configured" for reads, "GitHub adapter required for write operations" for writes.

**Changes in `stack_entity.py`**:

`submit_stack` and `ready_stack` accept `github: GitHubAdapter` — these stay as-is. They only need the write-capable GitHub adapter.

`get_branch_repo_context()` currently parses `workspace.repo_url` into `(owner, repo)`. For local adapter, this context resolution changes:
- The local adapter ignores `owner`/`repo` — it uses `repo_path` directly.
- The `owner` and `repo` values still need to flow through for GitHub write operations.
- The method can return dummy values when `local_path` is set and no `repo_url` is available.
- But actually, `repo_url` is a required field on Workspace, so it always exists. And `parse_owner_repo` will work on it. The local adapter just ignores those values. No change needed in `get_branch_repo_context`.

### Phase 4: Adapter selection — Final Design

**No DI layer changes needed.** Adapter selection happens per-workspace inside `StackAPI`.

The adapter choice depends on the *workspace* (which has `local_path`), not the user. A user might have multiple workspaces: some with `local_path`, some without. The resolution point is when a branch is being queried, because that's when we know which workspace is involved.

The DI layer continues to provide `GitHubAdapter | None` as today. `StackAPI` gains a `_get_reader_for_branch` method that resolves the best adapter lazily:

```python
async def _get_reader_for_branch(self, branch_id: UUID) -> GitRepoProtocol:
    """Resolve the best git reader for a specific branch's workspace.

    Priority: local_path (if exists and is a git repo) > GitHubAdapter > error.
    """
    branch = await self.entity.get_branch(branch_id)
    workspace = await self.entity.workspace_service.get(self.db, branch.workspace_id)
    if workspace is None:
        raise BranchNotFoundError(branch_id)

    # Prefer local if available and is a valid git repo
    if workspace.local_path:
        repo_path = Path(workspace.local_path)
        if repo_path.is_dir() and (repo_path / ".git").exists():
            from molecules.providers.local_git_adapter import LocalGitAdapter
            return LocalGitAdapter(workspace.local_path)

    # Fall back to GitHub
    if self.github is not None:
        return self.github

    raise RuntimeError("No git reader available: workspace has no local_path and no GitHub adapter configured")
```

Read methods (`get_branch_diff`, `get_branch_tree`, `get_branch_file`) use `self._get_reader_for_branch(branch_id)`. Write methods (`submit_stack`, `ready_stack`, `merge_stack`) continue using `self.github` directly.

**`_compute_restack_flags` note**: The existing guard (`if self.github is not None`) means local-only workspaces will show `needs_restack = false` for all branches. This is acceptable — restack detection from local git can be added later.

The diff/tree/file endpoints already use `StackAPIDep` (not `UserStackAPIDep`), so they work with or without a GitHub token. No dependency changes needed.

### Phase 5: Error handling

**Files**:
- Modified: `app/backend/src/organisms/api/error_handlers.py`
- Modified: `app/backend/src/organisms/api/app.py`

**Changes**: Register a handler for `LocalGitError`:

```python
async def local_git_exception_handler(request: Request, exc: LocalGitError) -> JSONResponse:
    if isinstance(exc, LocalGitRefNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    return JSONResponse(status_code=500, content={"detail": f"Local git error: {exc}"})
```

### Phase 6: Tests

**Files**:
- New: `app/backend/__tests__/molecules/test_local_git_adapter.py`

**Test strategy**:

Unit tests that mock `asyncio.create_subprocess_exec` to simulate git command output. This matches the project's existing pattern — the GitHub adapter tests mock `httpx`, the local adapter tests mock subprocess.

Test cases:

**`get_diff` tests**:
- Simple modification (one file changed)
- Multiple files with mixed change types (added, modified, deleted, renamed)
- Binary file (no patch, `Binary files ... differ`)
- Empty diff (no changes between refs)
- Missing ref (exit code 128 -> `LocalGitRefNotFoundError`)
- Diff with multiple hunks per file
- File with only additions (new file)
- File with only deletions (deleted file)

**`get_file_tree` tests**:
- Flat file list
- Nested directories (implicit parent creation)
- Empty tree
- Files with sizes

**`get_file_content` tests**:
- Normal text file
- Large file (truncation at `_MAX_CONTENT_SIZE`)
- Missing file (exit 128 -> error)
- Empty file
- Language detection

**`get_behind_count` tests**:
- Normal count (returns integer)
- Zero (same ref / up to date)
- Missing ref (error)

**Integration test** (optional, marked `@pytest.mark.integration`):
- Create a temp git repo with known commits, run actual `LocalGitAdapter` against it
- Verify diff output matches expected structure
- This proves the git command parsing works end-to-end without mocks

**`_get_reader_for_branch` tests** (in `test_stack_api.py` or new file):
- Workspace with `local_path` that exists -> returns `LocalGitAdapter`
- Workspace with `local_path` that does not exist -> falls back to `GitHubAdapter`
- Workspace with no `local_path` -> uses `GitHubAdapter`
- Workspace with no `local_path` and no GitHub adapter -> raises `RuntimeError`

## Implementation Phases

| Phase | What | Depends On | Risk |
|-------|------|------------|------|
| 1 | Extract shared types to `git_types.py` | -- | Low — pure refactor with re-exports |
| 2 | Create `LocalGitAdapter` class | Phase 1 | Medium — git output parsing |
| 3 | Update `StackAPI` to resolve adapter per-workspace | Phase 2 | Low — additive change |
| 4 | Update DI layer (if needed) | Phase 3 | Low — minimal changes |
| 5 | Error handling | Phase 2 | Low |
| 6 | Tests | Phase 2 | Low |

Phases 5 and 6 can run in parallel with Phase 3-4.

## File Tree

```
app/backend/src/
  molecules/providers/
    git_types.py                    # NEW: shared DTOs, protocol, parsing utils
    local_git_adapter.py            # NEW: LocalGitAdapter class
    github_adapter.py               # MODIFIED: re-export from git_types
    __init__.py                     # MODIFIED: export LocalGitAdapter
  molecules/apis/
    stack_api.py                    # MODIFIED: _get_reader_for_branch, read methods
  organisms/api/
    error_handlers.py               # MODIFIED: LocalGitError handler
    app.py                          # MODIFIED: register handler

app/backend/__tests__/
  molecules/
    test_local_git_adapter.py       # NEW: unit tests
    test_stack_api_reader.py        # NEW: reader resolution tests
```

## Key Design Decisions

### 1. Adapter resolves per-workspace, not per-user

The local adapter is tied to a workspace's `local_path`, not to the user. This means the same user can have some workspaces using local git and others using GitHub. The resolution happens inside `StackAPI._get_reader_for_branch()`, not at the DI injection point.

**Alternative considered**: Inject the adapter at the DI level based on a header or config flag. Rejected because the adapter choice depends on workspace-level data that's only available after loading the branch.

### 2. Re-export from `github_adapter.py` for backward compatibility

Rather than updating all import sites in Phase 1, `github_adapter.py` re-exports everything from `git_types.py`. This makes Phase 1 a zero-risk refactor — existing code continues to work without changes. Import sites can migrate to `git_types` over time.

### 3. No caching in `LocalGitAdapter`

GitHub API calls are rate-limited and slow (network round-trip). Local git commands are fast (sub-100ms). Adding caching would introduce staleness bugs — the user might amend a commit and the diff would be stale. Skip caching entirely for local operations.

### 4. `owner`/`repo` params are ignored but accepted

The protocol requires them. The local adapter accepts and discards them. This avoids changing the protocol interface, which would require changes to both adapters and all callers. The local adapter's `__init__` takes the `repo_path` which is all it needs.

### 5. Three-dot diff (`base...head`) not two-dot

`git diff base...head` computes the diff from the merge-base, matching what GitHub shows for PRs. `git diff base..head` would show all changes between the two refs including changes on the base branch since the fork point. We want the former.

### 6. Separate error hierarchy from GitHub errors

`LocalGitError` is distinct from `GitHubAPIError`. They share no inheritance. This prevents confusion at the error handler level and keeps error messages clear about what failed (local subprocess vs. API call).

## Open Questions

1. **Fetch before diff?** If the local repo hasn't been fetched recently, remote branches may be stale. Should the adapter run `git fetch` before operations? Recommendation: No — let the user manage their local repo. The adapter is read-only and fast. Adding implicit fetches would be slow and surprising.

2. **Submodule handling**: `git ls-tree` shows submodules as `commit` type entries. Should we include them in the file tree? Recommendation: Skip for MVP, add later if needed.

3. **Worktree support**: Should `local_path` point to a worktree or the main repo? `git` commands work transparently in worktrees, so no special handling needed. Document that `local_path` can be either.

4. **Concurrent access**: Multiple requests may hit the local adapter simultaneously. `git` commands are safe to run concurrently against the same repo (they use lock files internally). No mutex needed.

5. **Renamed file path in diff**: `git diff --name-status` shows `R100\told\tnew`. Which path should we use in `DiffFile.path`? Recommendation: Use the new path (matching GitHub's behavior), and optionally add an `old_path` field to `DiffFile` later.
