import pytest
from httpx import ASGITransport, AsyncClient

from organisms.api.app import app


@pytest.mark.unit
async def test_health_still_works() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.unit
async def test_conversations_router_registered() -> None:
    """Verify conversation routes are registered."""
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/conversations" in r for r in routes)


@pytest.mark.unit
async def test_agents_router_registered() -> None:
    """Verify agent routes are registered."""
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/agents" in r for r in routes)
