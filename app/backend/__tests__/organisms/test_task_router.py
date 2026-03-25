import pytest

from organisms.api.app import app
from organisms.api.routers.tasks import router


@pytest.mark.unit
def test_task_router_has_expected_routes() -> None:
    """Verify the tasks router exposes core task CRUD paths."""
    paths = [r.path for r in router.routes]
    assert "/tasks/" in paths  # POST /tasks, GET /tasks
    assert "/tasks/{task_id}" in paths  # GET, PUT, DELETE
    assert "/tasks/{task_id}/transition" in paths


@pytest.mark.unit
def test_task_router_has_project_routes() -> None:
    """Verify project sub-routes exist."""
    paths = [r.path for r in router.routes]
    assert "/tasks/projects" in paths
    assert "/tasks/projects/{project_id}" in paths


@pytest.mark.unit
def test_task_router_has_sprint_routes() -> None:
    """Verify sprint sub-routes exist."""
    paths = [r.path for r in router.routes]
    assert "/tasks/sprints" in paths
    assert "/tasks/sprints/{sprint_id}" in paths
    assert "/tasks/sprints/active" in paths


@pytest.mark.unit
def test_task_router_has_comment_routes() -> None:
    """Verify comment sub-routes exist."""
    paths = [r.path for r in router.routes]
    assert "/tasks/{task_id}/comments" in paths


@pytest.mark.unit
def test_task_router_has_tag_routes() -> None:
    """Verify tag sub-routes exist."""
    paths = [r.path for r in router.routes]
    assert "/tasks/{task_id}/tags" in paths
    assert "/tasks/{task_id}/tags/{tag_id}" in paths


@pytest.mark.unit
def test_task_router_has_sync_routes() -> None:
    """Verify sync sub-routes exist."""
    paths = [r.path for r in router.routes]
    assert "/tasks/sync" in paths
    assert "/tasks/{task_id}/sync" in paths


@pytest.mark.unit
def test_tasks_router_registered_in_app() -> None:
    """Verify /tasks routes are registered on the FastAPI app."""
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/tasks" in r for r in routes)


@pytest.mark.unit
def test_task_management_api_dep_exists() -> None:
    """Verify the DI dependency function exists and is callable."""
    from organisms.api.dependencies import get_task_management_api

    assert callable(get_task_management_api)


@pytest.mark.unit
def test_task_management_api_dep_type_alias_exists() -> None:
    """Verify the TaskManagementAPIDep type alias is importable."""
    from organisms.api.dependencies import TaskManagementAPIDep

    assert TaskManagementAPIDep is not None


@pytest.mark.unit
def test_error_handlers_include_task_exceptions() -> None:
    """Verify task-related exceptions are mapped in error_handlers."""
    from molecules.exceptions import (
        RelationCycleError,
        SprintNotFoundError,
        SyncNotConfiguredError,
        TaskHasBlockersError,
        TaskNotFoundError,
        TaskProjectNotFoundError,
    )
    from organisms.api.error_handlers import EXCEPTION_MAP

    assert TaskNotFoundError in EXCEPTION_MAP
    assert TaskProjectNotFoundError in EXCEPTION_MAP
    assert SprintNotFoundError in EXCEPTION_MAP
    assert TaskHasBlockersError in EXCEPTION_MAP
    assert RelationCycleError in EXCEPTION_MAP
    assert SyncNotConfiguredError in EXCEPTION_MAP
