---
title: "SB-062: st push -- push branches and sync stack state to backend"
date: 2026-03-24
status: draft
branch: null
depends_on: []
adrs: []
---

# SB-062: `st push` -- Push Branches and Sync Stack State to Backend

## Goal

Add an `st push` command to the stack CLI that (1) pushes git branches to GitHub via `git push`, then (2) reads the local stack state from `~/.claude/stacks/<repo>.json` and POSTs branch SHAs + PR numbers to the Stack Bench backend `/api/v1/stacks/{id}/sync` endpoint. This bridges the local git tool and the backend database, keeping branch SHAs and PR links in sync after every push. The backend sync call is best-effort: push succeeds even if the backend is unreachable.

## Context

Currently `st submit` handles pushing AND PR creation/updating as a single operation. The new `st push` command provides a lighter-weight operation: just push branches and sync metadata to the backend without creating or modifying PRs. This is the primary bridge between local git state and the Stack Bench backend (see remote-first architecture).

The backend already has the sync endpoint (`POST /stacks/{stack_id}/sync`) and `StackEntity.sync_stack()` method fully implemented. The work is primarily on the CLI side (new command) plus wiring the CLI to call the backend after push.

## Existing Architecture

### Backend (already complete)

- **Router**: `POST /stacks/{stack_id}/sync` in `organisms/api/routers/stacks.py` (line 113)
- **Request schema**: `SyncStackRequest` with `workspace_id` + list of `BranchSyncItem`
- **Entity**: `StackEntity.sync_stack()` in `molecules/entities/stack_entity.py` (line 218)
  - Creates or updates branches by name
  - Links PRs when `pr_number` is provided
  - Returns `synced_count` / `created_count`
- **API facade**: `StackAPI.sync_stack()` commits the transaction
- **Tests**: Full unit test coverage in `__tests__/molecules/test_stack_sync.py`

### Stack CLI (dugshub/stack)

- Commands auto-discovered from `src/commands/` directory
- State file: `~/.claude/stacks/<repo>.json` (StackFile type)
- Branch shape: `{ name, tip, pr, parentTip }` where `tip` is the HEAD SHA and `pr` is the GitHub PR number
- `submit.ts` already implements parallel push via `git.pushParallel()`
- No `push.ts` command exists yet

### Stack State File Format

```typescript
interface StackFile {
  repo: string;              // "owner/repo"
  stacks: Record<string, Stack>;
  currentStack: string | null;
}

interface Stack {
  trunk: string;
  branches: Branch[];
  created: string;
  updated: string;
}

interface Branch {
  name: string;
  tip: string | null;     // HEAD SHA
  pr: number | null;       // GitHub PR number
  parentTip: string | null;
}
```

## File Tree

```
# Stack CLI (dugshub/stack repo -- installed at ~/.bun/install/global/node_modules/@pattern-stack/stack/)
src/commands/push.ts                    # NEW -- st push command
src/lib/backend.ts                      # NEW -- backend HTTP client for sync calls

# Stack Bench backend (this repo)
app/backend/src/organisms/api/routers/stacks.py     # MODIFY -- add SyncStackResponse model
app/backend/src/molecules/apis/stack_api.py          # MODIFY -- serialize sync response
app/backend/__tests__/organisms/test_push_sync.py    # NEW -- integration test

# No model/service/entity changes needed -- sync endpoint already exists
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Backend: typed response model for sync endpoint | -- |
| 2 | CLI: backend HTTP client (`backend.ts`) | -- |
| 3 | CLI: `st push` command (`push.ts`) | Phase 2 |
| 4 | Integration test: push -> sync -> DB state verification | Phases 1, 3 |

## Phase Details

### Phase 1: Backend -- Typed Sync Response

The sync endpoint currently returns `dict[str, object]`. Add a proper Pydantic response model.

**File**: `app/backend/src/organisms/api/routers/stacks.py`

Add response model:

```python
class SyncBranchResult(BaseModel):
    branch: dict
    pull_request: dict | None

class SyncStackResponse(BaseModel):
    stack_id: str
    synced_count: int
    created_count: int
    branches: list[SyncBranchResult]
```

Update the endpoint signature:

```python
@router.post("/{stack_id}/sync", response_model=SyncStackResponse)
async def sync_stack(stack_id: UUID, data: SyncStackRequest, api: StackAPIDep) -> dict[str, object]:
```

**File**: `app/backend/src/molecules/apis/stack_api.py`

Modify `sync_stack()` to include `stack_id` and serialize branch results:

```python
async def sync_stack(self, stack_id, workspace_id, branches_data):
    result = await self.entity.sync_stack(stack_id, workspace_id, branches_data)
    await self.db.commit()

    serialized_branches = []
    for br in result["branches"]:
        branch_resp = BranchResponse.model_validate(br["branch"]).model_dump()
        pr_resp = (
            PullRequestResponse.model_validate(br["pull_request"]).model_dump()
            if br["pull_request"]
            else None
        )
        serialized_branches.append({"branch": branch_resp, "pull_request": pr_resp})

    return {
        "stack_id": str(stack_id),
        "branches": serialized_branches,
        "synced_count": result["synced_count"],
        "created_count": result["created_count"],
    }
```

### Phase 2: CLI -- Backend HTTP Client

**File**: `src/lib/backend.ts` (NEW)

A minimal HTTP client that calls the Stack Bench backend API. Reads the backend URL from daemon config or environment variable.

```typescript
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

export interface SyncBranch {
  name: string;
  position: number;
  head_sha: string | null;
  pr_number: number | null;
  pr_url: string | null;
}

export interface SyncRequest {
  workspace_id: string;
  branches: SyncBranch[];
}

export interface SyncResponse {
  stack_id: string;
  synced_count: number;
  created_count: number;
  branches: Array<{ branch: object; pull_request: object | null }>;
}

export function getBackendUrl(): string | null {
  // 1. Env var override
  if (process.env.STACK_BENCH_URL) return process.env.STACK_BENCH_URL;
  // 2. Daemon config
  try {
    const configPath = join(homedir(), '.claude', 'stacks', 'server.config.json');
    const config = JSON.parse(readFileSync(configPath, 'utf-8'));
    return config.url ?? null;
  } catch {
    return null;
  }
}

export async function syncStack(
  stackId: string,
  request: SyncRequest,
): Promise<SyncResponse | null> {
  const url = getBackendUrl();
  if (!url) return null;

  try {
    const resp = await fetch(`${url}/api/v1/stacks/${stackId}/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(10_000),
    });
    if (!resp.ok) return null;
    return (await resp.json()) as SyncResponse;
  } catch {
    return null;  // Graceful degradation
  }
}
```

Key design decisions:
- Returns `null` on any failure (graceful degradation per AC)
- 10-second timeout prevents blocking
- Backend URL from daemon config or `STACK_BENCH_URL` env var
- No retry logic -- push already succeeded, sync is best-effort

### Phase 3: CLI -- `st push` Command

**File**: `src/commands/push.ts` (NEW)

```typescript
import { Command, Option } from 'clipanion';
import * as git from '../lib/git.js';
import { syncStack, type SyncBranch } from '../lib/backend.js';
import { resolveStack } from '../lib/resolve.js';
import { loadAndRefreshState, saveState } from '../lib/state.js';
import { saveSnapshot } from '../lib/undo.js';
import { theme } from '../lib/theme.js';
import * as ui from '../lib/ui.js';

export class PushCommand extends Command {
  static override paths = [['push'], ['stack', 'push']];

  static override usage = Command.Usage({
    description: 'Push branches to remote and sync state to Stack Bench',
    examples: [
      ['Push all branches in current stack', 'st push'],
      ['Push only branch at position 2', 'st push --branch 2'],
      ['Dry run', 'st push --dry-run'],
    ],
  });

  stackName = Option.String('--stack,-s', {
    description: 'Target stack by name',
  });

  branch = Option.String('--branch,-b', {
    description: 'Push only the branch at this position (1-indexed)',
  });

  dryRun = Option.Boolean('--dry-run', false, {
    description: 'Show what would happen without pushing',
  });

  async execute(): Promise<number> {
    const state = loadAndRefreshState();

    let resolved;
    try {
      resolved = await resolveStack({ state, explicitName: this.stackName });
    } catch (err) {
      ui.error(err instanceof Error ? err.message : String(err));
      return 2;
    }

    const { stackName: resolvedName, stack, position } = resolved;
    const originalBranch = position ? git.currentBranch() : null;

    // Filter branches if --branch specified
    let branchesToPush = stack.branches;
    if (this.branch) {
      const pos = parseInt(this.branch, 10);
      if (isNaN(pos) || pos < 1 || pos > stack.branches.length) {
        ui.error(
          `Invalid branch position: ${this.branch} (stack has ${stack.branches.length} branches)`,
        );
        return 2;
      }
      branchesToPush = [stack.branches[pos - 1]!];
    }

    // Dry run
    if (this.dryRun) {
      ui.heading(`\nWould push ${branchesToPush.length} branch(es):\n`);
      for (const b of branchesToPush) {
        const needs = git.needsPush(b.name);
        ui.info(`  ${theme.branch(b.name)} (${needs ? 'needs push' : 'up to date'})`);
      }
      return 0;
    }

    // --- Phase 1: Git Push ---
    saveSnapshot('push');
    ui.heading('\nPushing branches...');

    const pushPlans: git.PushPlan[] = [];
    const upToDate: string[] = [];

    for (const b of branchesToPush) {
      if (!git.needsPush(b.name)) {
        upToDate.push(b.name);
        continue;
      }
      pushPlans.push({
        branch: b.name,
        mode: git.hasRemoteRef(b.name) ? 'force-with-lease' : 'new',
      });
    }

    for (const name of upToDate) {
      ui.info(`  ${theme.branch(name)} (up to date)`);
    }

    if (pushPlans.length > 0) {
      const results = await git.pushParallel('origin', pushPlans);
      for (const result of results) {
        if (result.ok) {
          const plan = pushPlans.find((p) => p.branch === result.branch);
          const suffix = plan?.mode === 'new' ? ' (new)' : '';
          ui.success(`Pushed ${theme.branch(result.branch)}${suffix}`);
        } else {
          ui.error(`Push failed: ${theme.branch(result.branch)}: ${result.error ?? 'unknown'}`);
          return 2;
        }
      }
    }

    // Update tips in state
    for (const b of branchesToPush) {
      b.tip = git.revParse(b.name);
    }
    stack.updated = new Date().toISOString();
    saveState(state);

    // --- Phase 2: Backend Sync (best-effort) ---
    const backendStackId = stack.backendId;  // See Open Question 1
    if (backendStackId) {
      const syncBranches: SyncBranch[] = stack.branches.map((b, i) => ({
        name: b.name,
        position: i + 1,
        head_sha: b.tip,
        pr_number: b.pr,
        pr_url: b.pr ? `https://github.com/${state.repo}/pull/${b.pr}` : null,
      }));

      const syncResult = await syncStack(backendStackId, {
        workspace_id: /* from daemon config */,
        branches: syncBranches,
      });

      if (syncResult) {
        ui.success(`Synced ${syncResult.synced_count} updated, ${syncResult.created_count} created`);
      } else {
        ui.warn('Backend sync skipped (unreachable or not configured)');
      }
    }

    // Restore original branch
    if (originalBranch) {
      try { git.checkout(originalBranch); } catch { /* non-fatal */ }
    }

    ui.success(`\nPushed ${branchesToPush.length} branch(es) in stack ${theme.stack(resolvedName)}`);
    return 0;
  }
}
```

### Phase 4: Integration Test

**File**: `app/backend/__tests__/organisms/test_push_sync.py` (NEW)

Tests the full HTTP flow: POST /sync -> DB verification.

```python
"""Integration test: push -> sync -> DB state verification.

Simulates what happens when st push calls POST /stacks/{id}/sync.
"""

import pytest
from httpx import AsyncClient

@pytest.mark.integration
async def test_push_sync_creates_branches_and_links_prs(client, seeded_stack):
    """Full flow: sync with branch + PR data, verify DB state."""
    stack_id = seeded_stack["stack_id"]
    workspace_id = seeded_stack["workspace_id"]

    resp = await client.post(
        f"/api/v1/stacks/{stack_id}/sync",
        json={
            "workspace_id": str(workspace_id),
            "branches": [
                {
                    "name": "user/my-stack/1-feature-a",
                    "position": 1,
                    "head_sha": "a" * 40,
                    "pr_number": 101,
                    "pr_url": "https://github.com/owner/repo/pull/101",
                },
                {
                    "name": "user/my-stack/2-feature-b",
                    "position": 2,
                    "head_sha": "b" * 40,
                    "pr_number": 102,
                    "pr_url": "https://github.com/owner/repo/pull/102",
                },
            ],
        },
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["created_count"] == 2
    assert result["synced_count"] == 0

    # Verify via detail endpoint
    detail = await client.get(f"/api/v1/stacks/{stack_id}/detail")
    assert detail.status_code == 200
    branches = detail.json()["branches"]
    assert len(branches) == 2
    assert branches[0]["branch"]["head_sha"] == "a" * 40
    assert branches[0]["pull_request"]["external_id"] == 101


@pytest.mark.integration
async def test_push_sync_updates_existing_shas(client, seeded_stack):
    """Second push updates SHAs without creating new branches."""
    stack_id = seeded_stack["stack_id"]
    workspace_id = seeded_stack["workspace_id"]

    initial = {
        "workspace_id": str(workspace_id),
        "branches": [{"name": "user/stack/1-feat", "position": 1, "head_sha": "a" * 40}],
    }
    await client.post(f"/api/v1/stacks/{stack_id}/sync", json=initial)

    updated = {
        "workspace_id": str(workspace_id),
        "branches": [{"name": "user/stack/1-feat", "position": 1, "head_sha": "c" * 40}],
    }
    resp = await client.post(f"/api/v1/stacks/{stack_id}/sync", json=updated)
    result = resp.json()
    assert result["synced_count"] == 1
    assert result["created_count"] == 0


@pytest.mark.integration
async def test_push_sync_idempotent(client, seeded_stack):
    """Same data twice: second call updates, not creates."""
    stack_id = seeded_stack["stack_id"]
    workspace_id = seeded_stack["workspace_id"]

    data = {
        "workspace_id": str(workspace_id),
        "branches": [{"name": "user/stack/1-feat", "position": 1, "head_sha": "d" * 40}],
    }
    await client.post(f"/api/v1/stacks/{stack_id}/sync", json=data)
    resp2 = await client.post(f"/api/v1/stacks/{stack_id}/sync", json=data)
    assert resp2.json()["synced_count"] == 1
    assert resp2.json()["created_count"] == 0
```

## Schema Definitions

### Existing (no changes needed)

- `BranchSyncItem` -- request item for each branch (already in stacks router)
- `SyncStackRequest` -- wraps workspace_id + list of BranchSyncItem (already in stacks router)
- `BranchCreate`, `BranchUpdate` -- feature-level schemas (already exist)
- `PullRequestCreate`, `PullRequestUpdate` -- feature-level schemas (already exist)

### New

- `SyncStackResponse` -- response model for the sync endpoint (router-level)
- `SyncBranchResult` -- individual branch result within the response (router-level)

## API Endpoint Details

### `POST /api/v1/stacks/{stack_id}/sync`

Already implemented. Enhancement: typed response model + stack_id in response body.

| Field | Value |
|-------|-------|
| Method | POST |
| Path | `/api/v1/stacks/{stack_id}/sync` |
| Request Body | `SyncStackRequest` |
| Response Body | `SyncStackResponse` |
| Auth | None (pre-auth) |
| Idempotent | Yes (same input -> same state) |

## Pattern Stack Patterns Used

- No new features, entities, or molecules needed
- Existing `StackEntity.sync_stack()` handles all reconciliation logic
- Existing `BranchService.get_by_name()` enables upsert-by-name pattern
- Router-level response model is the only backend addition

## Open Questions

1. **Stack ID mapping**: The CLI knows stack names but the backend uses UUIDs. How does the CLI discover its backend stack UUID?
   - **Option A** (recommended): Store `backendId` in the StackFile's Stack object after first sync. On first `st push`, call a lookup-or-create endpoint, then persist the UUID locally.
   - **Option B**: Add `GET /api/v1/stacks/by-name?name={name}&repo={repo}` endpoint.
   - **Option C**: Use daemon RPC which already knows the workspace.

2. **Workspace ID**: The sync endpoint requires `workspace_id`. Where does the CLI get this?
   - The daemon config at `~/.claude/stacks/server.config.json` likely has this.
   - Alternatively, store it in the StackFile after backend registration.
   - **Recommendation**: Read from daemon config; fall back to env var `STACK_BENCH_WORKSPACE_ID`.

3. **Cross-repo coordination**: CLI changes go in `dugshub/stack` repo, backend changes in this repo. PRs should be coordinated. Backend changes can land first since the sync endpoint already works.

## Dependencies

- Backend: No new Python dependencies
- CLI: No new npm dependencies (uses built-in `fetch`)
- `@pattern-stack/stack` package must be updated and republished

## Test Strategy

| Layer | Test File | What |
|-------|-----------|------|
| Unit (existing) | `test_stack_sync.py` | StackEntity.sync_stack, StackAPI.sync_stack |
| Integration (new) | `test_push_sync.py` | Full HTTP: POST /sync -> DB verification |
| CLI unit (new, stack repo) | `push.test.ts` | PushCommand with mocked git + backend |
| E2E (manual) | -- | `st push` in a real repo with backend running |
