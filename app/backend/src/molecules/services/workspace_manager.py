"""WorkspaceManager molecule for cloud workspace lifecycle.

Composes WorkspaceService (feature-layer DB ops) with GCPClient
(cloud infrastructure ops) to manage workspace provisioning,
teardown, stopping, and status queries.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from config.settings import get_settings
from features.workspaces.service import WorkspaceService
from molecules.exceptions import (
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
