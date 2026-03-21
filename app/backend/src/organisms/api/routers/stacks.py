from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from features.branches.schemas.output import BranchResponse
from features.pull_requests.schemas.output import PullRequestResponse
from features.stacks.schemas.output import StackResponse
from organisms.api.dependencies import StackAPIDep

router = APIRouter(prefix="/stacks", tags=["stacks"])


# --- Request schemas (router-local, like CreateConversationRequest) ---


class CreateStackRequest(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    trunk: str = Field("main", min_length=1, max_length=200)
    base_branch_id: UUID | None = None


class AddBranchRequest(BaseModel):
    workspace_id: UUID
    name: str = Field(..., min_length=1, max_length=500)
    position: int | None = Field(None, ge=1)
    head_sha: str | None = Field(None, max_length=40)


class CreatePullRequestRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    review_notes: str | None = None


class LinkExternalPRRequest(BaseModel):
    external_id: int
    external_url: str = Field(..., max_length=500)


# --- Stack endpoints ---


@router.post("/", response_model=StackResponse, status_code=201)
async def create_stack(data: CreateStackRequest, api: StackAPIDep) -> StackResponse:
    return await api.create_stack(
        data.project_id,
        data.name,
        trunk=data.trunk,
        base_branch_id=data.base_branch_id,
    )


@router.get("/", response_model=list[StackResponse])
async def list_stacks(
    api: StackAPIDep,
    project_id: UUID = Query(...),  # noqa: B008
) -> list[StackResponse]:
    return await api.list_stacks(project_id)


@router.get("/{stack_id}", response_model=StackResponse)
async def get_stack(stack_id: UUID, api: StackAPIDep) -> StackResponse:
    return await api.get_stack(stack_id)


@router.get("/{stack_id}/detail")
async def get_stack_detail(stack_id: UUID, api: StackAPIDep) -> dict[str, object]:
    """Get stack with all branches and pull requests."""
    return await api.get_stack_detail(stack_id)


@router.delete("/{stack_id}", status_code=204)
async def delete_stack(stack_id: UUID, api: StackAPIDep) -> None:
    await api.delete_stack(stack_id)


# --- Branch endpoints (nested under stack) ---


@router.post("/{stack_id}/branches", response_model=BranchResponse, status_code=201)
async def add_branch(stack_id: UUID, data: AddBranchRequest, api: StackAPIDep) -> BranchResponse:
    return await api.add_branch(
        stack_id,
        data.workspace_id,
        data.name,
        position=data.position,
        head_sha=data.head_sha,
    )


# --- PullRequest endpoints (nested under branch) ---


@router.post(
    "/{stack_id}/branches/{branch_id}/pr",
    response_model=PullRequestResponse,
    status_code=201,
)
async def create_pull_request(
    stack_id: UUID,
    branch_id: UUID,
    data: CreatePullRequestRequest,
    api: StackAPIDep,
) -> PullRequestResponse:
    return await api.create_pull_request(
        branch_id,
        data.title,
        description=data.description,
        review_notes=data.review_notes,
    )


@router.post(
    "/pull-requests/{pull_request_id}/link",
    response_model=PullRequestResponse,
)
async def link_external_pr(
    pull_request_id: UUID,
    data: LinkExternalPRRequest,
    api: StackAPIDep,
) -> PullRequestResponse:
    return await api.link_external_pr(pull_request_id, data.external_id, data.external_url)
