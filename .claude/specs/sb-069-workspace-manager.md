---
title: "SB-069: WorkspaceManager Molecule + Container Image"
date: 2026-03-25
status: draft
issue: SB-069
epic: EP-011
depends_on: [SB-068]
---

# SB-069: WorkspaceManager Molecule + Container Image

## Goal

Create a WorkspaceManager molecule that composes WorkspaceService + GCP API calls for cloud lifecycle management (provision, teardown, stop, get_status). Also create a workspace container Dockerfile and a lightweight workspace-server (FastAPI) that runs inside the container to expose file, git, worktree, and terminal operations.

## Architecture Overview

```
Organism layer (SB-070)
    |
    v
WorkspaceManager (molecule/services)
    |
    ├── WorkspaceService (feature) -- DB state transitions
    ├── GCPClient (protocol)       -- Cloud Run + GCS operations
    └── Settings (config)          -- GCP project, region, image path
```

The WorkspaceManager follows the molecule pattern: it composes the WorkspaceService feature with an external GCP client abstraction. The GCP client uses a Protocol for testability -- unit tests inject a mock, production uses the real `google-cloud` SDK implementation.

---

## 1. GCP Client Abstraction

### Protocol

```python
# app/backend/src/molecules/services/gcp_client.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class CloudRunServiceInfo:
    """Returned after deploying or querying a Cloud Run service."""
    name: str           # e.g. "ws-a1b2c3d4"
    url: str            # e.g. "https://ws-a1b2c3d4-xyz.a.run.app"
    region: str
    status: str         # "READY", "DEPLOYING", "NOT_FOUND", etc.
    revision: str | None = None


@dataclass
class GCSBucketInfo:
    """Returned after creating or querying a GCS bucket."""
    name: str           # e.g. "stack-bench-ws-a1b2c3d4-e5f6g7h8"
    location: str       # e.g. "northamerica-northeast2"
    exists: bool = True


@dataclass
class ResourceProfileConfig:
    """Cloud Run resource limits per profile."""
    cpu: str            # e.g. "1", "2", "4"
    memory: str         # e.g. "512Mi", "1Gi", "2Gi"
    max_instances: int  # e.g. 1, 2, 4
    timeout_seconds: int = 300

    @classmethod
    def from_profile(cls, profile: str) -> ResourceProfileConfig:
        profiles = {
            "light": cls(cpu="1", memory="512Mi", max_instances=1, timeout_seconds=300),
            "standard": cls(cpu="2", memory="1Gi", max_instances=1, timeout_seconds=600),
            "heavy": cls(cpu="4", memory="2Gi", max_instances=2, timeout_seconds=900),
        }
        if profile not in profiles:
            raise ValueError(f"Unknown resource profile: {profile}. Must be one of: {list(profiles.keys())}")
        return profiles[profile]


class GCPClientProtocol(Protocol):
    """Protocol for GCP operations. Mocked in tests."""

    async def create_gcs_bucket(
        self,
        bucket_name: str,
        region: str,
    ) -> GCSBucketInfo: ...

    async def delete_gcs_bucket(
        self,
        bucket_name: str,
    ) -> None: ...

    async def bucket_exists(
        self,
        bucket_name: str,
    ) -> bool: ...

    async def deploy_cloud_run_service(
        self,
        service_name: str,
        image: str,
        region: str,
        env_vars: dict[str, str],
        resources: ResourceProfileConfig,
        gcs_bucket: str | None = None,
    ) -> CloudRunServiceInfo: ...

    async def delete_cloud_run_service(
        self,
        service_name: str,
        region: str,
    ) -> None: ...

    async def get_cloud_run_service(
        self,
        service_name: str,
        region: str,
    ) -> CloudRunServiceInfo | None: ...

    async def scale_cloud_run_service(
        self,
        service_name: str,
        region: str,
        min_instances: int,
        max_instances: int,
    ) -> None: ...
```

### Production Implementation

```python
# app/backend/src/molecules/services/gcp_client.py (same file, below protocol)

from google.cloud import run_v2, storage


class GCPClient:
    """Production GCP client using google-cloud SDK.

    Uses async wrappers around the sync SDK via asyncio.to_thread.
    """

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    async def create_gcs_bucket(self, bucket_name: str, region: str) -> GCSBucketInfo:
        def _create():
            client = storage.Client(project=self.project_id)
            bucket = client.bucket(bucket_name)
            bucket.storage_class = "STANDARD"
            client.create_bucket(bucket, location=region)
            return GCSBucketInfo(name=bucket_name, location=region)
        return await asyncio.to_thread(_create)

    async def delete_gcs_bucket(self, bucket_name: str) -> None:
        def _delete():
            client = storage.Client(project=self.project_id)
            bucket = client.bucket(bucket_name)
            bucket.delete(force=True)
        await asyncio.to_thread(_delete)

    async def bucket_exists(self, bucket_name: str) -> bool:
        def _exists():
            client = storage.Client(project=self.project_id)
            return client.bucket(bucket_name).exists()
        return await asyncio.to_thread(_exists)

    async def deploy_cloud_run_service(
        self,
        service_name: str,
        image: str,
        region: str,
        env_vars: dict[str, str],
        resources: ResourceProfileConfig,
        gcs_bucket: str | None = None,
    ) -> CloudRunServiceInfo:
        """Deploy or update a Cloud Run service.

        Uses the Cloud Run Admin v2 API. Sets:
        - Container image from Artifact Registry
        - Environment variables (REPO_URL, DEFAULT_BRANCH, etc.)
        - CPU/memory from resource profile
        - GCS volume mount if gcs_bucket provided
        - min_instances=0 for scale-to-zero
        """
        # Implementation uses google.cloud.run_v2.ServicesAsyncClient
        # to create or update the service. Wrapped in asyncio.to_thread
        # if sync client is used instead.
        ...

    async def delete_cloud_run_service(self, service_name: str, region: str) -> None:
        ...

    async def get_cloud_run_service(self, service_name: str, region: str) -> CloudRunServiceInfo | None:
        ...

    async def scale_cloud_run_service(
        self, service_name: str, region: str, min_instances: int, max_instances: int,
    ) -> None:
        """Update scaling config. min=0, max=0 effectively stops the service."""
        ...
```

### Design Decisions

1. **Protocol + concrete class in same file.** The protocol is small enough that splitting into two files adds overhead without benefit. Tests import just the protocol and dataclasses.

2. **`asyncio.to_thread` for sync SDK.** The google-cloud Python SDK is synchronous. Wrapping in `to_thread` avoids blocking the event loop. If/when Google ships async clients, swap the internals without changing the interface.

3. **`ResourceProfileConfig.from_profile()` class method.** Keeps resource mapping close to the data class. The WorkspaceManager calls this with `workspace.resource_profile`.

---

## 2. Configuration / Settings

Add GCP-specific settings to `AppSettings`:

```python
# app/backend/src/config/settings.py (additions)

class AppSettings(BaseSettings):
    # ... existing fields ...

    # GCP Workspace provisioning
    GCP_PROJECT_ID: str = Field(default="stack-bench")
    GCP_REGION: str = Field(default="northamerica-northeast2")
    GCP_WORKSPACE_IMAGE: str = Field(
        default="northamerica-northeast2-docker.pkg.dev/stack-bench/workspace/workspace-server:latest"
    )
    GCP_SERVICE_ACCOUNT_EMAIL: str = Field(default="")  # for Cloud Run service identity
```

These are all overridable via environment variables in production.

---

## 3. WorkspaceManager

```python
# app/backend/src/molecules/services/workspace_manager.py

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from config.settings import get_settings
from features.workspaces.service import WorkspaceService
from molecules.exceptions import (
    MoleculeError,
    WorkspaceNotFoundError,
    WorkspaceProvisionError,
)
from molecules.services.gcp_client import (
    GCPClientProtocol,
    ResourceProfileConfig,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from features.workspaces.models import Workspace

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages workspace cloud lifecycle: provision, teardown, stop, status.

    Composes WorkspaceService (feature-layer DB ops) with GCPClient
    (cloud infrastructure ops). All state transitions go through
    WorkspaceService; all cloud calls go through GCPClient.
    """

    def __init__(
        self,
        db: AsyncSession,
        gcp_client: GCPClientProtocol,
    ) -> None:
        self.db = db
        self.gcp_client = gcp_client
        self.workspace_service = WorkspaceService()
        self._settings = get_settings()

    # --- Naming helpers ---

    @staticmethod
    def _service_name(workspace_id: UUID) -> str:
        """Cloud Run service name: ws-{first 8 chars of workspace_id}."""
        return f"ws-{str(workspace_id)[:8]}"

    @staticmethod
    def _bucket_name(project_id: UUID, workspace_id: UUID) -> str:
        """GCS bucket name: stack-bench-ws-{project_id[:8]}-{workspace_id[:8]}."""
        return f"stack-bench-ws-{str(project_id)[:8]}-{str(workspace_id)[:8]}"

    # --- Lifecycle operations ---

    async def provision(self, workspace_id: UUID) -> Workspace:
        """Provision cloud resources for a workspace.

        Flow:
        1. Load workspace, validate state allows provisioning
        2. Transition to "provisioning"
        3. Create GCS bucket (skip if re-provisioning and bucket exists)
        4. Deploy Cloud Run service with workspace image
        5. Store cloud resource names/URLs on workspace
        6. Transition to "ready"

        On failure at any GCP step:
        - Transition back to previous state ("created" or "stopped")
        - Log the error with full context
        - Raise WorkspaceProvisionError
        """
        workspace = await self._get_workspace(workspace_id)
        previous_state = workspace.state  # "created" or "stopped"

        # Step 1: Transition to provisioning
        workspace.transition_to("provisioning")
        await self.db.flush()

        service_name = self._service_name(workspace_id)
        bucket_name = self._bucket_name(workspace.project_id, workspace_id)

        try:
            # Step 2: Create GCS bucket (idempotent for re-provision)
            bucket_exists = await self.gcp_client.bucket_exists(bucket_name)
            if not bucket_exists:
                await self.gcp_client.create_gcs_bucket(
                    bucket_name=bucket_name,
                    region=workspace.region,
                )
                logger.info("Created GCS bucket %s", bucket_name)

            # Step 3: Deploy Cloud Run service
            resources = ResourceProfileConfig.from_profile(workspace.resource_profile)
            env_vars = self._build_env_vars(workspace, bucket_name)

            service_info = await self.gcp_client.deploy_cloud_run_service(
                service_name=service_name,
                image=self._settings.GCP_WORKSPACE_IMAGE,
                region=workspace.region,
                env_vars=env_vars,
                resources=resources,
                gcs_bucket=bucket_name,
            )
            logger.info(
                "Deployed Cloud Run service %s at %s",
                service_name,
                service_info.url,
            )

            # Step 4: Store cloud resource info
            workspace.cloud_run_service = service_info.name
            workspace.cloud_run_url = service_info.url
            workspace.gcs_bucket = bucket_name

            # Step 5: Transition to ready
            workspace.transition_to("ready")
            await self.db.flush()

            return workspace

        except Exception as exc:
            # Rollback state on any GCP failure
            logger.error(
                "Provision failed for workspace %s: %s",
                workspace_id,
                exc,
                exc_info=True,
            )
            workspace.transition_to(previous_state)
            await self.db.flush()
            raise WorkspaceProvisionError(workspace_id, str(exc)) from exc

    async def teardown(
        self,
        workspace_id: UUID,
        preserve_storage: bool = True,
    ) -> Workspace:
        """Tear down cloud resources for a workspace.

        Flow:
        1. Load workspace, transition to "destroying"
        2. Delete Cloud Run service
        3. Optionally delete GCS bucket
        4. Clear cloud resource fields
        5. Transition to "destroyed"

        Args:
            workspace_id: The workspace to tear down.
            preserve_storage: If True, keep the GCS bucket (default).
                Set to False for full cleanup.
        """
        workspace = await self._get_workspace(workspace_id)

        # Step 1: Transition to destroying
        workspace.transition_to("destroying")
        await self.db.flush()

        try:
            # Step 2: Delete Cloud Run service
            if workspace.cloud_run_service:
                await self.gcp_client.delete_cloud_run_service(
                    service_name=workspace.cloud_run_service,
                    region=workspace.region,
                )
                logger.info("Deleted Cloud Run service %s", workspace.cloud_run_service)

            # Step 3: Optionally delete GCS bucket
            if not preserve_storage and workspace.gcs_bucket:
                await self.gcp_client.delete_gcs_bucket(workspace.gcs_bucket)
                logger.info("Deleted GCS bucket %s", workspace.gcs_bucket)

            # Step 4: Clear cloud fields
            workspace.cloud_run_service = None
            workspace.cloud_run_url = None
            if not preserve_storage:
                workspace.gcs_bucket = None

            # Step 5: Transition to destroyed
            workspace.transition_to("destroyed")
            await self.db.flush()

            return workspace

        except Exception as exc:
            logger.error(
                "Teardown failed for workspace %s: %s",
                workspace_id,
                exc,
                exc_info=True,
            )
            # Leave in "destroying" state -- manual intervention needed
            raise WorkspaceProvisionError(workspace_id, f"Teardown failed: {exc}") from exc

    async def stop(self, workspace_id: UUID) -> Workspace:
        """Stop a workspace by scaling Cloud Run to zero.

        The GCS bucket and Cloud Run service definition remain.
        The workspace can be re-provisioned later.
        """
        workspace = await self._get_workspace(workspace_id)

        if workspace.cloud_run_service:
            await self.gcp_client.scale_cloud_run_service(
                service_name=workspace.cloud_run_service,
                region=workspace.region,
                min_instances=0,
                max_instances=0,
            )
            logger.info("Scaled Cloud Run service %s to zero", workspace.cloud_run_service)

        workspace.transition_to("stopped")
        await self.db.flush()

        return workspace

    async def get_status(self, workspace_id: UUID) -> dict[str, Any]:
        """Get workspace status with cloud resource details.

        Returns a dict with workspace state, cloud run status, and
        bucket existence -- useful for health dashboards and debugging.
        """
        workspace = await self._get_workspace(workspace_id)

        result: dict[str, Any] = {
            "workspace_id": str(workspace_id),
            "state": workspace.state,
            "resource_profile": workspace.resource_profile,
            "region": workspace.region,
            "cloud_run_service": workspace.cloud_run_service,
            "cloud_run_url": workspace.cloud_run_url,
            "gcs_bucket": workspace.gcs_bucket,
        }

        # Query live cloud status if provisioned
        if workspace.cloud_run_service:
            service_info = await self.gcp_client.get_cloud_run_service(
                service_name=workspace.cloud_run_service,
                region=workspace.region,
            )
            result["cloud_run_status"] = service_info.status if service_info else "NOT_FOUND"
            result["cloud_run_revision"] = service_info.revision if service_info else None

        if workspace.gcs_bucket:
            result["bucket_exists"] = await self.gcp_client.bucket_exists(workspace.gcs_bucket)

        return result

    # --- Internal helpers ---

    async def _get_workspace(self, workspace_id: UUID) -> Workspace:
        """Load workspace or raise WorkspaceNotFoundError."""
        workspace = await self.workspace_service.get(self.db, workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        return workspace

    def _build_env_vars(self, workspace: Workspace, bucket_name: str) -> dict[str, str]:
        """Build environment variables for the Cloud Run container."""
        env_vars = {
            "REPO_URL": workspace.repo_url,
            "DEFAULT_BRANCH": workspace.default_branch,
            "WORKSPACE_ID": str(workspace.id),
            "GCS_BUCKET": bucket_name,
        }
        # Merge any custom config from workspace.config
        if workspace.config:
            for key, value in workspace.config.items():
                if isinstance(value, str):
                    env_vars[key] = value
        return env_vars
```

### Error Handling Strategy

| Failure Point | Behavior | Resulting State |
|---|---|---|
| GCS bucket creation fails | Roll back to previous state (`created` or `stopped`) | `created` / `stopped` |
| Cloud Run deploy fails (bucket created) | Roll back to previous state. Bucket remains (harmless, reused on retry) | `created` / `stopped` |
| Teardown: Cloud Run delete fails | Leave in `destroying` state for manual intervention | `destroying` |
| Teardown: GCS delete fails | Leave in `destroying` state for manual intervention | `destroying` |
| Stop: scale fails | Raise error, state unchanged (transition not yet applied) | `ready` |

The key insight: provision failures are recoverable (retry), teardown failures require manual intervention. This matches typical cloud resource lifecycle patterns.

---

## 4. Molecule Exceptions

Add to `app/backend/src/molecules/exceptions.py`:

```python
class WorkspaceNotFoundError(MoleculeError):
    def __init__(self, workspace_id: UUID) -> None:
        super().__init__(f"Workspace {workspace_id} not found")
        self.workspace_id = workspace_id


class WorkspaceProvisionError(MoleculeError):
    def __init__(self, workspace_id: UUID, reason: str) -> None:
        super().__init__(f"Workspace {workspace_id} provisioning failed: {reason}")
        self.workspace_id = workspace_id
        self.reason = reason
```

---

## 5. Workspace Container Image

### Dockerfile

```dockerfile
# infrastructure/workspace/Dockerfile
#
# Workspace server container -- runs inside Cloud Run, provides
# file/git/terminal access for agents working on a repository.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    openssh-client \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash workspace

# App directory
WORKDIR /app

# Python deps
COPY server/requirements.txt /app/requirements.txt
RUN python3 -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Copy server code
COPY server/ /app/server/

# Workspace directory (repo clone target)
RUN mkdir -p /workspace && chown workspace:workspace /workspace

# Switch to non-root
USER workspace

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8080

ENTRYPOINT ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Directory Structure

```
infrastructure/
  workspace/
    Dockerfile
    cloudbuild.yaml
    server/
      __init__.py
      main.py              # FastAPI app + lifespan (repo clone on startup)
      requirements.txt     # fastapi, uvicorn, gitpython (minimal)
      routers/
        __init__.py
        health.py          # GET /health
        files.py           # File CRUD
        git.py             # Git operations
        worktrees.py       # Worktree management
        terminal.py        # Shell command execution
```

### Cloud Build

```yaml
# infrastructure/workspace/cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'northamerica-northeast2-docker.pkg.dev/stack-bench/workspace/workspace-server:$SHORT_SHA'
      - '-t'
      - 'northamerica-northeast2-docker.pkg.dev/stack-bench/workspace/workspace-server:latest'
      - '.'
    dir: 'infrastructure/workspace'

images:
  - 'northamerica-northeast2-docker.pkg.dev/stack-bench/workspace/workspace-server:$SHORT_SHA'
  - 'northamerica-northeast2-docker.pkg.dev/stack-bench/workspace/workspace-server:latest'
```

---

## 6. Workspace Server API

The workspace server is a lightweight FastAPI app that runs inside the container. It is NOT part of the main stack-bench backend -- it runs independently with its own process.

### Startup Behavior

On startup (via FastAPI lifespan), the server:
1. Reads `REPO_URL` and `DEFAULT_BRANCH` from environment
2. Clones the repo into `/workspace/main/` (if not already present)
3. Sets up the git worktree root

### Endpoints

#### Health

```
GET /health
Response: { "status": "ok", "repo_url": "...", "branch": "main" }
```

#### Files

```
GET    /files?path=/workspace/main/     # List directory contents
GET    /files/{path:path}               # Read file contents (returns text or base64)
PUT    /files/{path:path}               # Write file (body: { "content": "..." })
DELETE /files/{path:path}               # Delete file
```

Request/response schemas:

```python
class FileEntry(BaseModel):
    name: str
    path: str
    type: str  # "file" | "dir"
    size: int | None = None

class FileContent(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"  # "utf-8" or "base64"
    size: int

class FileWrite(BaseModel):
    content: str
    encoding: str = "utf-8"
```

#### Git Operations

```
GET  /git/status                       # Working tree status
POST /git/checkout   { "ref": "..." }  # Checkout branch/commit
POST /git/commit     { "message": "...", "paths": [...] }
POST /git/diff       { "base": "main", "head": "HEAD" }
POST /git/log        { "max_count": 20 }
POST /git/fetch
POST /git/pull
```

Response schema for status:

```python
class GitStatus(BaseModel):
    branch: str
    clean: bool
    staged: list[str]
    modified: list[str]
    untracked: list[str]
    ahead: int
    behind: int
```

#### Worktrees

```
GET    /worktrees                       # List worktrees
POST   /worktrees   { "name": "agent-coder-abc", "ref": "main" }
DELETE /worktrees/{name}
```

Response schema:

```python
class WorktreeInfo(BaseModel):
    name: str
    path: str
    branch: str
    head_sha: str
    is_main: bool
```

Worktrees are created at `/workspace/worktrees/{name}/`. Each worktree is a separate git working directory sharing the same `.git` -- perfect for multi-agent isolation.

#### Terminal

```
POST /terminal   { "command": "ls -la", "cwd": "/workspace/main", "timeout": 30 }
```

Response:

```python
class TerminalResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
```

Security constraints for terminal:
- Commands run as `workspace` user (non-root)
- Working directory must be under `/workspace/`
- Configurable timeout (default 30s, max 300s)
- No network access restrictions for now (agents need to install deps, fetch, etc.)

### Requirements

```
# infrastructure/workspace/server/requirements.txt
fastapi>=0.115.0,<1.0
uvicorn[standard]>=0.30.0,<1.0
```

Git operations use `asyncio.create_subprocess_exec` (same pattern as `CloneManager`), not `gitpython`. This avoids an unnecessary dependency and gives better async behavior.

---

## 7. Test Plan

### Unit Tests: WorkspaceManager

File: `app/backend/__tests__/molecules/test_workspace_manager.py`

All tests mock the GCPClient via the protocol. WorkspaceService operates against a real test DB (same as other molecule tests).

```python
# Test fixture
@pytest.fixture
def mock_gcp_client():
    """Create a mock GCP client implementing GCPClientProtocol."""
    client = AsyncMock()
    client.bucket_exists.return_value = False
    client.create_gcs_bucket.return_value = GCSBucketInfo(
        name="stack-bench-ws-test-test", location="northamerica-northeast2"
    )
    client.deploy_cloud_run_service.return_value = CloudRunServiceInfo(
        name="ws-test1234",
        url="https://ws-test1234-xyz.a.run.app",
        region="northamerica-northeast2",
        status="READY",
    )
    return client
```

| Test | What It Validates |
|---|---|
| `test_provision_happy_path` | Full provision flow: created -> provisioning -> ready, GCS + Cloud Run created, fields stored |
| `test_provision_reprovision_from_stopped` | stopped -> provisioning -> ready, bucket_exists=True so bucket not re-created |
| `test_provision_gcs_failure_rolls_back` | GCS creation fails, state rolls back to created |
| `test_provision_cloud_run_failure_rolls_back` | Cloud Run deploy fails, state rolls back to created, bucket remains |
| `test_provision_invalid_state` | Calling provision on a "ready" workspace raises InvalidStateTransitionError |
| `test_teardown_happy_path` | ready -> destroying -> destroyed, Cloud Run deleted, bucket preserved |
| `test_teardown_with_storage_deletion` | preserve_storage=False, both Cloud Run and GCS deleted |
| `test_teardown_cloud_run_failure` | Cloud Run delete fails, stays in "destroying" |
| `test_stop_scales_to_zero` | ready -> stopped, scale_cloud_run_service called with min=0, max=0 |
| `test_stop_no_cloud_run_service` | Workspace without cloud_run_service, just transitions state |
| `test_get_status_ready` | Returns workspace + live cloud status |
| `test_get_status_created` | Returns workspace state only, no cloud queries |
| `test_workspace_not_found` | Non-existent workspace_id raises WorkspaceNotFoundError |
| `test_service_name_format` | `_service_name()` returns correct format |
| `test_bucket_name_format` | `_bucket_name()` returns correct format |
| `test_build_env_vars` | Correct env vars built from workspace fields + config |
| `test_resource_profile_configs` | ResourceProfileConfig.from_profile returns correct values for light/standard/heavy |
| `test_resource_profile_invalid` | ResourceProfileConfig.from_profile raises ValueError for unknown profile |

### Unit Tests: GCP Client Protocol

File: `app/backend/__tests__/molecules/test_gcp_client.py`

| Test | What It Validates |
|---|---|
| `test_resource_profile_light` | Light profile: 1 CPU, 512Mi, 1 max |
| `test_resource_profile_standard` | Standard profile: 2 CPU, 1Gi, 1 max |
| `test_resource_profile_heavy` | Heavy profile: 4 CPU, 2Gi, 2 max |
| `test_resource_profile_invalid` | ValueError for unknown profile |
| `test_cloud_run_service_info_fields` | Dataclass fields correct |
| `test_gcs_bucket_info_fields` | Dataclass fields correct |

### Workspace Server Tests

File: `infrastructure/workspace/server/tests/test_server.py`

These are standalone pytest tests (not part of the backend test suite). Run separately.

| Test | What It Validates |
|---|---|
| `test_health_endpoint` | Returns 200 with status/repo info |
| `test_list_files` | Lists directory contents |
| `test_read_file` | Reads file content |
| `test_write_file` | Creates/overwrites file |
| `test_delete_file` | Removes file |
| `test_git_status` | Returns git status info |
| `test_create_worktree` | Creates isolated worktree |
| `test_list_worktrees` | Lists all worktrees |
| `test_delete_worktree` | Removes worktree |
| `test_terminal_command` | Executes command, returns output |
| `test_terminal_timeout` | Command exceeding timeout returns timed_out=True |
| `test_terminal_cwd_validation` | Rejects cwd outside /workspace/ |

These tests use `httpx.AsyncClient` with the FastAPI `TestClient` pattern. Git tests use a temporary git repo created in a pytest fixture.

---

## 8. File List

### New Files

| File | Purpose |
|---|---|
| `app/backend/src/molecules/services/gcp_client.py` | GCPClientProtocol + GCPClient + dataclasses |
| `app/backend/src/molecules/services/workspace_manager.py` | WorkspaceManager molecule |
| `app/backend/__tests__/molecules/test_workspace_manager.py` | Unit tests for WorkspaceManager |
| `app/backend/__tests__/molecules/test_gcp_client.py` | Unit tests for GCP client dataclasses/protocol |
| `infrastructure/workspace/Dockerfile` | Workspace container image |
| `infrastructure/workspace/cloudbuild.yaml` | Cloud Build config |
| `infrastructure/workspace/server/__init__.py` | Package init |
| `infrastructure/workspace/server/main.py` | FastAPI app + lifespan |
| `infrastructure/workspace/server/requirements.txt` | Python dependencies |
| `infrastructure/workspace/server/routers/__init__.py` | Router package init |
| `infrastructure/workspace/server/routers/health.py` | Health endpoint |
| `infrastructure/workspace/server/routers/files.py` | File CRUD endpoints |
| `infrastructure/workspace/server/routers/git.py` | Git operation endpoints |
| `infrastructure/workspace/server/routers/worktrees.py` | Worktree management |
| `infrastructure/workspace/server/routers/terminal.py` | Terminal execution |
| `infrastructure/workspace/server/tests/__init__.py` | Test package init |
| `infrastructure/workspace/server/tests/test_server.py` | Workspace server tests |

### Modified Files

| File | Change |
|---|---|
| `app/backend/src/molecules/exceptions.py` | Add `WorkspaceNotFoundError`, `WorkspaceProvisionError` |
| `app/backend/src/config/settings.py` | Add `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WORKSPACE_IMAGE`, `GCP_SERVICE_ACCOUNT_EMAIL` |
| `app/backend/pyproject.toml` | Add `google-cloud-storage`, `google-cloud-run` to dependencies |

---

## 9. Implementation Order

1. **GCP client abstraction** (`gcp_client.py`) -- protocol, dataclasses, production implementation stubs
2. **Molecule exceptions** (`exceptions.py`) -- add workspace-specific errors
3. **Settings** (`settings.py`) -- add GCP config fields
4. **WorkspaceManager** (`workspace_manager.py`) -- the core molecule
5. **WorkspaceManager tests** (`test_workspace_manager.py`, `test_gcp_client.py`) -- full coverage with mocked GCP
6. **Workspace server** (`infrastructure/workspace/server/`) -- all routers and main app
7. **Dockerfile + Cloud Build** (`infrastructure/workspace/Dockerfile`, `cloudbuild.yaml`)
8. **Workspace server tests** (`infrastructure/workspace/server/tests/`)

Steps 1-5 are the backend molecule work. Steps 6-8 are the container image work. They can be done in parallel by different builders if needed.

---

## 10. Dependencies

### Python Packages (backend)

```
google-cloud-storage>=2.18.0,<3.0
google-cloud-run>=0.10.0,<1.0
```

These are only imported in the production `GCPClient` class. Tests never import them (they mock the protocol). Add to `pyproject.toml` under `[project.dependencies]`.

### Python Packages (workspace server)

```
fastapi>=0.115.0,<1.0
uvicorn[standard]>=0.30.0,<1.0
```

Kept minimal. No database, no ORM, no pattern-stack. The server is a thin shell around `asyncio.create_subprocess_exec` calls.

---

## 11. Open Decisions (for builder to resolve)

1. **GCS FUSE vs ephemeral disk** -- The epic spec mentions both options. Recommendation: start with ephemeral disk (clone on startup). GCS is backup only, synced on explicit save. Simpler, faster git ops. FUSE can be added later if needed.

2. **Cloud Run service account** -- The workspace container needs a GCS-capable service account. The `GCP_SERVICE_ACCOUNT_EMAIL` setting provides this. The builder should set `service_account` on the Cloud Run service config.

3. **GCPClient production implementation** -- The protocol is fully specified but the production `GCPClient` methods are stubs (`...`). The builder should implement them using the `google.cloud.run_v2` and `google.cloud.storage` SDKs. The key complexity is in `deploy_cloud_run_service` which must construct the full Cloud Run service spec (container, env vars, volumes, scaling).

4. **Workspace server auth** -- For Phase 2, the workspace server has no auth. It runs behind Cloud Run IAM (backend authenticates as a service account). Adding token-based auth to the server itself is deferred to a future issue.
