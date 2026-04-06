"""Tests for POST /conversations/{id}/send streaming endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from starlette.testclient import TestClient


def _make_conversation_detail() -> dict:
    """Build a minimal ConversationDetailResponse-like dict."""
    conv_id = uuid4()
    return {
        "id": str(conv_id),
        "agent_name": "orchestrator",
        "model": "claude-sonnet-4-20250514",
        "state": "active",
        "exchange_count": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "messages": [],
    }


@pytest.mark.unit
async def test_send_endpoint_returns_streaming_response() -> None:
    """POST /conversations/{id}/send should return a StreamingResponse."""
    from organisms.api.routers.conversations import router

    conv_id = uuid4()

    # Mock the ConversationRunner.send() to yield SSE chunks
    async def mock_send(cid, message, **kwargs):
        yield 'event: agent.message.chunk\ndata: {"delta": "Hello"}\n\n'
        yield 'event: agent.message.complete\ndata: {"content": "Hello"}\n\n'

    mock_runner = MagicMock()
    mock_runner.send = mock_send

    # Mock ConversationAPI.get to not raise (validates conversation exists)
    mock_api = AsyncMock()
    mock_api.get = AsyncMock(return_value=_make_conversation_detail())

    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    from organisms.api.dependencies import get_conversation_api, get_conversation_runner

    app.dependency_overrides[get_conversation_runner] = lambda: mock_runner
    app.dependency_overrides[get_conversation_api] = lambda: mock_api

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/conversations/{conv_id}/send",
            json={"message": "Hello"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = response.text
        assert "agent.message.chunk" in body
        assert "agent.message.complete" in body


@pytest.mark.unit
async def test_send_endpoint_broadcasts_to_conversation_channel() -> None:
    """SSE chunks should be broadcast to conversation:{id} channel."""
    conv_id = uuid4()

    async def mock_send(cid, message, **kwargs):
        yield 'event: agent.message.chunk\ndata: {"delta": "Hi"}\n\n'
        yield 'event: agent.message.complete\ndata: {"content": "Hi"}\n\n'

    mock_runner = MagicMock()
    mock_runner.send = mock_send

    mock_api = AsyncMock()
    mock_api.get = AsyncMock(return_value=_make_conversation_detail())

    mock_broadcast = AsyncMock()

    from fastapi import FastAPI

    from organisms.api.dependencies import get_conversation_api, get_conversation_runner
    from organisms.api.routers.conversations import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_conversation_runner] = lambda: mock_runner
    app.dependency_overrides[get_conversation_api] = lambda: mock_api

    with patch(
        "organisms.api.routers.conversations.get_broadcast",
        return_value=mock_broadcast,
    ):
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/conversations/{conv_id}/send",
                json={"message": "Hi"},
            )
            assert response.status_code == 200

        # Verify broadcast was called for each SSE chunk
        assert mock_broadcast.broadcast.call_count >= 2
        # All broadcasts should target the conversation channel
        for c in mock_broadcast.broadcast.call_args_list:
            assert c[0][0] == f"conversation:{conv_id}"
