"""Tests for the SSE event stream router."""

import pytest

from organisms.api.app import create_app


@pytest.mark.unit
def test_event_stream_route_registered() -> None:
    """Verify the /events/stream route is present in the app."""
    app = create_app()
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/events/stream" in r for r in routes)
