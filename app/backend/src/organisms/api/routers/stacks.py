from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from features.branches.schemas.output import BranchResponse
from features.pull_requests.schemas.output import PullRequestResponse
from features.review_comments.schemas.input import ReviewCommentCreate, ReviewCommentUpdate
from features.review_comments.schemas.output import ReviewCommentResponse
from features.stacks.schemas.output import StackResponse
from molecules.providers.github_adapter import DiffData, FileContent, FileTreeNode
from organisms.api.dependencies import StackAPIDep, UserStackAPIDep

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


class BranchSyncItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    position: int = Field(..., ge=1)
    head_sha: str | None = Field(None, max_length=40)
    pr_number: int | None = None
    pr_url: str | None = Field(None, max_length=500)


class SyncStackRequest(BaseModel):
    workspace_id: UUID
    branches: list[BranchSyncItem]


class PushStackRequest(BaseModel):
    """Request body for stack push. Sent by the Go CLI after local git operations."""

    workspace_id: UUID
    branches: list[BranchSyncItem]


class ReadyStackRequest(BaseModel):
    """Optional: specify which branches to mark ready. If empty, marks all."""

    branch_ids: list[UUID] | None = None


class SyncBranchResult(BaseModel):
    branch: dict[str, object]
    pull_request: dict[str, object] | None


class SyncStackResponse(BaseModel):
    stack_id: str
    synced_count: int
    created_count: int
    branches: list[SyncBranchResult]


class CreateCommentRequest(BaseModel):
    pull_request_id: UUID
    path: str = Field(..., max_length=500)
    line_key: str = Field(..., max_length=200)
    body: str = Field(..., min_length=1)
    author: str = Field(..., max_length=200)
    line_number: int | None = None
    side: str | None = None


class UpdateCommentRequest(BaseModel):
    body: str | None = None
    resolved: bool | None = None


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


# --- Sync endpoint ---


@router.post("/{stack_id}/sync", response_model=SyncStackResponse)
async def sync_stack(stack_id: UUID, data: SyncStackRequest, api: UserStackAPIDep) -> dict[str, object]:
    """Sync stack state from client-provided branch and PR data.

    Called after `st push`, after merges, or manually from the UI.
    Creates or updates branches and links PRs as needed.
    """
    branches = [b.model_dump() for b in data.branches]
    return await api.sync_stack(stack_id, data.workspace_id, branches)


# --- Merge endpoint ---


@router.post("/{stack_id}/merge")
async def merge_stack(stack_id: UUID, api: UserStackAPIDep) -> dict[str, object]:
    """Merge all PRs in the stack bottom-up via GitHub API."""
    return await api.merge_stack(stack_id)


# --- Workflow endpoints (push, submit, ready) ---


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
    *,
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


# --- Git data endpoints (read-through via GitHub API) ---


@router.get(
    "/{stack_id}/branches/{branch_id}/diff",
    response_model=DiffData,
)
async def get_branch_diff(stack_id: UUID, branch_id: UUID, api: StackAPIDep) -> DiffData:
    """Get diff for a branch relative to its parent in the stack."""
    return await api.get_branch_diff(stack_id, branch_id)


@router.get(
    "/{stack_id}/branches/{branch_id}/tree",
    response_model=FileTreeNode,
)
async def get_branch_tree(stack_id: UUID, branch_id: UUID, api: StackAPIDep) -> FileTreeNode:
    """Get file tree at branch head."""
    return await api.get_branch_tree(stack_id, branch_id)


@router.get(
    "/{stack_id}/branches/{branch_id}/files/{path:path}",
    response_model=FileContent,
)
async def get_branch_file(stack_id: UUID, branch_id: UUID, path: str, api: StackAPIDep) -> FileContent:
    """Get file content at branch head."""
    return await api.get_branch_file(stack_id, branch_id, path)


# --- Review comment endpoints (Stack Bench local comments) ---


@router.post(
    "/{stack_id}/branches/{branch_id}/comments",
    response_model=ReviewCommentResponse,
    status_code=201,
)
async def create_comment(
    stack_id: UUID,
    branch_id: UUID,
    data: CreateCommentRequest,
    api: StackAPIDep,
) -> ReviewCommentResponse:
    """Create an inline review comment on a branch diff."""
    create_data = ReviewCommentCreate(
        pull_request_id=data.pull_request_id,
        branch_id=branch_id,
        path=data.path,
        line_key=data.line_key,
        body=data.body,
        author=data.author,
        line_number=data.line_number,
        side=data.side,
    )
    return await api.create_comment(create_data)


@router.get(
    "/{stack_id}/branches/{branch_id}/comments",
    response_model=list[ReviewCommentResponse],
)
async def list_comments(
    stack_id: UUID,
    branch_id: UUID,
    api: StackAPIDep,
) -> list[ReviewCommentResponse]:
    """List all inline review comments for a branch."""
    return await api.list_comments(branch_id)


@router.patch(
    "/{stack_id}/comments/{comment_id}",
    response_model=ReviewCommentResponse,
)
async def update_comment(
    stack_id: UUID,
    comment_id: UUID,
    data: UpdateCommentRequest,
    api: StackAPIDep,
) -> ReviewCommentResponse:
    """Update a review comment."""
    update_data = ReviewCommentUpdate(body=data.body, resolved=data.resolved)
    return await api.update_comment(comment_id, update_data)


@router.delete("/{stack_id}/comments/{comment_id}", status_code=204)
async def delete_comment(
    stack_id: UUID,
    comment_id: UUID,
    api: StackAPIDep,
) -> None:
    """Delete a review comment."""
    await api.delete_comment(comment_id)
