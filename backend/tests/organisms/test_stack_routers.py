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
