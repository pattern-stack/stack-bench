"""CascadeWorkflow -- orchestration logic for merge cascades.

Coordinates MergeCascadeEntity with GitHubAdapter and CloneManager to
execute the retarget-rebase-gate-merge cycle for each branch in a stack.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

from features.check_runs.schemas.input import CheckRunCreate
from features.pull_requests.schemas.input import PullRequestUpdate
from molecules.providers.github_adapter import GitHubAPIError, parse_owner_repo
from molecules.services.clone_manager import CloneOptions, GitOperations

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from features.cascade_steps.models import CascadeStep
    from molecules.entities.merge_cascade_entity import MergeCascadeEntity
    from molecules.providers.github_adapter import GitHubAdapter
    from molecules.services.clone_manager import CloneManager

logger = logging.getLogger(__name__)

CHECK_RUN_NAME = "Stack Bench / merge-gate"


class _HasRepoUrl(Protocol):
    """Minimal protocol for workspace objects passed to workflow methods."""

    repo_url: str


class CascadeWorkflow:
    """Orchestrates the merge cascade: retarget, rebase, CI gate, merge.

    Uses MergeCascadeEntity for domain state transitions and GitHubAdapter
    for external API calls. CloneManager handles ephemeral clones for rebase.
    """

    def __init__(
        self,
        entity: MergeCascadeEntity,
        github: GitHubAdapter,
        clone_manager: CloneManager,
    ) -> None:
        self.entity = entity
        self.github = github
        self.clone_manager = clone_manager

    async def process_step(
        self,
        db: AsyncSession,
        cascade_id: UUID,
        step: CascadeStep,
        workspace: _HasRepoUrl,
    ) -> CascadeStep:
        """Process the next step in the cascade.

        1. Get branch and PR for this step
        2. Get the stack's trunk branch name
        3. Retarget PR to trunk
        4. Rebase branch onto trunk via ephemeral clone
        5. Create check run for CI gating
        """
        owner, repo = parse_owner_repo(workspace.repo_url)

        branch = await self.entity.branch_service.get(db, step.branch_id)
        assert branch is not None, f"Branch {step.branch_id} not found"

        pr = await self.entity.pr_service.get(db, step.pull_request_id) if step.pull_request_id else None

        # Get trunk from cascade's stack
        cascade = await self.entity.cascade_service.get(db, cascade_id)
        assert cascade is not None, f"Cascade {cascade_id} not found"

        stack = await self.entity.stack_service.get(db, cascade.stack_id)
        assert stack is not None, f"Stack {cascade.stack_id} not found"
        trunk: str = stack.trunk

        # 1. Retarget PR to trunk
        step.transition_to("retargeting")
        await db.flush()

        try:
            if pr and pr.external_id:
                await self.github.retarget_pr(owner, repo, pr.external_id, trunk)
                # Update PR base_ref in DB
                await self.entity.pr_service.update(db, pr.id, PullRequestUpdate(base_ref=trunk))
        except GitHubAPIError:
            logger.exception("Failed to retarget PR %s", pr.external_id if pr else "N/A")
            await self.entity.fail_step(db, step.id, error="Failed to retarget PR")
            return step

        # 2. Rebase branch onto trunk via ephemeral clone
        step.transition_to("rebasing")
        await db.flush()

        try:
            new_sha = await self._rebase_single_branch(workspace.repo_url, trunk, branch.name)
        except _RebaseConflictError as exc:
            await self.entity.conflict_step(
                db,
                step.id,
                error=str(exc),
                conflicting_files=exc.conflicting_files,
            )
            return step
        except Exception as exc:
            logger.exception("Rebase failed for branch %s", branch.name)
            await self.entity.fail_step(db, step.id, error=f"Rebase failed: {exc}")
            return step

        # Update SHAs
        branch.head_sha = new_sha
        step.head_sha = new_sha
        await db.flush()

        # 3. Create check run for CI gating
        step.transition_to("ci_pending")
        await db.flush()

        try:
            cr_data: dict[str, Any] = await self.github.create_check_run(owner, repo, CHECK_RUN_NAME, new_sha)
            external_cr_id = int(str(cr_data["id"]))
            step.check_run_external_id = external_cr_id
            await db.flush()

            # Record CheckRun in DB
            if pr:
                await self.entity.check_run_service.create(
                    db,
                    CheckRunCreate(
                        pull_request_id=pr.id,
                        external_id=external_cr_id,
                        head_sha=new_sha,
                        name=CHECK_RUN_NAME,
                        status="in_progress",
                    ),
                )
        except GitHubAPIError:
            logger.exception("Failed to create check run for %s", branch.name)
            await self.entity.fail_step(db, step.id, error="Failed to create check run")
            return step

        return step

    async def evaluate_step(
        self,
        db: AsyncSession,
        step: CascadeStep,
        workspace: _HasRepoUrl,
    ) -> CascadeStep:
        """Evaluate whether a step can proceed after CI completes.

        Called from webhook handler when check_suite.completed fires.

        1. Get all check suites for the step's head_sha
        2. Filter out our own check suite
        3. If all external suites passed: complete our check run, merge PR
        4. If any failed: fail the step
        """
        owner, repo = parse_owner_repo(workspace.repo_url)

        suites = await self.github.get_check_suites(owner, repo, step.head_sha)

        # Separate our suite from external ones
        external_suites = []
        for suite in suites:
            app = suite.get("app", {})
            app_name = app.get("name", "") if isinstance(app, dict) else ""
            if "Stack Bench" in app_name:
                continue
            external_suites.append(suite)

        # Check external suite results
        any_failed = False
        for suite in external_suites:
            conclusion = suite.get("conclusion")
            if conclusion and conclusion not in ("success", "neutral", "skipped"):
                any_failed = True
                break

        if any_failed:
            # Fail our check run
            if step.check_run_external_id:
                try:
                    await self.github.update_check_run(
                        owner,
                        repo,
                        step.check_run_external_id,
                        status="completed",
                        conclusion="failure",
                    )
                except GitHubAPIError:
                    logger.warning("Failed to update check run %s", step.check_run_external_id)

            await self.entity.fail_step(db, step.id, error="External CI checks failed")
            return step

        # All passed -- complete our check run and merge
        if step.check_run_external_id:
            try:
                await self.github.update_check_run(
                    owner,
                    repo,
                    step.check_run_external_id,
                    status="completed",
                    conclusion="success",
                )
            except GitHubAPIError:
                logger.warning("Failed to update check run %s", step.check_run_external_id)

        # Merge the PR
        pr = await self.entity.pr_service.get(db, step.pull_request_id) if step.pull_request_id else None
        if pr and pr.external_id:
            step.transition_to("completing")
            await db.flush()

            try:
                await self.github.merge_pr(owner, repo, pr.external_id, merge_method="squash")
            except GitHubAPIError:
                logger.exception("Failed to merge PR %s", pr.external_id)
                await self.entity.fail_step(db, step.id, error="Failed to merge PR")
                return step

            # Complete the step (transitions step, branch, PR states)
            await self.entity.complete_step(db, step.id)

        return step

    async def advance_cascade(
        self,
        db: AsyncSession,
        cascade_id: UUID,
        workspace: _HasRepoUrl,
    ) -> CascadeStep | None:
        """After a step merges, advance to the next step.

        1. Get the next pending step
        2. If no more: complete cascade, return None
        3. Otherwise: process it
        """
        next_step = await self.entity.step_service.get_pending_step(db, cascade_id)

        if next_step is None:
            cascade = await self.entity.cascade_service.get(db, cascade_id)
            if cascade is not None and cascade.state == "running":
                cascade.transition_to("completed")
                await db.flush()
            return None

        return await self.process_step(db, cascade_id, next_step, workspace)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _rebase_single_branch(
        self,
        repo_url: str,
        trunk: str,
        branch_name: str,
    ) -> str:
        """Rebase a single branch onto trunk using an ephemeral clone.

        Returns the new HEAD SHA after rebase + force-push.
        Raises _RebaseConflictError if there's a conflict.
        """
        async with self.clone_manager.clone(repo_url, CloneOptions(ref=trunk, filter_blobs=True)) as ctx:
            git = GitOperations(ctx.path)

            # Fetch the branch
            await git._run("fetch", "origin", branch_name)

            # Checkout the branch
            checkout = await git.checkout(branch_name)
            if not checkout.success:
                msg = f"Checkout failed: {checkout.error}"
                raise RuntimeError(msg)

            # Rebase onto trunk
            rebase = await git.rebase(trunk)

            if rebase.has_conflicts:
                raise _RebaseConflictError(
                    f"Conflict rebasing {branch_name} onto {trunk}",
                    conflicting_files=rebase.conflicting_files,
                )

            if not rebase.success:
                msg = f"Rebase failed: {rebase.error}"
                raise RuntimeError(msg)

            # Get new SHA
            new_sha = await git.get_head_sha()

            # Force-push
            push = await git.push(branch_name)
            if not push.success:
                msg = f"Push failed: {push.error}"
                raise RuntimeError(msg)

            return new_sha


class _RebaseConflictError(Exception):
    """Internal error for rebase conflicts."""

    def __init__(self, message: str, conflicting_files: list[str] | None = None) -> None:
        super().__init__(message)
        self.conflicting_files = conflicting_files or []
