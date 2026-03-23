---
title: "SB-055: Stack merge flow via GitHub API"
status: in-progress
issue: "#92"
epic: EP-009
---

# SB-055: Stack Merge Flow via GitHub API

## Overview

Wire the Merge button to merge PRs bottom-up through the stack via GitHub API. Stack Bench is remote-first — reads everything from GitHub, no local git operations needed.

## Files to Modify

| File | Change |
|------|--------|
| `app/backend/src/molecules/providers/github_adapter.py` | Add `merge_pr()`, `mark_pr_ready()` methods after `hydrate_stack()` (line 452) |
| `app/backend/src/molecules/apis/stack_api.py` | Add `merge_stack()` method after `get_branch_file()` (line 148) |
| `app/backend/src/organisms/api/routers/stacks.py` | Add `POST /{stack_id}/merge` endpoint after `delete_stack` (line 78) |
| `app/frontend/src/App.tsx` | Wire `onMerge` callback to call API + invalidate cache (line 172) |

## Implementation Steps

### Step 1: GitHubAdapter — `merge_pr()` and `mark_pr_ready()`

File: `app/backend/src/molecules/providers/github_adapter.py`

Add after `hydrate_stack()` (after line 452):

```python
async def merge_pr(
    self, owner: str, repo: str, pr_number: int, *, merge_method: str = "squash"
) -> dict[str, object]:
    """Merge a pull request via GitHub API."""
    response = await self._client.put(
        f"/repos/{owner}/{repo}/pulls/{pr_number}/merge",
        json={"merge_method": merge_method},
    )
    self._raise_for_status(response)
    return response.json()

async def mark_pr_ready(self, owner: str, repo: str, pr_number: int) -> None:
    """Remove draft status from a pull request."""
    response = await self._client.patch(
        f"/repos/{owner}/{repo}/pulls/{pr_number}",
        json={"draft": False},
    )
    self._raise_for_status(response)
```

### Step 2: StackAPI — `merge_stack()`

File: `app/backend/src/molecules/apis/stack_api.py`

Add after `get_branch_file()` (after line 148):

```python
async def merge_stack(self, stack_id: UUID) -> dict[str, object]:
    """Merge all PRs in the stack, bottom-up."""
    if self.github is None:
        raise RuntimeError("GitHubAdapter not configured")

    data = await self.entity.get_stack_with_branches(stack_id)
    results = []

    for bd in data["branches"]:
        branch = bd["branch"]
        pr = bd["pull_request"]
        if pr is None or pr.state == "merged":
            continue
        if pr.external_id is None:
            raise ValueError(f"PR for branch {branch.name} has no GitHub PR number")

        owner, repo, _, _ = await self.entity.get_branch_repo_context(branch.id)

        # Mark ready if draft
        if pr.state == "draft":
            await self.github.mark_pr_ready(owner, repo, pr.external_id)
            pr.transition_to("open")

        # Merge
        result = await self.github.merge_pr(owner, repo, pr.external_id)
        pr.transition_to("merged")
        branch.transition_to("merged")
        results.append({"branch": branch.name, "pr_number": pr.external_id, "merged": True})

    await self.db.commit()
    return {"stack_id": str(stack_id), "merged": results}
```

### Step 3: Router endpoint

File: `app/backend/src/organisms/api/routers/stacks.py`

Add after `delete_stack` (after line 78):

```python
@router.post("/{stack_id}/merge")
async def merge_stack(stack_id: UUID, api: StackAPIDep) -> dict[str, object]:
    """Merge all PRs in the stack bottom-up via GitHub API."""
    return await api.merge_stack(stack_id)
```

### Step 4: Frontend — wire Merge button

File: `app/frontend/src/App.tsx` (around line 172)

Replace `console.log("merge stack")` with:

```typescript
const handleMerge = async () => {
  if (!stackId) return;
  try {
    await apiClient.post(`/api/v1/stacks/${stackId}/merge`);
    queryClient.invalidateQueries({ queryKey: ["stack-detail"] });
  } catch (err) {
    console.error("Merge failed:", err);
  }
};
```

Then use `onMerge={handleMerge}` in the JSX.

## Key Architecture Notes

- **GitHubAdapter**: Uses `httpx.AsyncClient` with `BASE_URL = "https://api.github.com"`, `_raise_for_status()` for error handling, custom error classes (`GitHubAPIError`, `GitHubNotFoundError`, `GitHubRateLimitError`)
- **StackAPI**: Facade over `self.github` (GitHubAdapter), `self.entity` (StackEntity), `self.db` (session)
- **StackEntity**: `get_stack_with_branches()` returns ordered branches, `get_branch_repo_context()` resolves owner/repo
- **PR states**: `draft → open → approved → merged` (already defined in model)
- **Branch states**: Also has `merged` as terminal state

## Acceptance Criteria

- `POST /api/v1/stacks/{id}/merge` endpoint merges PRs bottom-up
- Draft PRs are automatically marked as ready before merge
- Each PR and branch state transitions to "merged" in DB
- Frontend Merge button calls the endpoint
- Stack detail re-fetches after merge completes
- Already-merged PRs are skipped (idempotent)
- Error response if any PR has no `external_id`
- Merge method defaults to "squash"
