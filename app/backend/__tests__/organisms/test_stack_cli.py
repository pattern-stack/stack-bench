"""Unit tests for the Stack CLI organism (Typer commands).

All tests mock httpx to avoid real HTTP calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from organisms.cli.stack_commands import app

runner = CliRunner()


def _mock_response(json_data: dict | list, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_status_command_output() -> None:
    """Status command should display stack name, state, and branches."""
    detail_response = {
        "stack": {"name": "my-stack", "state": "active", "trunk": "main"},
        "branches": [
            {
                "branch": {"name": "feature/1", "state": "pushed"},
                "pull_request": None,
                "needs_restack": False,
            },
            {
                "branch": {"name": "feature/2", "state": "reviewing"},
                "pull_request": {"state": "draft", "external_id": 42},
                "needs_restack": True,
            },
        ],
    }

    mock_client = MagicMock()
    mock_client.get.return_value = _mock_response(detail_response)

    with patch("organisms.cli.stack_commands._get_client", return_value=mock_client):
        result = runner.invoke(app, ["status", "some-uuid"])

    assert result.exit_code == 0
    assert "my-stack" in result.output
    assert "active" in result.output
    assert "feature/1" in result.output
    assert "feature/2" in result.output
    assert "[needs restack]" in result.output


# ---------------------------------------------------------------------------
# push command
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_push_command_sends_correct_payload() -> None:
    """Push command should POST to /stacks/{id}/push with correct body."""
    push_response = {"stack_id": "uuid", "created_count": 1, "synced_count": 0, "branches": []}

    mock_client = MagicMock()
    mock_client.post.return_value = _mock_response(push_response)

    branches = '[{"name": "feature/1", "position": 1, "head_sha": "abc123"}]'

    with patch("organisms.cli.stack_commands._get_client", return_value=mock_client):
        result = runner.invoke(app, ["push", "stack-uuid", "ws-uuid", "--branches", branches])

    assert result.exit_code == 0
    assert "Pushed 1 new" in result.output

    # Verify the POST call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "/stacks/stack-uuid/push" in call_args[0][0]
    body = call_args[1]["json"]
    assert body["workspace_id"] == "ws-uuid"
    assert len(body["branches"]) == 1


# ---------------------------------------------------------------------------
# submit command
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_submit_command_output() -> None:
    """Submit command should display created PR info."""
    submit_response = {
        "stack_id": "uuid",
        "results": [
            {
                "branch": "feature/1",
                "action": "created",
                "pr_number": 42,
                "pr_url": "https://github.com/org/repo/pull/42",
            },
            {
                "branch": "feature/2",
                "action": "skipped",
                "reason": "already has PR",
            },
        ],
    }

    mock_client = MagicMock()
    mock_client.post.return_value = _mock_response(submit_response)

    with patch("organisms.cli.stack_commands._get_client", return_value=mock_client):
        result = runner.invoke(app, ["submit", "stack-uuid"])

    assert result.exit_code == 0
    assert "Created PR #42" in result.output
    assert "feature/1" in result.output
    assert "Skipped feature/2" in result.output


# ---------------------------------------------------------------------------
# ready command
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ready_command_output() -> None:
    """Ready command should display marked-ready info."""
    ready_response = {
        "stack_id": "uuid",
        "results": [
            {"branch": "feature/1", "action": "marked_ready", "pr_number": 42},
            {"branch": "feature/2", "action": "skipped", "reason": "pr_state=open"},
        ],
    }

    mock_client = MagicMock()
    mock_client.post.return_value = _mock_response(ready_response)

    with patch("organisms.cli.stack_commands._get_client", return_value=mock_client):
        result = runner.invoke(app, ["ready", "stack-uuid"])

    assert result.exit_code == 0
    assert "Marked PR #42 ready" in result.output
    assert "Skipped feature/2" in result.output
