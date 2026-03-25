"""Remote restack service — rebase stacked branches via ephemeral clone.

Clones the repository into a temporary directory, rebases each branch
in position order onto its parent (trunk for position 1, previous branch
for others), and force-pushes the results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from molecules.services.clone_manager import CloneError, CloneOptions, GitOperations

if TYPE_CHECKING:
    from molecules.services.clone_manager import CloneManager

logger = logging.getLogger(__name__)


@dataclass
class RestackBranchResult:
    """Result for a single branch in a restack operation."""

    branch_name: str
    position: int
    old_sha: str | None
    new_sha: str | None
    status: str  # "rebased" | "conflict" | "skipped" | "up_to_date" | "error"
    error: str | None = None
    conflicting_files: list[str] = field(default_factory=list)


@dataclass
class RestackResult:
    """Aggregate result of a restack operation across all branches."""

    success: bool
    branches: list[RestackBranchResult] = field(default_factory=list)
    error: str | None = None


class RemoteRestackService:
    """Orchestrates remote rebase of stacked branches via ephemeral clone.

    Usage::

        clone_mgr = CloneManager(...)
        svc = RemoteRestackService(clone_mgr)
        result = await svc.restack(
            repo_url="https://github.com/org/repo.git",
            trunk="main",
            branches=[
                {"name": "feat/1-first", "position": 1, "head_sha": "abc123"},
                {"name": "feat/2-second", "position": 2, "head_sha": "def456"},
            ],
        )
    """

    def __init__(self, clone_manager: CloneManager) -> None:
        self.clone_manager = clone_manager

    async def restack(
        self,
        repo_url: str,
        trunk: str,
        branches: list[dict[str, Any]],
    ) -> RestackResult:
        """Clone repo, rebase branches in order, force-push results.

        Args:
            repo_url: HTTPS clone URL for the repository.
            trunk: Name of the trunk branch (e.g. "main").
            branches: List of dicts with "name", "position", and "head_sha" keys,
                      ordered by position (1-indexed).

        Returns:
            RestackResult with per-branch outcomes.
        """
        # Sort by position to ensure correct order
        sorted_branches = sorted(branches, key=lambda b: b["position"])

        try:
            async with self.clone_manager.clone(
                repo_url,
                CloneOptions(ref=trunk, filter_blobs=True),
            ) as ctx:
                git = GitOperations(ctx.path)

                # Fetch all branch refs so we can check them out
                await git._run("fetch", "origin", *[b["name"] for b in sorted_branches])

                results: list[RestackBranchResult] = []
                chain_broken = False

                for i, branch_info in enumerate(sorted_branches):
                    name = branch_info["name"]
                    position = branch_info["position"]
                    old_sha = branch_info.get("head_sha")

                    if chain_broken:
                        results.append(
                            RestackBranchResult(
                                branch_name=name,
                                position=position,
                                old_sha=old_sha,
                                new_sha=None,
                                status="skipped",
                                error="Skipped due to earlier conflict",
                            )
                        )
                        continue

                    # Determine parent: trunk for position 1, previous branch otherwise
                    parent = trunk if i == 0 else sorted_branches[i - 1]["name"]

                    result = await self._rebase_branch(git, name, parent, position, old_sha)
                    results.append(result)

                    if result.status in ("conflict", "error"):
                        chain_broken = True

                # Force-push all successfully rebased branches
                push_errors: list[str] = []
                for result in results:
                    if result.status == "rebased":
                        push_result = await git.push(result.branch_name)
                        if not push_result.success:
                            result.status = "error"
                            result.error = f"Push failed: {push_result.error}"
                            push_errors.append(result.branch_name)

                all_ok = all(r.status in ("rebased", "up_to_date") for r in results)
                return RestackResult(
                    success=all_ok,
                    branches=results,
                    error=None if all_ok else "Some branches could not be restacked",
                )

        except CloneError as exc:
            logger.exception("Clone failed during restack")
            return RestackResult(
                success=False,
                error=f"Clone failed: {exc}",
            )

    async def _rebase_branch(
        self,
        git: GitOperations,
        branch_name: str,
        parent: str,
        position: int,
        old_sha: str | None,
    ) -> RestackBranchResult:
        """Rebase a single branch onto its parent."""
        # Checkout the branch
        checkout_result = await git.checkout(branch_name)
        if not checkout_result.success:
            return RestackBranchResult(
                branch_name=branch_name,
                position=position,
                old_sha=old_sha,
                new_sha=None,
                status="error",
                error=f"Checkout failed: {checkout_result.error}",
            )

        # Get current SHA before rebase
        pre_sha = await git.get_head_sha()

        # Rebase onto parent
        rebase_result = await git.rebase(parent)

        if rebase_result.has_conflicts:
            return RestackBranchResult(
                branch_name=branch_name,
                position=position,
                old_sha=old_sha,
                new_sha=None,
                status="conflict",
                error=rebase_result.error,
                conflicting_files=rebase_result.conflicting_files,
            )

        if not rebase_result.success:
            return RestackBranchResult(
                branch_name=branch_name,
                position=position,
                old_sha=old_sha,
                new_sha=None,
                status="error",
                error=f"Rebase failed: {rebase_result.error}",
            )

        # Get new SHA after rebase
        new_sha = await git.get_head_sha()

        # Check if the branch was already up to date
        if new_sha == pre_sha:
            return RestackBranchResult(
                branch_name=branch_name,
                position=position,
                old_sha=old_sha,
                new_sha=new_sha,
                status="up_to_date",
            )

        return RestackBranchResult(
            branch_name=branch_name,
            position=position,
            old_sha=old_sha,
            new_sha=new_sha,
            status="rebased",
        )
