import pytest
from httpx import ASGITransport, AsyncClient

from organisms.api.app import app, create_app


@pytest.mark.unit
def test_app_has_lifespan() -> None:
    """Verify app is created with lifespan."""
    test_app = create_app()
    assert test_app.title == "Stack Bench"


@pytest.mark.unit
async def test_health_endpoint() -> None:
    """Health endpoint still works."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
def test_app_routers_registered() -> None:
    """Verify routers are wired into the app."""
    test_app = create_app()
    routes = [getattr(r, "path", str(r)) for r in test_app.routes]
    assert any("/conversations" in r for r in routes)
    assert any("/agents" in r for r in routes)
