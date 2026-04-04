---
title: Stack Workflow Wiring — End-to-End Push/Submit/Ready
date: 2026-04-03
status: reviewed
epic: EP-003
issues: [SB-052]
depends_on: [2026-03-19-stack-branch-pr-domain]
adrs: [ADR-001, ADR-004]
---

# Stack Workflow Wiring — End-to-End Push/Submit/Ready

## Goal

Wire the three-tier stack workflow end-to-end: `push` syncs local git branches to Postgres*and also pushes the branch to git remote - no PR but remote branch*, `submit` creates GitHub draft PRs, `ready` marks PRs for review. The backend CLI organism (Typer) and REST API are the two entry points; the Go TUI (ADR-001) is a thin HTTP client that calls the REST API. This spec also completes SB-052 (Project model fields) as a prerequisite, adds GitHub write operations to GitHubAdapter, and builds a minimal frontend project creation form.

## Architecture

```
User (Go TUI or curl)
    |
    | HTTP POST /api/v1/stacks/{id}/push
    | HTTP POST /api/v1/stacks/{id}/submit
    | HTTP POST /api/v1/stacks/{id}/ready
    v
[Organisms: REST Router + CLI] -- thin interface, no logic
    |
    v
[Molecules: StackAPI facade] -- serialization, permissions, commit
    |
    v
[Molecules: StackEntity] -- domain aggregate, state transitions, events
    |
    +---> [Features: StackService, BranchService, PullRequestService] -- CRUD
    +---> [Molecules: GitHubAdapter] -- GitHub REST API (write ops)
    +---> [Molecules: GitHubOAuthAPI] -- token resolution (user's Connection)
```

Key architectural decision: the `GitHubAdapter` currently uses a static `GITHUB_TOKEN` from settings (line 103-104 of `dependencies.py`). For write operations that act on behalf of a user (creating PRs, marking ready), we must use the **user's OAuth token** from their encrypted `Connection`. This spec introduces a `UserGitHubAdapter` dependency that resolves the token from the authenticated user's Connection, falling back to the settings token for read-only operations.

## Implementation Phases

| Phase | What | Depends On | Files Changed/Created |
|-------|------|------------|-----------------------|
| 1 | GitHubAdapter write operations | -- | 2 modified |
| 2 | User-scoped GitHubAdapter dependency | Phase 1 | 1 modified |
| 3 | StackEntity push/submit/ready methods | Phase 1 | 2 modified |
| 4 | StackAPI facade operations | Phase 3 | 1 modified |
| 5 | REST API endpoints (push, submit, ready) | Phase 4 | 1 modified |
| 6 | Event topics for new operations | Phase 4 | 2 modified |
| 7 | Stack CLI organism (Typer) | Phase 5 | 3 created, 1 modified |
| 8 | Frontend project creation form | Phase 5 | 3 created, 2 modified |
| 9 | Tests | All | 5 created/modified |

---

## Phase 1: GitHubAdapter Write Operations

### Goal

Add `create_pull_request` and `update_pull_request` methods to the existing `GitHubAdapter`. The adapter already has `merge_pr`, `mark_pr_ready`, and `create_review_comment` -- this adds PR creation to complete the write surface.

> **REVIEWER NOTE (B1):** The existing `mark_pr_ready` method uses REST API `PATCH /pulls/{pr_number}` with `{"draft": false}`, but GitHub REST API v3 does not support removing draft status via PATCH. This requires the GraphQL mutation `markPullRequestReadyForReview`. This method must be rewritten to use GraphQL as part of this phase, since `ready_stack` (Phase 3) depends on it working correctly.

### File: `app/backend/src/molecules/providers/github_adapter.py`

**Add method: `create_pull_request`**

```python
async def create_pull_request(
    self,
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    *,
    body: str | None = None,
    draft: bool = True,
) -> dict[str, object]:
    """Create a pull request on GitHub.

    Args:
        owner: Repository owner (org or user).
        repo: Repository name.
        title: PR title.
        head: Head branch name.
        base: Base branch name (parent branch or trunk).
        body: Optional PR description/body.
        draft: Whether to create as draft (default True).

    Returns:
        GitHub API response dict with at least 'number', 'html_url', 'state'.
    """
    payload: dict[str, object] = {
        "title": title,
        "head": head,
        "base": base,
        "draft": draft,
    }
    if body is not None:
        payload["body"] = body
    response = await self._client.post(
        f"/repos/{owner}/{repo}/pulls",
        json=payload,
    )
    self._raise_for_status(response)
    data: dict[str, object] = response.json()
    return data
```

**Add method: `update_pull_request`**

```python
async def update_pull_request(
    self,
    owner: str,
    repo: str,
    pr_number: int,
    *,
    title: str | None = None,
    body: str | None = None,
    base: str | None = None,
) -> dict[str, object]:
    """Update an existing pull request on GitHub.

    Used when a branch's base changes after restack (need to update PR base).
    """
    payload: dict[str, object] = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    if base is not None:
        payload["base"] = base
    response = await self._client.patch(
        f"/repos/{owner}/{repo}/pulls/{pr_number}",
        json=payload,
    )
    self._raise_for_status(response)
    data: dict[str, object] = response.json()
    return data
```

### Rationale

- `mark_pr_ready` already exists (line 476 of `github_adapter.py`). We need `create_pull_request` for the `submit` operation and `update_pull_request` for base-branch updates during restack.
- Draft PR creation uses the GitHub `draft: true` parameter per the REST API v3.
- The adapter is stateless aside from its httpx client -- token is set at construction time.

---

## Phase 2: User-Scoped GitHubAdapter Dependency

### Goal

Create a FastAPI dependency that constructs a `GitHubAdapter` with the **authenticated user's GitHub OAuth token** (from their `Connection`), rather than the static settings token.

### File: `app/backend/src/organisms/api/dependencies.py`

**Add new dependency:**

```python
async def get_user_github_adapter(
    user: CurrentUser,
    db: DatabaseSession,
) -> GitHubAdapter:
    """Resolve GitHubAdapter using the authenticated user's OAuth token.

    Falls back to the settings GITHUB_TOKEN if the user has no connection
    (for read-only operations like diffs). Raises 403 for write ops that
    require a user token.
    """
    token = await _github_oauth.get_user_github_token(db, user.id)
    if token:
        return GitHubAdapter(token=token)
    # Fallback for read ops (diff, tree, file content)
    settings = get_settings()
    if settings.GITHUB_TOKEN:
        return GitHubAdapter(token=settings.GITHUB_TOKEN)
    raise HTTPException(403, detail="GitHub account not connected — connect via Settings")


UserGitHubAdapterDep = Annotated[GitHubAdapter, Depends(get_user_github_adapter)]
```

**Update `get_stack_api` to accept user-scoped adapter:**

```python
def get_stack_api_with_user(db: DatabaseSession, github: UserGitHubAdapterDep) -> StackAPI:
    return StackAPI(db, github)


UserStackAPIDep = Annotated[StackAPI, Depends(get_stack_api_with_user)]
```

The existing `StackAPIDep` (using the static token) continues to work for unauthenticated endpoints. The new `UserStackAPIDep` is used on endpoints that do write operations (push, submit, ready, merge).

### Migration path

Update the existing write endpoints (`merge_stack`, `sync_stack`) to use `UserStackAPIDep`. Read-only endpoints (`get_stack_detail`, `get_branch_diff`, etc.) can keep `StackAPIDep`.

---

## Phase 3: StackEntity Push/Submit/Ready Methods

### Goal

Add three domain operations to `StackEntity` that coordinate the feature services and GitHubAdapter.

### File: `app/backend/src/molecules/entities/stack_entity.py`

**Method: `push_stack`**

Reconciles DB state with branch data provided by the client. This is a superset of the existing `sync_stack` method -- `sync_stack` creates/updates branches; `push_stack` does the same plus transitions branch states to `pushed`.

```python
async def push_stack(
    self,
    stack_id: UUID,
    workspace_id: UUID,
    branches_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Push: sync branch data from client and transition to pushed state.

    Each entry in branches_data:
      - name: str (git branch name)
      - position: int
      - head_sha: str (current HEAD)
      - pr_number: int | None (existing GitHub PR, if any)
      - pr_url: str | None

    State transitions:
      - Branch: created -> pushed (first push)
      - Branch: pushed stays pushed (subsequent pushes update head_sha)
      - Stack: draft -> active (first push with any branch)
    """
    result = await self.sync_stack(stack_id, workspace_id, branches_data)

    # Transition branches to pushed state
    for br in result["branches"]:
        branch = br["branch"]
        if branch.state == "created":
            branch.transition_to("pushed")

    # Transition stack to active on first push
    stack = await self.get_stack(stack_id)
    if stack.state == "draft":
        stack.transition_to("active")

    return result
```

**Method: `submit_stack`**

Creates GitHub draft PRs for all pushed branches that don't yet have a PR.

```python
async def submit_stack(
    self,
    stack_id: UUID,
    github: GitHubAdapter,
) -> dict[str, Any]:
    """Submit: create GitHub draft PRs for pushed branches without PRs.

    For each branch in the stack (ordered by position):
      1. Skip if branch already has a PR with external_id
      2. Resolve owner/repo from workspace
      3. Determine base branch (previous branch name, or trunk for position 1)
      4. Create draft PR via GitHub API
      5. Create/update PullRequest record with external_id and external_url
      6. Transition branch: pushed -> reviewing (or ready -> submitted)
      7. Transition PR: draft (initial state from creation)

    State transitions:
      - Branch: pushed -> reviewing
      - Stack: active -> submitted (when all branches have PRs)
    """
    data = await self.get_stack_with_branches(stack_id)
    stack = data["stack"]
    branch_list = data["branches"]
    results: list[dict[str, Any]] = []

    for i, bd in enumerate(branch_list):
        branch = bd["branch"]
        pr = bd.get("pull_request")

        # Skip branches that already have GitHub PRs
        if pr is not None and pr.external_id is not None:
            results.append({
                "branch": branch.name,
                "action": "skipped",
                "pr_number": pr.external_id,
            })
            continue

        # Skip branches not yet pushed
        if branch.state == "created":
            results.append({
                "branch": branch.name,
                "action": "skipped",
                "reason": "not_pushed",
            })
            continue

        # Resolve repo context
        workspace = await self.workspace_service.get(self.db, branch.workspace_id)
        if workspace is None:
            continue
        owner, repo = parse_owner_repo(workspace.repo_url)

        # Determine base branch
        if branch.position == 1:
            base = stack.trunk
        else:
            prev_branch = branch_list[i - 1]["branch"]
            base = prev_branch.name

        # Create draft PR on GitHub
        gh_pr = await github.create_pull_request(
            owner, repo,
            title=branch.name,
            head=branch.name,
            base=base,
            body=pr.description if pr else None,
            draft=True,
        )

        pr_number = int(gh_pr["number"])
        pr_url = str(gh_pr["html_url"])

        # Create or update PullRequest record
        if pr is None:
            pr = await self.pr_service.create(
                self.db,
                PullRequestCreate(
                    branch_id=branch.id,
                    title=branch.name,
                    external_id=pr_number,
                    external_url=pr_url,
                ),
            )
        else:
            pr = await self.pr_service.update(
                self.db,
                pr.id,
                PullRequestUpdate(
                    external_id=pr_number,
                    external_url=pr_url,
                ),
            )

        # Transition branch state
        if branch.state == "pushed":
            branch.transition_to("reviewing")

        results.append({
            "branch": branch.name,
            "action": "created",
            "pr_number": pr_number,
            "pr_url": pr_url,
        })

    # Transition stack state if all branches submitted
    all_submitted = all(
        bd.get("pull_request") is not None
        and (bd["pull_request"].external_id is not None
             or any(r.get("branch") == bd["branch"].name and r.get("action") == "created"
                    for r in results))
        for bd in branch_list
        if bd["branch"].state != "created"
    )
    if all_submitted and stack.state == "active":
        stack.transition_to("submitted")

    return {
        "stack_id": str(stack_id),
        "results": results,
    }
```

**Method: `ready_stack`**

Marks all draft PRs in a stack as ready for review.

```python
async def ready_stack(
    self,
    stack_id: UUID,
    github: GitHubAdapter,
    *,
    branch_ids: list[UUID] | None = None,
) -> dict[str, Any]:
    """Ready: mark draft PRs as ready for review on GitHub.

    If branch_ids is provided, only those branches are marked ready.
    Otherwise, all draft PRs in the stack are marked.

    State transitions:
      - PR: draft -> open
      - Branch: reviewing -> ready
    """
    data = await self.get_stack_with_branches(stack_id)
    results: list[dict[str, Any]] = []

    for bd in data["branches"]:
        branch = bd["branch"]
        pr = bd.get("pull_request")

        # Filter to requested branches if specified
        if branch_ids and branch.id not in branch_ids:
            continue

        if pr is None or pr.external_id is None:
            continue

        # Only mark draft PRs ready
        if pr.state != "draft":
            results.append({
                "branch": branch.name,
                "action": "skipped",
                "reason": f"pr_state={pr.state}",
            })
            continue

        # Resolve repo context
        workspace = await self.workspace_service.get(self.db, branch.workspace_id)
        if workspace is None:
            continue
        owner, repo = parse_owner_repo(workspace.repo_url)

        # Mark ready on GitHub
        await github.mark_pr_ready(owner, repo, pr.external_id)

        # Transition states
        pr.transition_to("open")
        if branch.state == "reviewing":
            branch.transition_to("ready")

        results.append({
            "branch": branch.name,
            "action": "marked_ready",
            "pr_number": pr.external_id,
        })

    return {
        "stack_id": str(stack_id),
        "results": results,
    }
```

---

## Phase 4: StackAPI Facade Operations

### Goal

Add `push_stack`, `submit_stack`, and `ready_stack` methods to the `StackAPI` facade.

### File: `app/backend/src/molecules/apis/stack_api.py`

```python
async def push_stack(
    self,
    stack_id: UUID,
    workspace_id: UUID,
    branches_data: list[dict[str, object]],
) -> dict[str, Any]:
    """Push: sync and transition branches to pushed state."""
    result = await self.entity.push_stack(stack_id, workspace_id, branches_data)
    await self.db.commit()

    # Serialize
    serialized_branches: list[dict[str, Any]] = []
    for br in result["branches"]:
        branch_resp = BranchResponse.model_validate(br["branch"]).model_dump()
        pr_resp = (
            PullRequestResponse.model_validate(br["pull_request"]).model_dump()
            if br["pull_request"]
            else None
        )
        serialized_branches.append({"branch": branch_resp, "pull_request": pr_resp})

    await publish(
        DomainEvent(
            topic=STACK_PUSHED,
            entity_type="stack",
            entity_id=stack_id,
            source="user_action",
            payload={
                "synced_count": result["synced_count"],
                "created_count": result["created_count"],
            },
        )
    )

    return {
        "stack_id": str(stack_id),
        "branches": serialized_branches,
        "synced_count": result["synced_count"],
        "created_count": result["created_count"],
    }


async def submit_stack(self, stack_id: UUID) -> dict[str, Any]:
    """Submit: create GitHub draft PRs for all pushed branches."""
    if self.github is None:
        raise RuntimeError("GitHubAdapter not configured")
    result = await self.entity.submit_stack(stack_id, self.github)
    await self.db.commit()

    await publish(
        DomainEvent(
            topic=STACK_SUBMITTED,
            entity_type="stack",
            entity_id=stack_id,
            source="user_action",
            payload={"results": result["results"]},
        )
    )

    return result


async def ready_stack(
    self,
    stack_id: UUID,
    *,
    branch_ids: list[UUID] | None = None,
) -> dict[str, Any]:
    """Ready: mark draft PRs as ready for review."""
    if self.github is None:
        raise RuntimeError("GitHubAdapter not configured")
    result = await self.entity.ready_stack(
        stack_id, self.github, branch_ids=branch_ids
    )
    await self.db.commit()

    await publish(
        DomainEvent(
            topic=STACK_MARKED_READY,
            entity_type="stack",
            entity_id=stack_id,
            source="user_action",
            payload={"results": result["results"]},
        )
    )

    return result
```

---

## Phase 5: REST API Endpoints

### Goal

Add three new endpoints to the stacks router for push, submit, and ready operations.

### File: `app/backend/src/organisms/api/routers/stacks.py`

**New request schemas:**

```python
class PushStackRequest(BaseModel):
    """Request body for stack push. Sent by the Go CLI after local git operations."""
    workspace_id: UUID
    branches: list[BranchSyncItem]


class ReadyStackRequest(BaseModel):
    """Optional: specify which branches to mark ready. If empty, marks all."""
    branch_ids: list[UUID] | None = None
```

**New endpoints:**

```python
@router.post("/{stack_id}/push")
async def push_stack(
    stack_id: UUID,
    data: PushStackRequest,
    api: UserStackAPIDep,
) -> dict[str, object]:
    """Push local branch state to the private workspace.

    Called by the Go CLI after `git push`. Syncs branch names, positions,
    and head SHAs to Postgres. Transitions branches to 'pushed' state.

    CLI equivalent: `sb stack push`
    """
    branches = [b.model_dump() for b in data.branches]
    return await api.push_stack(stack_id, data.workspace_id, branches)


@router.post("/{stack_id}/submit")
async def submit_stack(
    stack_id: UUID,
    api: UserStackAPIDep,
) -> dict[str, object]:
    """Submit: create GitHub draft PRs for pushed branches.

    Creates draft pull requests on GitHub for each branch that has been
    pushed but does not yet have a PR. Uses the authenticated user's
    GitHub token.

    CLI equivalent: `sb stack submit`
    """
    return await api.submit_stack(stack_id)


@router.post("/{stack_id}/ready")
async def ready_stack(
    stack_id: UUID,
    data: ReadyStackRequest | None = None,
    api: UserStackAPIDep,
) -> dict[str, object]:
    """Ready: mark draft PRs as ready for review on GitHub.

    Removes draft status from pull requests, making them visible to
    reviewers. Optionally specify branch_ids to mark only specific
    branches ready.

    CLI equivalent: `sb stack ready`
    """
    branch_ids = data.branch_ids if data else None
    return await api.ready_stack(stack_id, branch_ids=branch_ids)
```

**Update existing `merge_stack` and `sync_stack` to use `UserStackAPIDep`:**

The merge endpoint already calls `github.merge_pr` and `github.mark_pr_ready` which require write access. Switch its dependency from `StackAPIDep` to `UserStackAPIDep`.

### API Contracts

**POST /api/v1/stacks/{stack_id}/push**

Request:
```json
{
  "workspace_id": "uuid",
  "branches": [
    {
      "name": "dug/feature/1-api-endpoint",
      "position": 1,
      "head_sha": "abc123def456...",
      "pr_number": null,
      "pr_url": null
    },
    {
      "name": "dug/feature/2-ui-component",
      "position": 2,
      "head_sha": "def456abc789...",
      "pr_number": null,
      "pr_url": null
    }
  ]
}
```

Response (200):
```json
{
  "stack_id": "uuid",
  "branches": [
    {
      "branch": { "id": "uuid", "name": "...", "state": "pushed", "head_sha": "..." },
      "pull_request": null
    }
  ],
  "synced_count": 0,
  "created_count": 2
}
```

**POST /api/v1/stacks/{stack_id}/submit**

Request: empty body (stack_id in URL, token in auth header)

Response (200):
```json
{
  "stack_id": "uuid",
  "results": [
    {
      "branch": "dug/feature/1-api-endpoint",
      "action": "created",
      "pr_number": 42,
      "pr_url": "https://github.com/org/repo/pull/42"
    },
    {
      "branch": "dug/feature/2-ui-component",
      "action": "created",
      "pr_number": 43,
      "pr_url": "https://github.com/org/repo/pull/43"
    }
  ]
}
```

**POST /api/v1/stacks/{stack_id}/ready**

Request:
```json
{
  "branch_ids": ["uuid1", "uuid2"]
}
```
Or empty body to mark all draft PRs ready.

Response (200):
```json
{
  "stack_id": "uuid",
  "results": [
    {
      "branch": "dug/feature/1-api-endpoint",
      "action": "marked_ready",
      "pr_number": 42
    }
  ]
}
```

---

## Phase 6: Event Topics

### Goal

Register new event topics for the stack workflow operations.

### File: `app/backend/src/molecules/events/topics.py`

Add:
```python
# --- Stack workflow operations ---
STACK_PUSHED = "stack.pushed"
STACK_SUBMITTED = "stack.submitted"
STACK_MARKED_READY = "stack.marked_ready"
```

### File: `app/backend/src/molecules/events/__init__.py`

Add the new constants to `__all__` and the imports.

---

## Phase 7: Stack CLI Organism

### Goal

Create a Typer-based CLI as a backend organism. This CLI runs locally and communicates with the backend REST API over HTTP. It is **not** the Go TUI -- it is a Python CLI that wraps the REST endpoints, providing a quick local interface for developers.

Note: Per ADR-001, the primary CLI is the Go TUI (Bubble Tea). This Python CLI organism serves as (a) a development/debugging tool, (b) a scripting interface, and (c) a reference implementation showing how the REST API is consumed.

### File: `app/backend/src/organisms/cli/__init__.py`

Empty, or export the typer app.

### File: `app/backend/src/organisms/cli/stack_commands.py`

```python
"""Stack CLI commands — thin interface over REST API.

Usage:
    python -m organisms.cli.stack_commands push --stack-id <id> --workspace-id <id>
    python -m organisms.cli.stack_commands submit --stack-id <id>
    python -m organisms.cli.stack_commands ready --stack-id <id>
    python -m organisms.cli.stack_commands status --stack-id <id>
"""
import json
import subprocess
import typer
import httpx

app = typer.Typer(name="stack", help="Stack workflow commands")

DEFAULT_BASE_URL = "http://localhost:8000/api/v1"


def _get_client(token: str | None = None) -> httpx.Client:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=DEFAULT_BASE_URL, headers=headers, timeout=30.0)


def _read_local_branches(repo_path: str) -> list[dict]:
    """Read branch info from local git state.

    Calls `git` directly to get branch names and HEAD SHAs for the
    current stack. Returns data suitable for the push endpoint.
    """
    # Get the stack metadata from ~/.claude/stacks/
    # This reads the same state the `stack` CLI binary uses
    # Placeholder: In production, this parses the stack's branch list
    # from the local JSON state file
    pass


@app.command()
def status(
    stack_id: str = typer.Argument(..., help="Stack UUID"),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--url"),
    token: str = typer.Option("", "--token", envvar="SB_TOKEN"),
) -> None:
    """Show stack status from the backend."""
    client = _get_client(token or None)
    response = client.get(f"/stacks/{stack_id}/detail")
    response.raise_for_status()
    data = response.json()

    stack = data["stack"]
    typer.echo(f"Stack: {stack['name']} ({stack['state']})")
    typer.echo(f"Trunk: {stack['trunk']}")
    typer.echo()

    for i, bd in enumerate(data["branches"]):
        branch = bd["branch"]
        pr = bd.get("pull_request")
        restack = bd.get("needs_restack", False)

        status_str = branch["state"]
        if pr:
            status_str = f"{pr['state']} (PR #{pr.get('external_id', '?')})"
        if restack:
            status_str += " [needs restack]"

        typer.echo(f"  {i + 1}. {branch['name']} — {status_str}")


@app.command()
def push(
    stack_id: str = typer.Argument(..., help="Stack UUID"),
    workspace_id: str = typer.Argument(..., help="Workspace UUID"),
    branches_json: str = typer.Option(
        ..., "--branches", "-b",
        help='JSON array: [{"name": "...", "position": 1, "head_sha": "..."}]',
    ),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--url"),
    token: str = typer.Option("", "--token", envvar="SB_TOKEN"),
) -> None:
    """Push local branch state to the private workspace."""
    client = _get_client(token or None)
    branches = json.loads(branches_json)
    response = client.post(
        f"/stacks/{stack_id}/push",
        json={"workspace_id": workspace_id, "branches": branches},
    )
    response.raise_for_status()
    data = response.json()

    typer.echo(f"Pushed {data.get('created_count', 0)} new, "
               f"{data.get('synced_count', 0)} updated branches")


@app.command()
def submit(
    stack_id: str = typer.Argument(..., help="Stack UUID"),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--url"),
    token: str = typer.Option("", "--token", envvar="SB_TOKEN"),
) -> None:
    """Create GitHub draft PRs for pushed branches."""
    client = _get_client(token or None)
    response = client.post(f"/stacks/{stack_id}/submit")
    response.raise_for_status()
    data = response.json()

    for result in data.get("results", []):
        action = result["action"]
        branch = result["branch"]
        if action == "created":
            typer.echo(f"  Created PR #{result['pr_number']} for {branch}")
            typer.echo(f"    {result['pr_url']}")
        elif action == "skipped":
            reason = result.get("reason", "already has PR")
            typer.echo(f"  Skipped {branch} ({reason})")


@app.command()
def ready(
    stack_id: str = typer.Argument(..., help="Stack UUID"),
    branch_ids: list[str] = typer.Option(
        [], "--branch", "-b", help="Specific branch UUIDs (default: all)"
    ),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--url"),
    token: str = typer.Option("", "--token", envvar="SB_TOKEN"),
) -> None:
    """Mark draft PRs as ready for review."""
    client = _get_client(token or None)
    payload = {"branch_ids": branch_ids} if branch_ids else {}
    response = client.post(
        f"/stacks/{stack_id}/ready",
        json=payload if payload else None,
    )
    response.raise_for_status()
    data = response.json()

    for result in data.get("results", []):
        action = result["action"]
        branch = result["branch"]
        if action == "marked_ready":
            typer.echo(f"  Marked PR #{result['pr_number']} ready for {branch}")
        elif action == "skipped":
            typer.echo(f"  Skipped {branch} ({result.get('reason', '')})")


if __name__ == "__main__":
    app()
```

### File: `app/backend/src/organisms/cli/main.py`

Top-level CLI entry point that registers all command groups:

```python
"""Stack Bench CLI — backend organism.

Usage: python -m organisms.cli.main [COMMAND]
"""
import typer

from organisms.cli.stack_commands import app as stack_app

app = typer.Typer(name="sb", help="Stack Bench CLI")
app.add_typer(stack_app, name="stack")

if __name__ == "__main__":
    app()
```

---

## Phase 8: Frontend Project Creation Form

### Goal

Provide a minimal project creation form so users can create projects after onboarding. The current onboarding flow connects GitHub and installs the app, but does not create a project. After onboarding, the user lands in the app shell with an empty state.

### File: `app/frontend/src/pages/ProjectCreatePage.tsx`

A form with:
- Project name (text input, required)
- GitHub repo (dropdown populated from the user's GitHub repos, or text input for URL)
- Local path (text input, optional -- set by CLI if working locally)
- Submit button that POSTs to `/api/v1/projects/`

After creation, redirect to the main app view. The project is created in `setup` state, then immediately transitioned to `active` via `POST /api/v1/projects/{id}/activate`.

### File: `app/frontend/src/hooks/useCreateProject.ts`

```typescript
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";

interface CreateProjectInput {
  name: string;
  github_repo: string;
  owner_id: string;
  local_path?: string;
  description?: string;
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: CreateProjectInput) => {
      // Create project
      const project = await apiClient.post("/api/v1/projects/", input);
      // Activate immediately
      await apiClient.post(`/api/v1/projects/${project.id}/activate`);
      return project;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}
```

### File: `app/frontend/src/AppRouter.tsx`

Add route:
```typescript
<Route path="/projects/new" element={
  <ProtectedRoute>
    <ProjectCreatePage />
  </ProtectedRoute>
} />
```

### Content empty state update

The existing `ContentEmptyState` component (rendered when no stack is selected) should include a "Create Project" button that navigates to `/projects/new`.

---

## State Machine Transitions

### Branch State Machine

```
created ──push──> pushed ──submit──> reviewing ──(user marks)──> ready ──submit──> submitted ──merge──> merged
```

- `created`: Branch record exists in DB, not yet synced from local git.
- `pushed`: Branch data (name, head_sha) synced to Postgres from local git.
- `reviewing`: GitHub draft PR exists. Private workspace review in progress.
- `ready`: User has marked the branch ready for team review.
- `submitted`: PR is open (not draft) on GitHub.
- `merged`: PR merged on GitHub.

> **REVIEWER NOTE (B2):** The branch model only allows `submitted -> merged`. The existing `merge_stack` code calls `branch.transition_to("merged")` without checking branch state. Branches in `reviewing` or `ready` state would raise `InvalidStateTransitionError`. The builder must either add a multi-step transition helper or add direct transitions from `reviewing`/`ready`/`pushed` to `merged` in the branch model.

### Stack State Machine

```
draft ──push──> active ──submit──> submitted ──merge──> merged
                   |                   |
                   └──close──> closed <──┘
```

- `draft`: Stack created, no branches pushed yet.
- `active`: At least one branch has been pushed.
- `submitted`: All non-draft branches have GitHub PRs.
- `merged`: All PRs merged.
- `closed`: Stack abandoned.

### PullRequest State Machine

```
draft ──ready──> open ──approve──> approved ──merge──> merged
                   |                   |
                   └──close──> closed <──┘
                          |
                          └──reopen──> open
```

- `draft`: GitHub draft PR (not visible to reviewers).
- `open`: PR open for review.
- `approved`: At least one approval.
- `merged`: PR merged.
- `closed`: PR closed (can reopen).

### State Transition Mapping to CLI Commands

| CLI Command | Branch Transition | Stack Transition | PR Transition |
|-------------|-------------------|------------------|---------------|
| `push` | created -> pushed | draft -> active | -- |
| `submit` | pushed -> reviewing | active -> submitted | (creates as draft) |
| `ready` | reviewing -> ready | -- | draft -> open |
| `merge` | -- -> merged | submitted -> merged | open/approved -> merged |

---

## File Tree (All Changes)

```
app/backend/src/
  molecules/
    providers/
      github_adapter.py                    # MODIFY: add create_pull_request, update_pull_request
    entities/
      stack_entity.py                      # MODIFY: add push_stack, submit_stack, ready_stack
    apis/
      stack_api.py                         # MODIFY: add push_stack, submit_stack, ready_stack
    events/
      topics.py                            # MODIFY: add STACK_PUSHED, STACK_SUBMITTED, STACK_MARKED_READY
      __init__.py                          # MODIFY: export new topics
  organisms/
    api/
      dependencies.py                      # MODIFY: add UserGitHubAdapterDep, UserStackAPIDep
      routers/
        stacks.py                          # MODIFY: add push, submit, ready endpoints
    cli/
      __init__.py                          # MODIFY: export app
      stack_commands.py                    # CREATE: Typer stack commands
      main.py                              # CREATE: CLI entry point

app/frontend/src/
  pages/
    ProjectCreatePage.tsx                  # CREATE: project creation form
  hooks/
    useCreateProject.ts                    # CREATE: mutation hook
  AppRouter.tsx                            # MODIFY: add /projects/new route

app/backend/__tests__/
  molecules/
    test_github_adapter.py                 # MODIFY: add tests for create_pull_request, update_pull_request
    test_stack_entity.py                   # MODIFY: add tests for push_stack, submit_stack, ready_stack
    test_stack_api.py                      # MODIFY: add tests for new facade methods
  organisms/
    test_stack_routers.py                  # MODIFY: add tests for push, submit, ready endpoints
    test_stack_cli.py                      # CREATE: CLI command tests
```

---

## Implementation Order

1. **Phase 6: Event topics** (no dependencies, fast) — add the three new topic constants.
2. **Phase 1: GitHubAdapter write operations** — add `create_pull_request` and `update_pull_request`.
3. **Phase 2: User-scoped dependency** — add `UserGitHubAdapterDep` and `UserStackAPIDep`.
4. **Phase 3: StackEntity methods** — add `push_stack`, `submit_stack`, `ready_stack`.
5. **Phase 4: StackAPI facade** — add three facade methods that delegate to entity.
6. **Phase 5: REST endpoints** — add three router endpoints, update merge/sync to use user token.
7. **Phase 7: CLI organism** — create Typer commands (can be done in parallel with Phase 8).
8. **Phase 8: Frontend form** — create project creation page (can be done in parallel with Phase 7).
9. **Phase 9: Tests** — write tests for all phases (some can be done per-phase).

Phases 1-6 are backend-only and form the core. Phases 7-8 are interface layers and can be parallelized. Tests should be written alongside each phase but are grouped here for spec clarity.

---

## Testing Strategy

### Unit Tests (no DB required)

**`test_github_adapter.py` additions:**
- `test_create_pull_request_sends_correct_payload` — mock httpx, verify POST to `/repos/{owner}/{repo}/pulls` with draft=True
- `test_create_pull_request_returns_pr_data` — mock response, verify number/html_url extraction
- `test_create_pull_request_raises_on_error` — mock 422 response, verify GitHubAPIError
- `test_update_pull_request_sends_patch` — mock httpx, verify PATCH with base field

**`test_stack_entity.py` additions:**
- `test_push_stack_transitions_created_to_pushed` — create branch in "created" state, call push_stack, verify state is "pushed"
- `test_push_stack_activates_draft_stack` — push on a draft stack, verify stack transitions to "active"
- `test_push_stack_updates_head_sha` — push with new head_sha, verify branch.head_sha updated
- `test_submit_stack_creates_draft_prs` — mock GitHubAdapter, verify PRs created with draft=True
- `test_submit_stack_skips_branches_with_prs` — branch with existing external_id skipped
- `test_submit_stack_skips_unpushed_branches` — branch in "created" state skipped
- `test_submit_stack_transitions_branch_to_reviewing` — after submit, branch state is "reviewing"
- `test_ready_stack_marks_draft_prs_open` — mock GitHub, verify mark_pr_ready called, PR state "open"
- `test_ready_stack_skips_non_draft_prs` — PR already "open" is skipped
- `test_ready_stack_filters_by_branch_ids` — only specified branches are marked ready

**`test_stack_api.py` additions:**
- `test_push_stack_publishes_event` — verify STACK_PUSHED event published
- `test_submit_stack_publishes_event` — verify STACK_SUBMITTED event published
- `test_ready_stack_publishes_event` — verify STACK_MARKED_READY event published
- `test_submit_stack_raises_without_github` — no GitHubAdapter raises RuntimeError

### Router Tests (TestClient, mocked DB)

**`test_stack_routers.py` additions:**
- `test_push_endpoint_returns_200` — POST /stacks/{id}/push with valid body
- `test_push_endpoint_requires_auth` — no token returns 401
- `test_submit_endpoint_returns_200` — POST /stacks/{id}/submit
- `test_submit_endpoint_requires_github` — user without GitHub connection returns 403
- `test_ready_endpoint_with_branch_ids` — POST with specific branch_ids
- `test_ready_endpoint_without_body` — POST with empty body marks all ready

### CLI Tests

**`test_stack_cli.py` (new file):**
- `test_status_command_output` — mock httpx, verify formatted output
- `test_push_command_sends_correct_payload` — mock httpx, verify POST
- `test_submit_command_output` — mock httpx, verify PR creation output
- `test_ready_command_output` — mock httpx, verify ready output
- All use `typer.testing.CliRunner` for clean testing

### Integration Tests (DB required, `@pytest.mark.integration`)

- `test_push_submit_ready_lifecycle` — full lifecycle: create stack, push branches, submit (mocked GitHub), ready (mocked GitHub), verify all state transitions
- `test_push_idempotent` — pushing same branches twice updates rather than duplicates

### Test Markers

All unit tests: `@pytest.mark.unit`
All integration tests: `@pytest.mark.integration`
All CLI tests: `@pytest.mark.unit` (they mock HTTP, no DB needed)

---

## Migration Plan

No Alembic migration needed for this spec. All model changes are in existing tables with existing columns. The Project model already has `local_path` and `github_repo` fields (SB-052 was implemented). The Stack, Branch, and PullRequest tables already exist with their state machines.

If the builder discovers that the `ready` branch state transition requires a new intermediate state or the PR state machine needs adjustment, a migration may be needed to update the state column constraints. However, EventPattern stores state as a string column without DB-level constraints, so state machine changes are code-only.

---

## Key Design Decisions

### 1. User-scoped vs static GitHub token

**Decision:** Use the user's OAuth token for write operations, static token for reads.

**Why:** Creating PRs on behalf of a user requires their token (for authorship attribution and permission checking). The static `GITHUB_TOKEN` from settings is a personal access token or app token used for read operations (diffs, trees, file content) where authorship doesn't matter. The `UserGitHubAdapterDep` dependency cleanly separates these concerns.

**Alternative considered:** Always use the user's token. Rejected because read operations (viewing diffs, file trees) should work even during initial setup before GitHub is connected, using the app-level token.

### 2. Push as sync + transition (not a separate code path)

**Decision:** `push_stack` calls `sync_stack` (existing method) then adds state transitions.

**Why:** `sync_stack` already handles the complex branch creation/update logic with proper event emission. `push_stack` layers state transitions on top. This avoids code duplication and ensures sync events are always emitted.

**Alternative considered:** Separate push implementation. Rejected because it would duplicate 80% of sync_stack's logic.

### 3. CLI organism is a REST client, not direct DB access

**Decision:** The Typer CLI calls the REST API over HTTP, it does not import services directly.

**Why:** (a) Consistent behavior -- same code path whether using CLI, Go TUI, or frontend. (b) Auth is handled by the same middleware. (c) No need to manage DB connections in the CLI. (d) The Go TUI will call the same endpoints, so this validates the API surface.

**Alternative considered:** Direct service access (like the pattern-stack docs show for CLI organisms). Rejected because stack-bench's CLI is explicitly a thin HTTP client per ADR-001, and the Python CLI organism should follow the same pattern to validate the REST API.

### 4. Submit creates draft PRs only

**Decision:** `submit` always creates draft PRs. `ready` is a separate operation to remove draft status.

**Why:** The three-tier architecture (ADR-004) explicitly separates push (sync to workspace), submit (create GitHub PRs as drafts for private review), and ready (mark for team review). Creating drafts by default gives the developer a chance to review the PR descriptions and add review notes before making them visible to the team.

### 5. No new Alembic migration

**Decision:** This spec does not require a migration.

**Why:** All models (Stack, Branch, PullRequest, Project) already exist with the correct columns. State values are stored as strings in a `state` VARCHAR column without database-level constraints -- the state machine is enforced by the EventPattern Python class. New state transitions are code-only changes.

---

## Open Questions

1. **PR title generation** -- Currently using branch name as PR title. Should we generate better titles from commit messages? (Deferred to a future spec.)

2. **PR description template** -- Should `submit` accept a description template that gets applied to all PRs? (Deferred to a future spec. The `review_notes` field exists for private notes.)

3. **Selective push** -- ADR-004 mentions `sb stack push 1 3 5` to push specific branches by position. The current `push_stack` pushes all branches in the request. Selective push is handled by the client (CLI sends only the branches to push). No backend change needed.

4. **Error handling on partial submit** -- If GitHub PR creation fails for branch 3 of 5, should branches 1-2 be committed? Current implementation: yes, partial success is committed. The response includes per-branch results so the client can retry.

---

## Validator Review (2026-04-03)

### BLOCKERS

**B1: `mark_pr_ready` uses REST API but GitHub requires GraphQL to remove draft status.**

The existing `GitHubAdapter.mark_pr_ready` at `app/backend/src/molecules/providers/github_adapter.py:476` uses `PATCH /repos/{owner}/{repo}/pulls/{pr_number}` with `{"draft": false}`. GitHub REST API v3 does NOT support removing draft status via PATCH -- this requires the GraphQL mutation `markPullRequestReadyForReview`. The REST PATCH only supports setting `draft: true`.

This is a pre-existing bug but `ready_stack` is the primary feature that exercises it. Phase 1 should include rewriting `mark_pr_ready` to use the GraphQL API, or this must be called out as a prerequisite fix.

**B2: Branch state machine does not allow `merged` from all states where `merge_stack` attempts it.**

The branch model (`app/backend/src/features/branches/models.py:16-23`) only permits `submitted -> merged`. The existing `merge_stack` code (`stack_api.py:286`) calls `branch.transition_to("merged")` without ensuring the branch is in `submitted` state. Branches in `reviewing` or `ready` state would raise `InvalidStateTransitionError`.

The builder must either: (a) add a multi-step transition helper that walks `reviewing -> ready -> submitted -> merged`, or (b) add direct transitions from `reviewing`/`ready` to `merged` in the branch model.

### CONCERNS

**C1: Frontend `useCreateProject` should use generated `projectApi` client.** The spec uses raw `apiClient.post("/api/v1/projects/", ...)` but `app/frontend/src/generated/api/project.ts` already provides `projectApi.create()`. Use the generated client for consistency.

**C2: Generated `projectApi.transition()` calls `/transition` endpoint which does not exist.** The actual backend endpoint is `POST /projects/{id}/activate` (at `app/backend/src/organisms/api/routers/projects.py:45`). The frontend hook should call `/activate` directly, not the generated `transition` method.

**C3: `submit_stack` "all_submitted" check (Phase 3 lines 362-373) cross-references results list against the original branch_list which has stale PR data.** The newly created PRs exist only in the session, not in the original `branch_list` dicts. Consider re-querying or using a simpler count-based approach after the loop.

**C4: `merge_stack` and `sync_stack` must be migrated to `UserStackAPIDep`.** The spec mentions this (line 628-630) but only in passing. The builder should explicitly update `stacks.py:139` (`merge_stack`) and `stacks.py:125` (`sync_stack`) to use `UserStackAPIDep`.

**C5: `ready` endpoint body `ReadyStackRequest | None = None` may cause OpenAPI schema issues.** Consider always requiring a body with `branch_ids: list[UUID] | None = None` inside it, or use a `Body(None)` annotation.

**C6: `submit_stack` entity method lacks try/except around `github.create_pull_request`.** If GitHub returns 422 (e.g., PR already exists for that head/base), the entire operation fails. Per-branch error handling with result status would support the partial-success design described in Open Question 4.

**C7: CLI organism uses sync httpx. This is correct for Typer but should be noted as intentional.**

### SUGGESTIONS

- S1: The `_read_local_branches` helper in Phase 7 is a `pass` stub. Consider removing it or marking it clearly as not-implemented since the CLI is a REST client, not a git reader.
- S2: Verify `@tanstack/react-query` is in `app/frontend/package.json` before Phase 8.
- S3: Consider adding retry guidance for partial submit failures in the CLI output (Phase 7 `submit` command).

### Recommendation

**REQUEST_CHANGES** -- Fix B1 (mark_pr_ready GraphQL) and B2 (branch merge transition path) before building. Both are pre-existing issues that this spec's features will expose. The spec should either include fixes or explicitly add them as prerequisite tasks.
