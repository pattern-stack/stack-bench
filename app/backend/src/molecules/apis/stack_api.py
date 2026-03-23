from __future__ import annotations

from typing import TYPE_CHECKING

from features.branches.schemas.output import BranchResponse
from features.pull_requests.schemas.output import PullRequestResponse
from features.stacks.schemas.output import StackResponse
from molecules.entities.stack_entity import StackEntity

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from molecules.providers.github_adapter import DiffData, FileContent, FileTreeNode, GitHubAdapter


class StackDetailResponse:
    """Not a Pydantic model -- a simple container for stack + branch + PR data.

    Serialization happens at the router level using the individual response schemas.
    """

    pass


class StackAPI:
    """API facade for stack domain.

    Coordinates StackEntity and handles serialization. Both REST and CLI
    consume this. Permissions will be added here when auth is implemented.
    """

    def __init__(self, db: AsyncSession, github: GitHubAdapter | None = None) -> None:
        self.db = db
        self.entity = StackEntity(db)
        self.github = github

    async def create_stack(
        self,
        project_id: UUID,
        name: str,
        *,
        trunk: str = "main",
        base_branch_id: UUID | None = None,
    ) -> StackResponse:
        """Create a new stack."""
        if base_branch_id is not None:
            # Validate DAG before creating -- use a temporary stack_id
            # For new stacks, there can't be a cycle since the stack doesn't exist yet
            pass
        stack = await self.entity.create_stack(project_id, name, trunk=trunk, base_branch_id=base_branch_id)
        await self.db.commit()
        return StackResponse.model_validate(stack)

    async def get_stack(self, stack_id: UUID) -> StackResponse:
        """Get a stack."""
        stack = await self.entity.get_stack(stack_id)
        return StackResponse.model_validate(stack)

    async def get_stack_detail(self, stack_id: UUID) -> dict[str, object]:
        """Get a stack with all branches and PRs."""
        data = await self.entity.get_stack_with_branches(stack_id)
        stack = data["stack"]
        branches = []
        for bd in data["branches"]:
            branch_resp = BranchResponse.model_validate(bd["branch"])
            pr_resp = PullRequestResponse.model_validate(bd["pull_request"]) if bd["pull_request"] else None
            branches.append(
                {
                    "branch": branch_resp.model_dump(),
                    "pull_request": pr_resp.model_dump() if pr_resp else None,
                }
            )
        return {
            "stack": StackResponse.model_validate(stack).model_dump(),
            "branches": branches,
        }

    async def list_stacks(self, project_id: UUID) -> list[StackResponse]:
        """List all stacks for a project."""
        stacks = await self.entity.list_stacks_by_project(project_id)
        return [StackResponse.model_validate(s) for s in stacks]

    async def delete_stack(self, stack_id: UUID) -> None:
        """Soft-delete a stack."""
        await self.entity.delete_stack(stack_id)
        await self.db.commit()

    async def add_branch(
        self,
        stack_id: UUID,
        workspace_id: UUID,
        name: str,
        *,
        position: int | None = None,
        head_sha: str | None = None,
    ) -> BranchResponse:
        """Add a branch to a stack."""
        branch = await self.entity.add_branch(stack_id, workspace_id, name, position=position, head_sha=head_sha)
        await self.db.commit()
        return BranchResponse.model_validate(branch)

    async def create_pull_request(
        self,
        branch_id: UUID,
        title: str,
        *,
        description: str | None = None,
        review_notes: str | None = None,
    ) -> PullRequestResponse:
        """Create a pull request for a branch."""
        pr = await self.entity.create_pull_request(branch_id, title, description=description, review_notes=review_notes)
        await self.db.commit()
        return PullRequestResponse.model_validate(pr)

    async def link_external_pr(self, pull_request_id: UUID, external_id: int, external_url: str) -> PullRequestResponse:
        """Link a PR to a GitHub PR after submission."""
        pr = await self.entity.link_external_pr(pull_request_id, external_id, external_url)
        await self.db.commit()
        return PullRequestResponse.model_validate(pr)

    # --- Git data (read-through via GitHubAdapter) ---

    async def get_branch_diff(self, stack_id: UUID, branch_id: UUID) -> DiffData:
        """Get diff for a branch relative to its base."""
        if self.github is None:
            msg = "GitHubAdapter not configured"
            raise RuntimeError(msg)
        owner, repo, base_ref, head_ref = await self.entity.get_branch_repo_context(branch_id)
        return await self.github.get_diff(owner, repo, base_ref, head_ref)

    async def get_branch_tree(self, stack_id: UUID, branch_id: UUID) -> FileTreeNode:
        """Get file tree at branch head."""
        if self.github is None:
            msg = "GitHubAdapter not configured"
            raise RuntimeError(msg)
        owner, repo, _, head_ref = await self.entity.get_branch_repo_context(branch_id)
        return await self.github.get_file_tree(owner, repo, head_ref)

    async def get_branch_file(self, stack_id: UUID, branch_id: UUID, path: str) -> FileContent:
        """Get file content at branch head."""
        if self.github is None:
            msg = "GitHubAdapter not configured"
            raise RuntimeError(msg)
        owner, repo, _, head_ref = await self.entity.get_branch_repo_context(branch_id)
        return await self.github.get_file_content(owner, repo, head_ref, path)
