"""Tests for webhook router -- HMAC verification and event dispatching."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from organisms.api.app import create_app
from organisms.api.routers.webhooks import get_webhook_dispatcher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_SECRET = "test-webhook-secret-123"


def _sign_payload(payload: bytes, secret: str) -> str:
    """Create a valid HMAC-SHA256 signature for a payload."""
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def _make_test_app(*, dispatcher_mock: AsyncMock | None = None):
    """Create a test app with dependency overrides to skip DB."""
    app = create_app()

    if dispatcher_mock is not None:
        app.dependency_overrides[get_webhook_dispatcher] = lambda: dispatcher_mock

    return app


# ---------------------------------------------------------------------------
# Signature verification tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_webhook_signature_valid() -> None:
    """Correct HMAC signature passes verification."""
    payload = json.dumps({"action": "completed", "check_suite": {"head_sha": "abc"}}).encode()
    signature = _sign_payload(payload, TEST_SECRET)

    mock_dispatcher = AsyncMock()
    mock_dispatcher.dispatch.return_value = {"handled": False, "reason": "unhandled event"}

    app = _make_test_app(dispatcher_mock=mock_dispatcher)

    with patch("organisms.api.routers.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = TEST_SECRET

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "check_suite",
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 200


@pytest.mark.unit
async def test_webhook_signature_invalid() -> None:
    """Wrong signature returns 401."""
    payload = json.dumps({"action": "completed"}).encode()
    bad_signature = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

    # No dispatcher needed -- should reject before dispatch
    app = _make_test_app(dispatcher_mock=AsyncMock())

    with patch("organisms.api.routers.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = TEST_SECRET

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-Hub-Signature-256": bad_signature,
                    "X-GitHub-Event": "check_suite",
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 401


@pytest.mark.unit
async def test_webhook_empty_secret_rejected() -> None:
    """Empty WEBHOOK_SECRET returns 500 -- don't silently accept."""
    payload = json.dumps({"action": "completed"}).encode()

    app = _make_test_app(dispatcher_mock=AsyncMock())

    with patch("organisms.api.routers.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = ""

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-Hub-Signature-256": "sha256=anything",
                    "X-GitHub-Event": "check_suite",
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 500


# ---------------------------------------------------------------------------
# Event dispatching tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_webhook_check_suite_completed_dispatched() -> None:
    """check_suite event with completed action is dispatched."""
    payload_dict = {"action": "completed", "check_suite": {"head_sha": "abc123"}}
    payload = json.dumps(payload_dict).encode()
    signature = _sign_payload(payload, TEST_SECRET)

    mock_dispatcher = AsyncMock()
    mock_dispatcher.dispatch.return_value = {"handled": True}

    app = _make_test_app(dispatcher_mock=mock_dispatcher)

    with patch("organisms.api.routers.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = TEST_SECRET

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "check_suite",
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 200
    mock_dispatcher.dispatch.assert_called_once_with("check_suite", payload_dict)


@pytest.mark.unit
async def test_webhook_pull_request_merged_dispatched() -> None:
    """pull_request event with merged PR is dispatched."""
    payload_dict = {
        "action": "closed",
        "pull_request": {"number": 42, "merged": True},
    }
    payload = json.dumps(payload_dict).encode()
    signature = _sign_payload(payload, TEST_SECRET)

    mock_dispatcher = AsyncMock()
    mock_dispatcher.dispatch.return_value = {"handled": True}

    app = _make_test_app(dispatcher_mock=mock_dispatcher)

    with patch("organisms.api.routers.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = TEST_SECRET

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 200
    mock_dispatcher.dispatch.assert_called_once_with("pull_request", payload_dict)


@pytest.mark.unit
async def test_webhook_unhandled_event_ignored() -> None:
    """Unknown event type returns 200 -- we always ack webhooks."""
    payload_dict = {"action": "something"}
    payload = json.dumps(payload_dict).encode()
    signature = _sign_payload(payload, TEST_SECRET)

    mock_dispatcher = AsyncMock()
    mock_dispatcher.dispatch.return_value = {"handled": False, "reason": "unhandled event"}

    app = _make_test_app(dispatcher_mock=mock_dispatcher)

    with patch("organisms.api.routers.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = TEST_SECRET

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "random_event",
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 200
