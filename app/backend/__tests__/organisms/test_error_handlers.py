from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from molecules.exceptions import AgentNotFoundError, ConversationNotFoundError
from organisms.api.error_handlers import molecule_exception_handler


@pytest.mark.unit
async def test_conversation_not_found_returns_404() -> None:
    request = MagicMock()
    exc = ConversationNotFoundError(uuid4())
    response = await molecule_exception_handler(request, exc)
    assert response.status_code == 404


@pytest.mark.unit
async def test_agent_not_found_returns_404() -> None:
    request = MagicMock()
    exc = AgentNotFoundError("unknown", ["a", "b"])
    response = await molecule_exception_handler(request, exc)
    assert response.status_code == 404
