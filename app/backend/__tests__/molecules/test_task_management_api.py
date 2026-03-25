from unittest.mock import AsyncMock

import pytest

from molecules.apis.task_management_api import TaskManagementAPI
from molecules.entities.task_management_entity import TaskManagementEntity
from molecules.services.sync_engine import SyncEngine


@pytest.mark.unit
def test_task_management_api_init() -> None:
    """Verify TaskManagementAPI composes TaskManagementEntity."""
    db = AsyncMock()
    api = TaskManagementAPI(db)
    assert hasattr(api, "entity")


@pytest.mark.unit
def test_task_management_api_has_entity() -> None:
    """Verify entity is correct type."""
    db = AsyncMock()
    api = TaskManagementAPI(db)
    assert isinstance(api.entity, TaskManagementEntity)


@pytest.mark.unit
def test_task_management_api_with_adapter_creates_sync_engine() -> None:
    """Verify passing an adapter creates a SyncEngine."""
    db = AsyncMock()
    adapter = AsyncMock()
    api = TaskManagementAPI(db, adapter=adapter)
    assert api.sync is not None
    assert isinstance(api.sync, SyncEngine)


@pytest.mark.unit
def test_task_management_api_without_adapter_has_no_sync() -> None:
    """Verify no adapter means sync is None."""
    db = AsyncMock()
    api = TaskManagementAPI(db)
    assert api.sync is None
