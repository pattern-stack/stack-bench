"""Webhook router -- receives GitHub webhook events with HMAC verification."""

import hashlib
import hmac
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from config.settings import get_settings
from features.branches.service import BranchService
from features.cascade_steps.service import CascadeStepService
from features.pull_requests.service import PullRequestService
from features.workspaces.service import WorkspaceService
from molecules.entities.merge_cascade_entity import MergeCascadeEntity
from molecules.services.webhook_dispatcher import WebhookDispatcher
from molecules.workflows.cascade_workflow import CascadeWorkflow
from organisms.api.dependencies import CloneManagerDep, DatabaseSession, GitHubAdapterDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_signature(payload_body: bytes, secret: str, signature_header: str) -> bool:
    """Verify HMAC-SHA256 signature from GitHub."""
    expected = "sha256=" + hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def get_webhook_dispatcher(
    db: DatabaseSession,
    github: GitHubAdapterDep,
    clone_manager: CloneManagerDep,
) -> WebhookDispatcher:
    """Build the webhook dispatcher with all its dependencies."""
    entity = MergeCascadeEntity(db)
    workflow = CascadeWorkflow(entity=entity, github=github, clone_manager=clone_manager)

    return WebhookDispatcher(
        cascade_workflow=workflow,
        cascade_step_service=CascadeStepService(),
        pull_request_service=PullRequestService(),
        workspace_service=WorkspaceService(),
        branch_service=BranchService(),
        db=db,
    )


WebhookDispatcherDep = Annotated[WebhookDispatcher, Depends(get_webhook_dispatcher)]


@router.post("/github")
async def github_webhook(request: Request, dispatcher: WebhookDispatcherDep) -> JSONResponse:
    """Receive GitHub webhook events.

    1. Read raw body bytes (needed for HMAC verification)
    2. Verify HMAC-SHA256 signature
    3. Dispatch to handler based on event type
    4. Return 200 OK (always, even if we ignore the event)
    """
    # 1. Read raw body
    payload_body = await request.body()

    # 2. Get signature header
    signature_header = request.headers.get("X-Hub-Signature-256", "")

    # 3. Get webhook secret
    settings = get_settings()
    webhook_secret = settings.WEBHOOK_SECRET

    # 4. Reject if no secret configured (don't silently accept)
    if not webhook_secret:
        logger.error("WEBHOOK_SECRET is not configured -- rejecting webhook")
        return JSONResponse(
            status_code=500,
            content={"error": "Webhook secret not configured"},
        )

    # 5. Verify HMAC signature
    if not _verify_signature(payload_body, webhook_secret, signature_header):
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid signature"},
        )

    # 6. Parse event type and body
    event_type = request.headers.get("X-GitHub-Event", "")
    payload = json.loads(payload_body)

    # 7. Dispatch
    result = await dispatcher.dispatch(event_type, payload)

    return JSONResponse(status_code=200, content=result)
