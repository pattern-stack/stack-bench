from __future__ import annotations

from typing import TYPE_CHECKING, Any

from features.branches.schemas.output import BranchResponse
from features.pull_requests.schemas.output import PullRequestResponse
from features.review_comments.schemas.output import ReviewCommentResponse
from features.review_comments.service import ReviewCommentService
from features.stacks.schemas.output import StackResponse
from molecules.entities.stack_entity import StackEntity
from molecules.events import (
    PULL_REQUEST_MARKED_READY,
    PULL_REQUEST_MERGED,
    REVIEW_COMMENT_CREATED,
    REVIEW_COMMENT_UPDATED,
    DomainEvent,
    publish,
)
from molecules.providers.github_adapter import parse_owner_repo

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from features.review_comments.schemas.input import ReviewCommentCreate, ReviewCommentUpdate
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
        self._comment_svc = ReviewCommentService()

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
        """Get a stack with all branches, PRs, and restack status."""
        data = await self.entity.get_stack_with_branches(stack_id)
        stack = data["stack"]
        branch_list = data["branches"]

        # Compute needs_restack per branch (only if github adapter is available)
        restack_flags: list[bool] = [False] * len(branch_list)
        if self.github is not None and len(branch_list) > 0:
            restack_flags = await self._compute_restack_flags(stack, branch_list)

        branches = []
        for i, bd in enumerate(branch_list):
            branch_resp = BranchResponse.model_validate(bd["branch"])
            pr_resp = PullRequestResponse.model_validate(bd["pull_request"]) if bd["pull_request"] else None
            branches.append(
                {
                    "branch": branch_resp.model_dump(),
                    "pull_request": pr_resp.model_dump() if pr_resp else None,
                    "needs_restack": restack_flags[i],
                }
            )
        return {
            "stack": StackResponse.model_validate(stack).model_dump(),
            "branches": branches,
        }

    async def _compute_restack_flags(self, stack: Any, branch_list: list[dict[str, Any]]) -> list[bool]:
        """Compute needs_restack for each branch in a stack.

        Uses asyncio.gather for parallel GitHub API calls.
        Branches that are merged or have no remote never need restack.
        """
        import asyncio

        assert self.github is not None
        github = self.github

        # Resolve owner/repo from the first branch's workspace
        first_branch = branch_list[0]["branch"]
        workspace = await self.entity.workspace_service.get(self.db, first_branch.workspace_id)
        if workspace is None:
            return [False] * len(branch_list)
        owner, repo = parse_owner_repo(workspace.repo_url)

        async def check_branch(index: int, bd: dict[str, Any]) -> bool:
            branch = bd["branch"]
            pr = bd.get("pull_request")

            # Merged branches never need restack
            if branch.state == "merged" or (pr is not None and pr.state == "merged"):
                return False

            head_ref = branch.head_sha if branch.head_sha else branch.name

            # Determine base ref
            if branch.position == 1:
                base_ref = stack.trunk
            else:
                prev_branch = branch_list[index - 1]["branch"]
                base_ref = prev_branch.name

            try:
                behind_count = await github.get_behind_count(owner, repo, base_ref, head_ref)
                return behind_count > 0
            except Exception:
                # On API error, don't flag as needing restack (avoid false positives)
                return False

        tasks = [check_branch(i, bd) for i, bd in enumerate(branch_list)]
        results = await asyncio.gather(*tasks)
        return list(results)

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

    # --- Sync operations ---

    async def sync_stack(
        self,
        stack_id: UUID,
        workspace_id: UUID,
        branches_data: list[dict[str, object]],
    ) -> dict[str, Any]:
        """Sync stack state from client-provided branch and PR data."""
        result: dict[str, Any] = await self.entity.sync_stack(stack_id, workspace_id, branches_data)
        await self.db.commit()

        serialized_branches: list[dict[str, Any]] = []
        for br in result["branches"]:
            branch_resp = BranchResponse.model_validate(br["branch"]).model_dump()
            pr_resp = (
                PullRequestResponse.model_validate(br["pull_request"]).model_dump() if br["pull_request"] else None
            )
            serialized_branches.append({"branch": branch_resp, "pull_request": pr_resp})

        return {
            "stack_id": str(stack_id),
            "branches": serialized_branches,
            "synced_count": result["synced_count"],
            "created_count": result["created_count"],
        }

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

    async def merge_stack(self, stack_id: UUID) -> dict[str, object]:
        """Merge all PRs in the stack, bottom-up."""
        if self.github is None:
            msg = "GitHubAdapter not configured"
            raise RuntimeError(msg)

        data = await self.entity.get_stack_with_branches(stack_id)
        results: list[dict[str, object]] = []

        for bd in data["branches"]:
            branch = bd["branch"]
            pr = bd.get("pull_request")
            if pr is None or pr.state == "merged":
                continue
            if pr.external_id is None:
                msg = f"PR for branch {branch.name} has no GitHub PR number"
                raise ValueError(msg)

            owner, repo, _, _ = await self.entity.get_branch_repo_context(branch.id)

            # Mark ready if draft
            if pr.state == "draft":
                await self.github.mark_pr_ready(owner, repo, pr.external_id)
                pr.transition_to("open")
                await publish(DomainEvent(
                    topic=PULL_REQUEST_MARKED_READY,
                    entity_type="pull_request",
                    entity_id=pr.id,
                    source="user_action",
                    payload={
                        "branch_id": str(branch.id),
                        "stack_id": str(stack_id),
                        "external_id": pr.external_id,
                    },
                ))

            # Merge
            await self.github.merge_pr(owner, repo, pr.external_id)
            if pr.state == "open":
                pr.transition_to("approved")
            pr.transition_to("merged")
            branch.transition_to("merged")
            await publish(DomainEvent(
                topic=PULL_REQUEST_MERGED,
                entity_type="pull_request",
                entity_id=pr.id,
                source="user_action",
                payload={
                    "branch_id": str(branch.id),
                    "stack_id": str(stack_id),
                    "external_id": pr.external_id,
                },
            ))
            results.append({"branch": branch.name, "pr_number": pr.external_id, "merged": True})

        await self.db.commit()
        return {"stack_id": str(stack_id), "merged": results}

    # --- Review comments (Stack Bench local, GitHub sync optional) ---

    async def create_comment(self, data: ReviewCommentCreate) -> ReviewCommentResponse:
        """Create a review comment. Saved locally; GitHub sync is best-effort."""
        comment = await self._comment_svc.create(self.db, data)
        await self.db.commit()
        await self.db.refresh(comment)
        await publish(DomainEvent(
            topic=REVIEW_COMMENT_CREATED,
            entity_type="review_comment",
            entity_id=comment.id,
            source="user_action",
            payload={
                "pull_request_id": str(data.pull_request_id),
                "branch_id": str(data.branch_id),
            },
        ))
        return ReviewCommentResponse.model_validate(comment)

    async def list_comments(self, branch_id: UUID) -> list[ReviewCommentResponse]:
        """List all comments for a branch."""
        comments = await self._comment_svc.list_by_branch(self.db, branch_id)
        return [ReviewCommentResponse.model_validate(c) for c in comments]

    async def update_comment(self, comment_id: UUID, data: ReviewCommentUpdate) -> ReviewCommentResponse:
        """Update a comment body or resolved status."""
        comment = await self._comment_svc.update(self.db, comment_id, data)
        await self.db.commit()
        await self.db.refresh(comment)
        await publish(DomainEvent(
            topic=REVIEW_COMMENT_UPDATED,
            entity_type="review_comment",
            entity_id=comment.id,
            source="user_action",
            payload={
                "resolved": getattr(data, 'resolved', None),
            },
        ))
        return ReviewCommentResponse.model_validate(comment)

    async def delete_comment(self, comment_id: UUID) -> None:
        """Soft-delete a comment."""
        await self._comment_svc.delete(self.db, comment_id)
        await self.db.commit()
