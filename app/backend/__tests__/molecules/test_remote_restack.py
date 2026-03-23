"""Tests for RemoteRestackService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from molecules.services.clone_manager import (
    CloneContext,
    CloneError,
    CloneManager,
)
from molecules.services.remote_restack import (
    RemoteRestackService,
    RestackResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_branches(names: list[str]) -> list[dict]:
    """Build a branches list from names, assigning positions 1..N."""
    return [
        {"name": name, "position": i + 1, "head_sha": f"sha_{i}"}
        for i, name in enumerate(names)
    ]


def _mock_clone_manager(clone_path: Path = Path("/tmp/fake-clone")) -> CloneManager:
    """Create a CloneManager whose clone() yields a fake CloneContext."""
    from contextlib import asynccontextmanager
    from datetime import UTC, datetime

    ctx = CloneContext(
        path=clone_path,
        repo_url="https://github.com/org/repo.git",
        ref="main",
        created_at=datetime.now(tz=UTC),
        clone_id="test123",
    )

    manager = MagicMock(spec=CloneManager)

    @asynccontextmanager
    async def _clone(*args, **kwargs):
        yield ctx

    manager.clone = _clone
    return manager


def _mock_clone_manager_failing() -> CloneManager:
    """Create a CloneManager whose clone() raises CloneError."""
    from contextlib import asynccontextmanager

    manager = MagicMock(spec=CloneManager)

    @asynccontextmanager
    async def _clone(*args, **kwargs):
        raise CloneError("clone failed: repo not found")
        yield  # noqa: F841 — required for async generator syntax

    manager.clone = _clone
    return manager


# ---------------------------------------------------------------------------
# All branches rebase successfully
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_restack_all_branches_succeed() -> None:
    """All branches rebase and push successfully."""
    manager = _mock_clone_manager()
    svc = RemoteRestackService(manager)

    branches = _make_branches(["feat/1-first", "feat/2-second", "feat/3-third"])

    # rev-parse is called twice per branch (before + after rebase).
    # Returning a different value each time means SHA changed = "rebased".
    rev_parse_count = 0

    async def mock_git_run(self, *args):
        nonlocal rev_parse_count
        cmd = args[0] if args else ""

        if cmd == "fetch":
            return ("", "", 0)
        if cmd == "checkout":
            return ("", "", 0)
        if cmd == "rev-parse":
            rev_parse_count += 1
            return (f"sha_{rev_parse_count}", "", 0)
        if cmd == "rebase":
            return ("Successfully rebased", "", 0)
        if cmd == "push":
            return ("", "", 0)
        return ("", "", 0)

    with patch("molecules.services.clone_manager.GitOperations._run", mock_git_run):
        result = await svc.restack(
            "https://github.com/org/repo.git",
            "main",
            branches,
        )

    assert result.success is True
    assert len(result.branches) == 3
    assert all(br.status == "rebased" for br in result.branches)
    assert result.error is None


# ---------------------------------------------------------------------------
# Conflict on middle branch stops chain
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_restack_conflict_stops_chain() -> None:
    """Conflict on branch 2 causes branch 3 to be skipped."""
    manager = _mock_clone_manager()
    svc = RemoteRestackService(manager)

    branches = _make_branches(["feat/1-first", "feat/2-second", "feat/3-third"])

    rebase_count = 0
    rev_parse_count = 0

    async def mock_git_run(self, *args):
        nonlocal rebase_count, rev_parse_count
        cmd = args[0] if args else ""

        if cmd == "fetch":
            return ("", "", 0)
        if cmd == "checkout":
            return ("", "", 0)
        if cmd == "rev-parse":
            rev_parse_count += 1
            return (f"sha_{rev_parse_count}", "", 0)
        if cmd == "rebase":
            rebase_count += 1
            if rebase_count == 2:
                # Second rebase hits a conflict
                return ("", "CONFLICT (content): Merge conflict in file.py", 1)
            return ("Successfully rebased", "", 0)
        if cmd == "diff":
            # Conflicting files query after conflict
            return ("file.py", "", 0)
        if cmd == "push":
            return ("", "", 0)
        return ("", "", 0)

    with patch("molecules.services.clone_manager.GitOperations._run", mock_git_run):
        result = await svc.restack(
            "https://github.com/org/repo.git",
            "main",
            branches,
        )

    assert result.success is False
    assert len(result.branches) == 3

    # First branch rebased ok
    assert result.branches[0].status in ("rebased", "up_to_date")
    # Second branch had conflict
    assert result.branches[1].status == "conflict"
    assert "file.py" in result.branches[1].conflicting_files
    # Third branch was skipped
    assert result.branches[2].status == "skipped"


# ---------------------------------------------------------------------------
# Up-to-date branches detected
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_restack_up_to_date() -> None:
    """Branch already on top of parent returns up_to_date."""
    manager = _mock_clone_manager()
    svc = RemoteRestackService(manager)

    branches = _make_branches(["feat/1-only"])

    async def mock_git_run(self, *args):
        cmd = args[0] if args else ""

        if cmd == "fetch":
            return ("", "", 0)
        if cmd == "checkout":
            return ("", "", 0)
        if cmd == "rev-parse":
            # Same SHA before and after rebase = up to date
            return ("same_sha_abc", "", 0)
        if cmd == "rebase":
            return ("Current branch feat/1-only is up to date.", "", 0)
        return ("", "", 0)

    with patch("molecules.services.clone_manager.GitOperations._run", mock_git_run):
        result = await svc.restack(
            "https://github.com/org/repo.git",
            "main",
            branches,
        )

    assert result.success is True
    assert len(result.branches) == 1
    assert result.branches[0].status == "up_to_date"


# ---------------------------------------------------------------------------
# Clone failure
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_restack_clone_failure() -> None:
    """CloneError during clone returns failure result."""
    manager = _mock_clone_manager_failing()
    svc = RemoteRestackService(manager)

    branches = _make_branches(["feat/1-first"])

    result = await svc.restack(
        "https://github.com/org/repo.git",
        "main",
        branches,
    )

    assert result.success is False
    assert "Clone failed" in (result.error or "")
    assert len(result.branches) == 0


# ---------------------------------------------------------------------------
# Push failure
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_restack_push_failure() -> None:
    """Push failure marks the branch as error."""
    manager = _mock_clone_manager()
    svc = RemoteRestackService(manager)

    branches = _make_branches(["feat/1-first"])
    rev_parse_count = 0

    async def mock_git_run(self, *args):
        nonlocal rev_parse_count
        cmd = args[0] if args else ""

        if cmd == "fetch":
            return ("", "", 0)
        if cmd == "checkout":
            return ("", "", 0)
        if cmd == "rev-parse":
            rev_parse_count += 1
            # Return different SHAs before (call 1) vs after (call 2) rebase
            return (f"sha_{rev_parse_count}", "", 0)
        if cmd == "rebase":
            return ("Successfully rebased", "", 0)
        if cmd == "push":
            return ("", "rejected: stale info", 1)
        return ("", "", 0)

    with patch("molecules.services.clone_manager.GitOperations._run", mock_git_run):
        result = await svc.restack(
            "https://github.com/org/repo.git",
            "main",
            branches,
        )

    assert result.success is False
    assert len(result.branches) == 1
    assert result.branches[0].status == "error"
    assert "Push failed" in (result.branches[0].error or "")


# ---------------------------------------------------------------------------
# Dataclass defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_restack_result_defaults() -> None:
    """RestackResult has sensible defaults."""
    r = RestackResult(success=True)
    assert r.branches == []
    assert r.error is None
