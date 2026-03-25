---
title: "SB-064: Needs-restack detection from GitHub branch comparison"
date: 2026-03-24
status: draft
branch: dug/sb-064/1-needs-restack-detection
depends_on: []
adrs: []
---

# SB-064: Needs-restack detection from GitHub branch comparison

## Goal

Detect when stacked branches are behind their parent and surface this via the existing RestackBadge UI. Currently `needsRestack` is hardcoded to `false` for every branch in `App.tsx`. This spec adds a `get_behind_count` method to `GitHubAdapter`, enriches the `get_stack_detail` response with `needs_restack: bool` per branch, and wires the frontend to read it from the API instead of hardcoding.

## How It Works

The GitHub compare API (`GET /repos/{owner}/{repo}/compare/{base}...{head}`) already returns a `behind_by` field. A branch needs restacking when `behind_by > 0`, meaning the parent branch has commits that haven't been incorporated.

- Branch at position 1: compare against trunk (e.g. `main...branch-1`)
- Branch at position N: compare against branch at position N-1

## File Tree

Files to modify:

```
app/backend/src/molecules/providers/github_adapter.py    # Add get_behind_count method
app/backend/src/molecules/apis/stack_api.py              # Enrich get_stack_detail with needs_restack
app/backend/src/organisms/api/routers/stacks.py          # (No changes needed -- dict response passes through)
app/frontend/src/types/stack.ts                          # Add needs_restack to BranchWithPR
app/frontend/src/App.tsx                                 # Read needs_restack from API data
app/backend/__tests__/molecules/test_needs_restack.py    # New: unit tests
```

No database migrations needed.

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Add `get_behind_count` to GitHubAdapter | -- |
| 2 | Enrich `get_stack_detail` in StackAPI | Phase 1 |
| 3 | Wire frontend to read `needs_restack` from API | Phase 2 |

## Phase Details

### Phase 1: GitHubAdapter.get_behind_count

Add a lightweight method that calls the compare API and returns only the `behind_by` integer. This avoids the overhead of parsing the full diff.

**File: `app/backend/src/molecules/providers/github_adapter.py`**

Add to `GitHubAdapter`:

```python
async def get_behind_count(self, owner: str, repo: str, base_ref: str, head_ref: str) -> int:
    """Return how many commits head_ref is behind base_ref.

    Uses the compare API: GET /repos/{owner}/{repo}/compare/{base}...{head}
    The response includes `behind_by` which counts commits on base not on head.
    """
    cache_key = f"behind:{owner}/{repo}:{base_ref}:{head_ref}"
    cached = await self._cache.get(cache_key, namespace=_CACHE_NS)
    if cached is not None:
        return int(cached)

    response = await self._client.get(
        f"/repos/{owner}/{repo}/compare/{base_ref}...{head_ref}"
    )
    self._raise_for_status(response)
    data = response.json()
    behind_by = int(data.get("behind_by", 0))

    await self._cache.set(cache_key, behind_by, ttl=_CACHE_TTL, namespace=_CACHE_NS)
    return behind_by
```

Also add to `GitRepoProtocol`:

```python
async def get_behind_count(self, owner: str, repo: str, base_ref: str, head_ref: str) -> int: ...
```

**Design note**: We use a separate method (not piggybacking on `get_diff`) because `get_stack_detail` needs behind counts for all branches but doesn't need full diff data. Separate caching avoids coupling.

### Phase 2: Enrich get_stack_detail

**File: `app/backend/src/molecules/apis/stack_api.py`**

Modify `get_stack_detail` to compute `needs_restack` for each branch using parallel GitHub API calls.

```python
async def get_stack_detail(self, stack_id: UUID) -> dict[str, object]:
    """Get a stack with all branches, PRs, and restack status."""
    data = await self.entity.get_stack_with_branches(stack_id)
    stack = data["stack"]
    branch_list = data["branches"]

    # Compute needs_restack per branch (only if github adapter is available)
    restack_flags: list[bool] = [False] * len(branch_list)
    if self.github is not None and len(branch_list) > 0:
        restack_flags = await self._compute_restack_flags(stack, branch_list)

    branches = []
    for i, bd in enumerate(branch_list):
        branch_resp = BranchResponse.model_validate(bd["branch"])
        pr_resp = (
            PullRequestResponse.model_validate(bd["pull_request"])
            if bd["pull_request"]
            else None
        )
        branches.append({
            "branch": branch_resp.model_dump(),
            "pull_request": pr_resp.model_dump() if pr_resp else None,
            "needs_restack": restack_flags[i],
        })
    return {
        "stack": StackResponse.model_validate(stack).model_dump(),
        "branches": branches,
    }
```

Add a private helper:

```python
async def _compute_restack_flags(
    self, stack: object, branch_list: list[dict[str, object]]
) -> list[bool]:
    """Compute needs_restack for each branch in a stack.

    Uses asyncio.gather for parallel GitHub API calls.
    Branches that are merged or have no remote never need restack.
    """
    import asyncio

    assert self.github is not None

    # Resolve owner/repo from the first branch's workspace
    first_branch = branch_list[0]["branch"]
    workspace = await self.entity.workspace_service.get(self.db, first_branch.workspace_id)
    if workspace is None:
        return [False] * len(branch_list)
    owner, repo = parse_owner_repo(workspace.repo_url)

    async def check_branch(index: int, bd: dict) -> bool:
        branch = bd["branch"]
        pr = bd.get("pull_request")

        # Merged branches never need restack
        if branch.state == "merged" or (pr is not None and pr.state == "merged"):
            return False

        head_ref = branch.head_sha if branch.head_sha else branch.name

        # Determine base ref
        if branch.position == 1:
            base_ref = stack.trunk
        else:
            prev_branch = branch_list[index - 1]["branch"]
            base_ref = prev_branch.name

        try:
            behind_count = await self.github.get_behind_count(
                owner, repo, base_ref, head_ref
            )
            return behind_count > 0
        except Exception:
            # On API error, don't flag as needing restack (avoid false positives)
            return False

    tasks = [check_branch(i, bd) for i, bd in enumerate(branch_list)]
    results = await asyncio.gather(*tasks)
    return list(results)
```

**Import needed**: Add `from molecules.providers.github_adapter import parse_owner_repo` to `stack_api.py` (already used in `stack_entity.py`).

**Router layer** (`app/backend/src/organisms/api/routers/stacks.py`): No changes needed. The `get_stack_detail` endpoint returns `dict[str, object]` with no strict response_model, so the new `needs_restack` field passes through automatically.

### Phase 3: Frontend wiring

**File: `app/frontend/src/types/stack.ts`**

Add `needs_restack` to `BranchWithPR`:

```typescript
export interface BranchWithPR {
  branch: Branch;
  pull_request: PullRequest | null;
  needs_restack?: boolean;  // from get_stack_detail enrichment
}
```

**File: `app/frontend/src/App.tsx`**

Change the items mapping (line 137):

```typescript
// Before:
needsRestack: false,

// After:
needsRestack: b.needs_restack ?? false,
```

Where `b` is `data.branches[index]` (already a `BranchWithPR`). Falls back to `false` if the field is missing (backward compatible).

## Edge Cases

| Case | Behavior | Rationale |
|------|----------|-----------|
| Merged branch | `needs_restack: false` | Done; restacking is irrelevant |
| Merged PR | `needs_restack: false` | Same as above, check PR state too |
| No GitHub adapter configured | All `false` | No API to compare against; degrade gracefully |
| GitHub API error (rate limit, 404) | `false` for that branch | Avoid false positives; catch in `check_branch` |
| Branch has no remote push yet | `false` | Compare API will 404; caught by error handling |
| Branch at position 1 | Compares against `stack.trunk` | Trunk is always the canonical base for first branch |
| Stack with only one branch | Works fine | Position 1 compares against trunk |
| `behind_by == 0` | `false` | Branch is up-to-date with parent |

## Test Strategy

**File: `app/backend/__tests__/molecules/test_needs_restack.py`**

### Unit tests (mock GitHub API):

1. **`test_get_behind_count_returns_integer`** -- Mock `_client.get` to return `{"behind_by": 3}`, verify returns `3`.

2. **`test_get_behind_count_caches_result`** -- Call twice, verify only one HTTP request.

3. **`test_get_behind_count_zero`** -- `behind_by: 0` returns `0`.

4. **`test_compute_restack_flags_parallel`** -- Mock `get_behind_count` returning `[2, 0, 5]` for three branches. Verify flags `[True, False, True]`.

5. **`test_merged_branch_skipped`** -- Branch with `state="merged"` always returns `False`.

6. **`test_merged_pr_skipped`** -- Branch with PR `state="merged"` always returns `False`.

7. **`test_github_error_returns_false`** -- When `get_behind_count` raises, that branch gets `False`.

8. **`test_no_github_adapter_all_false`** -- `StackAPI(db, github=None)` returns all `needs_restack: False`.

9. **`test_position_1_uses_trunk`** -- First branch compares against `stack.trunk`.

10. **`test_position_n_uses_previous_branch`** -- Branch at position 3 compares against branch at position 2's name.

### Frontend (manual verification):

- Seed a stack where one branch is behind its parent. Verify yellow badge appears.
- Verify StackHeader chip shows correct count (e.g. "1 need restack").
- Verify merged branches never show the badge.

## Open Questions

None -- the implementation is straightforward. The compare API is already in use for diffs, and the `behind_by` field is part of the standard response.
