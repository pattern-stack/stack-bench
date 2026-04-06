"""Tests for runner selection logic in ConversationRunner."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from molecules.runtime.conversation_runner import ConversationRunner


@pytest.mark.unit
def test_get_default_runner_returns_stub_when_no_api_key() -> None:
    """_get_default_runner should return StubRunner when ANTHROPIC_API_KEY is empty."""
    from molecules.runtime.stub_runner import StubRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    from unittest.mock import MagicMock

    mock_settings = MagicMock()
    mock_settings.ANTHROPIC_API_KEY = ""

    with patch("config.settings.get_settings", return_value=mock_settings):
        result = runner._get_default_runner()

    assert isinstance(result, StubRunner)


@pytest.mark.unit
def test_get_default_runner_returns_agent_runner_when_api_key_set() -> None:
    """_get_default_runner should return AgentRunner when ANTHROPIC_API_KEY is set."""
    from agentic_patterns.core.systems.runners.agent import AgentRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    from unittest.mock import MagicMock

    mock_settings = MagicMock()
    mock_settings.ANTHROPIC_API_KEY = "sk-ant-test-key"

    with patch("config.settings.get_settings", return_value=mock_settings):
        result = runner._get_default_runner()

    assert isinstance(result, AgentRunner)
