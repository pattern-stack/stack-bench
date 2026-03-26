from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class WorkspaceResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    project_id: UUID
    name: str
    repo_url: str
    provider: str
    default_branch: str
    local_path: str | None = None
    metadata_: dict[str, Any]
    is_active: bool
    state: str
    resource_profile: str
    region: str
    cloud_run_service: str | None = None
    cloud_run_url: str | None = None
    gcs_bucket: str | None = None
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceSummary(BaseModel):
    id: UUID
    name: str
    state: str
    resource_profile: str
    cloud_run_url: str | None = None

    model_config = {"from_attributes": True}


class WorkspaceStatusResponse(BaseModel):
    workspace_id: str
    state: str
    resource_profile: str
    region: str
    cloud_run_service: str | None = None
    cloud_run_url: str | None = None
    gcs_bucket: str | None = None
    cloud_run_status: str | None = None
    cloud_run_revision: str | None = None
    bucket_exists: bool | None = None
