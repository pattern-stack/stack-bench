import pytest

from organisms.api.app import app


@pytest.mark.unit
async def test_projects_router_registered() -> None:
    """Verify project routes are registered."""
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/projects" in r for r in routes)
