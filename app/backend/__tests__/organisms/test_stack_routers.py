import pytest

from organisms.api.app import app


@pytest.mark.unit
def test_stacks_router_registered() -> None:
    """Verify /stacks routes exist."""
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/stacks" in r for r in routes)


@pytest.mark.unit
def test_stacks_branches_router_registered() -> None:
    """Verify /stacks/{stack_id}/branches routes exist."""
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/branches" in r for r in routes)


@pytest.mark.unit
def test_stacks_pr_router_registered() -> None:
    """Verify /stacks/{stack_id}/branches/{branch_id}/pr routes exist."""
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/pr" in r for r in routes)


# ---------------------------------------------------------------------------
# New workflow endpoints (push, submit, ready)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_push_endpoint_registered() -> None:
    """Verify POST /stacks/{stack_id}/push route exists."""
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/push" in r for r in routes)


@pytest.mark.unit
def test_submit_endpoint_registered() -> None:
    """Verify POST /stacks/{stack_id}/submit route exists."""
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/submit" in r for r in routes)


@pytest.mark.unit
def test_ready_endpoint_registered() -> None:
    """Verify POST /stacks/{stack_id}/ready route exists."""
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/ready" in r for r in routes)
