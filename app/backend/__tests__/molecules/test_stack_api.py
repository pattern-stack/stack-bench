from unittest.mock import AsyncMock

import pytest

from molecules.apis.stack_api import StackAPI
from molecules.entities.stack_entity import StackEntity


@pytest.mark.unit
def test_stack_api_init() -> None:
    """Verify StackAPI composes StackEntity."""
    db = AsyncMock()
    api = StackAPI(db)
    assert hasattr(api, "entity")


@pytest.mark.unit
def test_stack_api_has_entity() -> None:
    """Verify entity is correct type."""
    db = AsyncMock()
    api = StackAPI(db)
    assert isinstance(api.entity, StackEntity)
