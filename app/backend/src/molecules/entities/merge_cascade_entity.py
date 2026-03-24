"""MergeCascadeEntity -- domain aggregate for merge cascade lifecycle.

Composes cascade, step, check-run, branch, PR, and stack services to
orchestrate the bottom-up merge of a stacked PR set with CI gating.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from features.branches.service import BranchService
from features.cascade_steps.schemas.input import CascadeStepCreate
from features.cascade_steps.service import CascadeStepService
from features.check_runs.service import CheckRunService
from features.merge_cascades.schemas.input import MergeCascadeCreate
from features.merge_cascades.service import MergeCascadeService
from features.pull_requests.service import PullRequestService
from features.stacks.service import StackService
from molecules.exceptions import MoleculeError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from features.cascade_steps.models import CascadeStep
    from features.merge_cascades.models import MergeCascade


class ActiveCascadeError(MoleculeError):
    """Raised when a cascade is already active for a stack."""

    def __init__(self, stack_id: UUID) -> None:
        super().__init__(f"Stack {stack_id} already has an active cascade")
        self.stack_id = stack_id


class InvalidBranchStateError(MoleculeError):
    """Raised when branches are not in the required state for a cascade."""

    def __init__(self, branch_name: str, state: str) -> None:
        super().__init__(f"Branch '{branch_name}' is in state '{state}', must be 'submitted'")
        self.branch_name = branch_name
        self.state = state


class MergeCascadeEntity:
    """Domain aggregate for merge cascade lifecycle.

    Coordinates cascade, step, check-run, branch, PR, and stack features
    into the merge-cascade domain concept.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cascade_service = MergeCascadeService()
        self.step_service = CascadeStepService()
        self.check_run_service = CheckRunService()
        self.branch_service = BranchService()
        self.pr_service = PullRequestService()
        self.stack_service = StackService()

    async def create_cascade(
        self,
        db: AsyncSession,
        stack_id: UUID,
        triggered_by: str,
    ) -> MergeCascade:
        """Create a cascade with steps for all unmerged branches.

        1. Verify no active cascade exists for this stack
        2. Get stack with all branches ordered by position
        3. Filter to unmerged branches only
        4. Validate all unmerged branches are in "submitted" state
        5. Create MergeCascade in "pending" state
        6. Create CascadeStep for each branch
        7. Transition cascade to "running"
        """
        # 1. Check for existing active cascade
        active = await self.cascade_service.get_active_for_stack(db, stack_id)
        if active is not None:
            raise ActiveCascadeError(stack_id)

        # 2. Get stack (validates existence) and branches
        await self.stack_service.get(db, stack_id)
        branches = await self.branch_service.list_by_stack(db, stack_id)

        # 3. Filter to unmerged branches
        unmerged = [b for b in branches if b.state != "merged"]

        # 4. Validate all are in "submitted" state
        for branch in unmerged:
            if branch.state != "submitted":
                raise InvalidBranchStateError(branch.name, branch.state)

        # 5. Create cascade
        cascade = await self.cascade_service.create(
            db,
            MergeCascadeCreate(stack_id=stack_id, triggered_by=triggered_by),
        )

        # 6. Create steps for each unmerged branch
        for branch in unmerged:
            pr = await self.pr_service.get_by_branch(db, branch.id)
            await self.step_service.create(
                db,
                CascadeStepCreate(
                    cascade_id=cascade.id,
                    branch_id=branch.id,
                    pull_request_id=pr.id if pr else None,
                    position=branch.position,
                    head_sha=branch.head_sha,
                ),
            )

        # 7. Transition to running
        cascade.transition_to("running")
        await db.flush()

        return cascade

    async def get_cascade_detail(self, db: AsyncSession, cascade_id: UUID) -> dict[str, Any]:
        """Get cascade with all steps and their branch/PR data."""
        cascade = await self.cascade_service.get(db, cascade_id)
        steps = await self.step_service.list_by_cascade(db, cascade_id)

        step_details = []
        for step in steps:
            branch = await self.branch_service.get(db, step.branch_id)
            pr = await self.pr_service.get(db, step.pull_request_id) if step.pull_request_id else None
            step_details.append(
                {
                    "step": step,
                    "branch": branch,
                    "pull_request": pr,
                }
            )

        return {
            "cascade": cascade,
            "steps": step_details,
        }

    async def cancel_cascade(self, db: AsyncSession, cascade_id: UUID) -> MergeCascade:
        """Cancel a running cascade.

        1. Transition cascade to "cancelled"
        2. Transition all pending steps to "skipped", fail active steps
        """
        cascade = await self.cascade_service.get(db, cascade_id)
        assert cascade is not None, f"Cascade {cascade_id} not found"
        cascade.transition_to("cancelled")

        steps = await self.step_service.list_by_cascade(db, cascade_id)
        terminal_states = {"merged", "conflict", "failed", "skipped"}
        for step in steps:
            if step.state in terminal_states:
                continue
            if step.state == "pending":
                step.transition_to("skipped")
            else:
                # Active steps (retargeting, rebasing, ci_pending, completing)
                # transition to "failed" since they can't go directly to "skipped"
                step.transition_to("failed")

        await db.flush()
        return cascade

    async def complete_step(self, db: AsyncSession, step_id: UUID) -> CascadeStep:
        """Mark a step as merged after PR merge.

        1. Transition step to "merged"
        2. Transition associated Branch to "merged"
        3. Transition associated PR: open -> approved -> merged
        4. Check if all steps are merged -> complete cascade
        """
        step = await self.step_service.get(db, step_id)
        assert step is not None, f"Step {step_id} not found"
        step.transition_to("merged")
        step.completed_at = datetime.now(tz=UTC)

        # Transition branch
        branch = await self.branch_service.get(db, step.branch_id)
        assert branch is not None, f"Branch {step.branch_id} not found"
        if branch.state != "merged":
            branch.transition_to("merged")

        # Transition PR through required states
        if step.pull_request_id:
            pr = await self.pr_service.get(db, step.pull_request_id)
            if pr is not None and pr.state == "open":
                pr.transition_to("approved")
            if pr is not None and pr.state == "approved":
                pr.transition_to("merged")

        # Check if cascade is complete
        all_steps = await self.step_service.list_by_cascade(db, step.cascade_id)
        all_merged = all(s.state == "merged" for s in all_steps)
        if all_merged:
            cascade = await self.cascade_service.get(db, step.cascade_id)
            assert cascade is not None, f"Cascade {step.cascade_id} not found"
            cascade.transition_to("completed")

        await db.flush()
        return step

    async def fail_step(self, db: AsyncSession, step_id: UUID, error: str) -> CascadeStep:
        """Mark a step as failed, fail cascade, skip remaining.

        1. Transition step to "failed"
        2. Transition cascade to "failed"
        3. Skip all remaining pending steps
        """
        step = await self.step_service.get(db, step_id)
        assert step is not None, f"Step {step_id} not found"
        step.transition_to("failed")
        step.error = error
        step.completed_at = datetime.now(tz=UTC)

        cascade = await self.cascade_service.get(db, step.cascade_id)
        assert cascade is not None, f"Cascade {step.cascade_id} not found"
        cascade.transition_to("failed")

        # Skip remaining pending steps
        all_steps = await self.step_service.list_by_cascade(db, step.cascade_id)
        for s in all_steps:
            if s.id != step.id and s.state == "pending":
                s.transition_to("skipped")

        await db.flush()
        return step

    async def conflict_step(
        self,
        db: AsyncSession,
        step_id: UUID,
        error: str,
        conflicting_files: list[str] | None = None,
    ) -> CascadeStep:
        """Mark a step as conflicted, fail cascade, skip remaining.

        Similar to fail_step but transitions to "conflict" state.
        """
        step = await self.step_service.get(db, step_id)
        assert step is not None, f"Step {step_id} not found"
        step.transition_to("conflict")
        step.error = error
        step.completed_at = datetime.now(tz=UTC)

        cascade = await self.cascade_service.get(db, step.cascade_id)
        assert cascade is not None, f"Cascade {step.cascade_id} not found"
        cascade.transition_to("failed")

        # Skip remaining pending steps
        all_steps = await self.step_service.list_by_cascade(db, step.cascade_id)
        for s in all_steps:
            if s.id != step.id and s.state == "pending":
                s.transition_to("skipped")

        await db.flush()
        return step
