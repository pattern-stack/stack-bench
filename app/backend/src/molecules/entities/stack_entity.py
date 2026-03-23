from __future__ import annotations

from typing import TYPE_CHECKING, Any

from features.branches.schemas.input import BranchCreate, BranchUpdate
from features.branches.service import BranchService
from features.pull_requests.schemas.input import PullRequestCreate, PullRequestUpdate
from features.pull_requests.service import PullRequestService
from features.stacks.schemas.input import StackCreate
from features.stacks.service import StackService
from features.workspaces.service import WorkspaceService
from molecules.exceptions import (
    BranchNotFoundError,
    PullRequestNotFoundError,
    StackCycleError,
    StackNotFoundError,
)
from molecules.providers.github_adapter import parse_owner_repo

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from features.branches.models import Branch
    from features.pull_requests.models import PullRequest
    from features.stacks.models import Stack


class StackEntity:
    """Domain aggregate for stack + branch + pull request lifecycle.

    Coordinates the three features into a single domain concept.
    The stack owns the branches, and each branch optionally owns a pull request.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.stack_service = StackService()
        self.branch_service = BranchService()
        self.pr_service = PullRequestService()
        self.workspace_service = WorkspaceService()

    # --- Stack operations ---

    async def create_stack(
        self,
        project_id: UUID,
        name: str,
        *,
        trunk: str = "main",
        base_branch_id: UUID | None = None,
    ) -> Stack:
        """Create a new stack."""
        stack = await self.stack_service.create(
            self.db,
            StackCreate(
                project_id=project_id,
                name=name,
                trunk=trunk,
                base_branch_id=base_branch_id,
            ),
        )
        return stack

    async def get_stack(self, stack_id: UUID) -> Stack:
        """Get a stack by ID or raise."""
        stack = await self.stack_service.get(self.db, stack_id)
        if stack is None or stack.is_deleted:
            raise StackNotFoundError(stack_id)
        return stack

    async def get_stack_with_branches(self, stack_id: UUID) -> dict[str, Any]:
        """Get a stack with all its branches and their pull requests."""
        stack = await self.get_stack(stack_id)
        branches = await self.branch_service.list_by_stack(self.db, stack_id)

        branch_data = []
        for branch in branches:
            pr = await self.pr_service.get_by_branch(self.db, branch.id)
            branch_data.append({"branch": branch, "pull_request": pr})

        return {"stack": stack, "branches": branch_data}

    async def list_stacks_by_project(self, project_id: UUID) -> list[Stack]:
        """List all stacks for a project."""
        return await self.stack_service.list_by_project(self.db, project_id)

    async def delete_stack(self, stack_id: UUID) -> None:
        """Soft-delete a stack."""
        stack = await self.get_stack(stack_id)
        stack.soft_delete()
        await self.db.flush()

    # --- Branch operations ---

    async def add_branch(
        self,
        stack_id: UUID,
        workspace_id: UUID,
        name: str,
        *,
        position: int | None = None,
        head_sha: str | None = None,
    ) -> Branch:
        """Add a branch to a stack.

        If position is None, appends to the end of the stack.
        """
        await self.get_stack(stack_id)  # Validate stack exists

        if position is None:
            max_pos = await self.branch_service.get_max_position(self.db, stack_id)
            position = max_pos + 1

        branch = await self.branch_service.create(
            self.db,
            BranchCreate(
                stack_id=stack_id,
                workspace_id=workspace_id,
                name=name,
                position=position,
                head_sha=head_sha,
            ),
        )
        return branch

    async def get_branch(self, branch_id: UUID) -> Branch:
        """Get a branch by ID or raise."""
        branch = await self.branch_service.get(self.db, branch_id)
        if branch is None or branch.is_deleted:
            raise BranchNotFoundError(branch_id)
        return branch

    async def update_branch_sha(self, branch_id: UUID, head_sha: str) -> Branch:
        """Update a branch's head SHA."""
        branch = await self.get_branch(branch_id)
        updated = await self.branch_service.update(self.db, branch.id, BranchUpdate(head_sha=head_sha))
        return updated

    # --- PullRequest operations ---

    async def create_pull_request(
        self,
        branch_id: UUID,
        title: str,
        *,
        description: str | None = None,
        review_notes: str | None = None,
    ) -> PullRequest:
        """Create a pull request for a branch."""
        await self.get_branch(branch_id)  # Validate branch exists

        pr = await self.pr_service.create(
            self.db,
            PullRequestCreate(
                branch_id=branch_id,
                title=title,
                description=description,
                review_notes=review_notes,
            ),
        )
        return pr

    async def get_pull_request(self, pull_request_id: UUID) -> PullRequest:
        """Get a pull request by ID or raise."""
        pr = await self.pr_service.get(self.db, pull_request_id)
        if pr is None or pr.is_deleted:
            raise PullRequestNotFoundError(pull_request_id)
        return pr

    async def link_external_pr(self, pull_request_id: UUID, external_id: int, external_url: str) -> PullRequest:
        """Link a pull request to a GitHub PR after submission."""
        pr = await self.get_pull_request(pull_request_id)
        updated = await self.pr_service.update(
            self.db,
            pr.id,
            PullRequestUpdate(external_id=external_id, external_url=external_url),
        )
        return updated

    # --- Git context resolution ---

    async def get_branch_repo_context(self, branch_id: UUID) -> tuple[str, str, str, str]:
        """Resolve branch -> workspace -> repo_url, plus base/head refs.

        Returns (owner, repo, base_ref, head_ref) where:
        - owner: GitHub org/user (from workspace.repo_url)
        - repo: GitHub repo name (from workspace.repo_url)
        - base_ref: the parent branch name or trunk (for diff base)
        - head_ref: branch head_sha if available, otherwise branch name
        """
        branch = await self.get_branch(branch_id)
        workspace = await self.workspace_service.get(self.db, branch.workspace_id)
        if workspace is None:
            raise BranchNotFoundError(branch_id)

        owner, repo = parse_owner_repo(workspace.repo_url)

        # Head ref: prefer SHA (immutable, cache-friendly), fall back to branch name
        head_ref = branch.head_sha if branch.head_sha else branch.name

        # Base ref: position 1 diffs against trunk, otherwise against the previous branch
        stack = await self.get_stack(branch.stack_id)
        if branch.position == 1:
            base_ref = stack.trunk
        else:
            # Find the branch at position N-1
            branches = await self.branch_service.list_by_stack(self.db, branch.stack_id)
            prev_branch = None
            for b in branches:
                if b.position == branch.position - 1:
                    prev_branch = b
                    break
            base_ref = prev_branch.name if prev_branch is not None else stack.trunk

        return owner, repo, base_ref, head_ref

    # --- DAG validation ---

    async def validate_dag(self, stack_id: UUID, base_branch_id: UUID) -> None:
        """Validate that setting base_branch_id does not create a cycle.

        Walks the DAG from base_branch_id upward, checking that we never
        reach a branch belonging to stack_id.
        """
        visited: set[UUID] = set()
        current_branch_id: UUID | None = base_branch_id

        while current_branch_id is not None:
            if current_branch_id in visited:
                raise StackCycleError(stack_id, base_branch_id)
            visited.add(current_branch_id)

            branch = await self.branch_service.get(self.db, current_branch_id)
            if branch is None:
                break

            if branch.stack_id == stack_id:
                raise StackCycleError(stack_id, base_branch_id)

            # Walk up to the parent stack's base_branch_id
            parent_stack = await self.stack_service.get(self.db, branch.stack_id)
            if parent_stack is None:
                break
            current_branch_id = parent_stack.base_branch_id
