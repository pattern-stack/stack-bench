"""WebhookDispatcher -- routes GitHub webhook events to domain handlers.

Lives at the molecule layer, composing feature services and the cascade
workflow to handle check_suite.completed and pull_request.merged events.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from features.branches.service import BranchService
    from features.cascade_steps.service import CascadeStepService
    from features.pull_requests.service import PullRequestService
    from features.workspaces.service import WorkspaceService
    from molecules.workflows.cascade_workflow import CascadeWorkflow

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Routes GitHub webhook events to the appropriate domain handler.

    Composes CascadeWorkflow and feature services to handle:
    - check_suite.completed: evaluate whether a cascade step can proceed
    - pull_request.closed+merged: complete a cascade step and advance
    """

    def __init__(
        self,
        *,
        cascade_workflow: CascadeWorkflow,
        cascade_step_service: CascadeStepService,
        pull_request_service: PullRequestService,
        workspace_service: WorkspaceService,
        branch_service: BranchService,
        db: AsyncSession,
    ) -> None:
        self.cascade_workflow = cascade_workflow
        self.cascade_step_service = cascade_step_service
        self.pull_request_service = pull_request_service
        self.workspace_service = workspace_service
        self.branch_service = branch_service
        self.db = db

    async def dispatch(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Route a webhook event to the appropriate handler.

        Returns a result dict indicating whether the event was handled.
        """
        if event_type == "check_suite" and payload.get("action") == "completed":
            return await self._handle_check_suite_completed(payload)

        if (
            event_type == "pull_request"
            and payload.get("action") == "closed"
            and payload.get("pull_request", {}).get("merged")
        ):
            return await self._handle_pull_request_merged(payload)

        return {"handled": False, "reason": "unhandled event"}

    async def _handle_check_suite_completed(self, payload: dict[str, Any]) -> dict[str, Any]:
        """External CI finished -- evaluate if cascade step can proceed.

        1. Extract head_sha from payload
        2. Find cascade step by head_sha
        3. If no step found or not in ci_pending state, ignore (idempotent)
        4. Get workspace for the step's branch
        5. Call cascade_workflow.evaluate_step()
        6. If step transitions to completing, advance cascade
        """
        head_sha = payload.get("check_suite", {}).get("head_sha")
        if not head_sha:
            return {"handled": False, "reason": "no head_sha in payload"}

        step = await self.cascade_step_service.get_by_head_sha(self.db, head_sha)
        if step is None:
            logger.debug("No cascade step found for head_sha=%s", head_sha)
            return {"handled": False, "reason": "no matching cascade step"}

        if step.state != "ci_pending":
            logger.debug("Step %s in state %s, not ci_pending -- ignoring", step.id, step.state)
            return {"handled": False, "reason": f"step in state {step.state}"}

        # Get workspace via branch
        workspace = await self._get_workspace_for_step(step)
        if workspace is None:
            logger.warning("No workspace found for step %s", step.id)
            return {"handled": False, "reason": "no workspace found"}

        # Evaluate the step
        evaluated = await self.cascade_workflow.evaluate_step(self.db, step, workspace)

        # If step transitioned to completing (PR merged by us), advance cascade
        if evaluated.state == "completing":
            await self.cascade_workflow.advance_cascade(self.db, step.cascade_id, workspace)

        return {"handled": True, "step_id": str(step.id), "new_state": evaluated.state}

    async def _handle_pull_request_merged(self, payload: dict[str, Any]) -> dict[str, Any]:
        """PR was merged on GitHub -- complete cascade step and advance.

        1. Extract PR number from payload
        2. Find PullRequest by external_id
        3. If not found, ignore
        4. Find cascade step by pull_request_id
        5. If no step or not in completing state, ignore (idempotent)
        6. Call entity.complete_step()
        7. Call cascade_workflow.advance_cascade()
        """
        pr_number = payload.get("pull_request", {}).get("number")
        if pr_number is None:
            return {"handled": False, "reason": "no PR number in payload"}

        pr = await self.pull_request_service.get_by_external_id(self.db, pr_number)
        if pr is None:
            logger.debug("No local PR found for external_id=%s", pr_number)
            return {"handled": False, "reason": "no matching pull request"}

        step = await self.cascade_step_service.get_by_pull_request(self.db, pr.id)
        if step is None:
            logger.debug("No cascade step found for PR %s", pr.id)
            return {"handled": False, "reason": "no matching cascade step"}

        if step.state != "completing":
            logger.debug("Step %s in state %s, not completing -- ignoring", step.id, step.state)
            return {"handled": False, "reason": f"step in state {step.state}"}

        # Get workspace via branch
        workspace = await self._get_workspace_for_step(step)
        if workspace is None:
            logger.warning("No workspace found for step %s", step.id)
            return {"handled": False, "reason": "no workspace found"}

        # Complete the step
        await self.cascade_workflow.entity.complete_step(self.db, step.id)

        # Advance the cascade
        await self.cascade_workflow.advance_cascade(self.db, step.cascade_id, workspace)

        return {"handled": True, "step_id": str(step.id), "action": "completed_and_advanced"}

    async def _get_workspace_for_step(self, step: Any) -> Any:
        """Resolve the workspace for a cascade step via its branch."""
        branch = await self.branch_service.get(self.db, step.branch_id)
        if branch is None:
            return None
        return await self.workspace_service.get(self.db, branch.workspace_id)
