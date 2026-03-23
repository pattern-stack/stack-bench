"""Tests for EphemeralCloneManager and GitOperations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from molecules.services.clone_manager import (
    CloneContext,
    CloneError,
    CloneManager,
    CloneOptions,
    GitOperations,
    GitResult,
    RebaseResult,
)

# ---------------------------------------------------------------------------
# CloneOptions defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_clone_options_defaults() -> None:
    """CloneOptions has sensible defaults."""
    opts = CloneOptions()
    assert opts.ref == "main"
    assert opts.depth is None
    assert opts.sparse_paths is None
    assert opts.filter_blobs is True


@pytest.mark.unit
def test_clone_options_custom() -> None:
    """CloneOptions accepts custom values."""
    opts = CloneOptions(ref="feature/x", depth=1, sparse_paths=["src/"], filter_blobs=False)
    assert opts.ref == "feature/x"
    assert opts.depth == 1
    assert opts.sparse_paths == ["src/"]
    assert opts.filter_blobs is False


# ---------------------------------------------------------------------------
# CloneContext
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_clone_context_fields() -> None:
    """CloneContext captures clone metadata."""
    ctx = CloneContext(
        path=Path("/tmp/test-clone"),
        repo_url="https://github.com/org/repo.git",
        ref="main",
        created_at=datetime.now(tz=UTC),
        clone_id="abc123",
    )
    assert ctx.path == Path("/tmp/test-clone")
    assert ctx.repo_url == "https://github.com/org/repo.git"
    assert ctx.ref == "main"
    assert ctx.clone_id == "abc123"


# ---------------------------------------------------------------------------
# GitResult / RebaseResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_git_result_success() -> None:
    """GitResult tracks command outcomes."""
    r = GitResult(success=True, output="ok")
    assert r.success is True
    assert r.error is None


@pytest.mark.unit
def test_rebase_result_conflict() -> None:
    """RebaseResult can indicate conflicts."""
    r = RebaseResult(success=False, output="", has_conflicts=True, conflicting_files=["a.py"])
    assert r.has_conflicts is True
    assert r.conflicting_files == ["a.py"]


# ---------------------------------------------------------------------------
# CloneManager -- clone lifecycle
# ---------------------------------------------------------------------------


def _make_proc_mock(
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> AsyncMock:
    """Create a mock async subprocess."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    proc.returncode = returncode
    return proc


@pytest.mark.unit
async def test_clone_manager_creates_and_cleans_up(tmp_path: Path) -> None:
    """Clone context manager creates directory and cleans up."""
    manager = CloneManager(base_dir=tmp_path, max_clones=5)

    proc_mock = _make_proc_mock()
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock):
        async with manager.clone("https://github.com/org/repo.git") as ctx:
            assert ctx.path.exists()
            assert ctx.repo_url == "https://github.com/org/repo.git"
            assert ctx.ref == "main"
            clone_path = ctx.path

        assert not clone_path.exists()


@pytest.mark.unit
async def test_clone_manager_cleanup_on_exception(tmp_path: Path) -> None:
    """Clone directory is cleaned up even when an exception occurs."""
    manager = CloneManager(base_dir=tmp_path, max_clones=5)

    proc_mock = _make_proc_mock()
    clone_path: Path | None = None

    with (
        pytest.raises(RuntimeError, match="test error"),
        patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock),
    ):
        async with manager.clone("https://github.com/org/repo.git") as ctx:
            clone_path = ctx.path
            raise RuntimeError("test error")

    assert clone_path is not None
    assert not clone_path.exists()


@pytest.mark.unit
async def test_clone_manager_tracks_active_clones(tmp_path: Path) -> None:
    """Active clones are tracked and removed after cleanup."""
    manager = CloneManager(base_dir=tmp_path, max_clones=5)

    proc_mock = _make_proc_mock()
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock):
        async with manager.clone("https://github.com/org/repo.git") as ctx:
            assert len(manager.active_clones) == 1
            assert ctx.clone_id in manager.active_clones

        assert len(manager.active_clones) == 0


@pytest.mark.unit
async def test_clone_manager_max_clones_enforced(tmp_path: Path) -> None:
    """Exceeding max_clones raises CloneError."""
    manager = CloneManager(base_dir=tmp_path, max_clones=1)

    proc_mock = _make_proc_mock()
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock):
        async with manager.clone("https://github.com/org/repo.git"):
            with pytest.raises(CloneError, match="Maximum concurrent clones"):
                async with manager.clone("https://github.com/org/repo2.git"):
                    pass  # Should not reach here


@pytest.mark.unit
async def test_clone_manager_clone_failure(tmp_path: Path) -> None:
    """CloneError raised when git clone fails."""
    manager = CloneManager(base_dir=tmp_path, max_clones=5)

    proc_mock = _make_proc_mock(stderr="fatal: repo not found", returncode=128)
    with (
        patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock),
        pytest.raises(CloneError, match="Clone failed"),
    ):
        async with manager.clone("https://github.com/org/bad-repo.git"):
            pass


@pytest.mark.unit
async def test_clone_manager_builds_correct_clone_command(tmp_path: Path) -> None:
    """Verify the git clone command is constructed properly."""
    manager = CloneManager(base_dir=tmp_path, max_clones=5)

    proc_mock = _make_proc_mock()
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock) as mock_exec:
        async with manager.clone(
            "https://github.com/org/repo.git",
            CloneOptions(ref="develop", depth=1, filter_blobs=True),
        ):
            pass

        call_args = mock_exec.call_args_list[0]
        args = call_args[0]
        assert args[0] == "git"
        assert "clone" in args
        assert "--single-branch" in args
        assert "--branch" in args
        assert "develop" in args
        assert "--filter=blob:none" in args
        assert "--depth" in args
        assert "1" in args


@pytest.mark.unit
async def test_clone_manager_no_filter_blobs(tmp_path: Path) -> None:
    """When filter_blobs=False, --filter flag is omitted."""
    manager = CloneManager(base_dir=tmp_path, max_clones=5)

    proc_mock = _make_proc_mock()
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock) as mock_exec:
        async with manager.clone(
            "https://github.com/org/repo.git",
            CloneOptions(filter_blobs=False),
        ):
            pass

        call_args = mock_exec.call_args_list[0]
        args = call_args[0]
        assert "--filter=blob:none" not in args


@pytest.mark.unit
async def test_clone_manager_github_token_injection(tmp_path: Path) -> None:
    """GitHub token is injected into the clone URL."""
    manager = CloneManager(base_dir=tmp_path, max_clones=5, github_token="ghp_test123")

    proc_mock = _make_proc_mock()
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock) as mock_exec:
        async with manager.clone("https://github.com/org/repo.git"):
            pass

        call_args = mock_exec.call_args_list[0]
        args = call_args[0]
        url_arg = [a for a in args if "github.com" in a][0]
        assert "x-access-token:ghp_test123@github.com" in url_arg


@pytest.mark.unit
async def test_clone_manager_stale_cleanup(tmp_path: Path) -> None:
    """cleanup_stale removes directories older than TTL."""
    manager = CloneManager(base_dir=tmp_path, max_clones=5, ttl_seconds=0)

    stale_dir = tmp_path / "stale-clone"
    stale_dir.mkdir(parents=True)

    old_ctx = CloneContext(
        path=stale_dir,
        repo_url="https://github.com/org/repo.git",
        ref="main",
        created_at=datetime(2020, 1, 1, tzinfo=UTC),
        clone_id="stale-id",
    )
    manager._active[old_ctx.clone_id] = old_ctx

    await manager.cleanup_stale()

    assert not stale_dir.exists()
    assert "stale-id" not in manager._active


# ---------------------------------------------------------------------------
# GitOperations
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_git_operations_checkout() -> None:
    """GitOperations.checkout runs git checkout."""
    git = GitOperations(Path("/tmp/fake-clone"))

    proc_mock = _make_proc_mock()
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock) as mock_exec:
        result = await git.checkout("feature-branch")

        assert result.success is True
        call_args = mock_exec.call_args[0]
        assert call_args == ("git", "checkout", "feature-branch")


@pytest.mark.unit
async def test_git_operations_rebase_success() -> None:
    """GitOperations.rebase returns success result."""
    git = GitOperations(Path("/tmp/fake-clone"))

    proc_mock = _make_proc_mock(stdout="Successfully rebased")
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock):
        result = await git.rebase("main")

        assert result.success is True
        assert result.has_conflicts is False


@pytest.mark.unit
async def test_git_operations_rebase_conflict() -> None:
    """GitOperations.rebase detects conflicts."""
    git = GitOperations(Path("/tmp/fake-clone"))

    rebase_proc = _make_proc_mock(stderr="CONFLICT (content): Merge conflict in a.py", returncode=1)
    diff_proc = _make_proc_mock(stdout="a.py\nb.py")
    abort_proc = _make_proc_mock()

    call_count = 0

    async def mock_exec(*args: str, **kwargs: object) -> AsyncMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return rebase_proc
        elif call_count == 2:  # noqa: RET505
            return diff_proc
        return abort_proc

    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", side_effect=mock_exec):
        result = await git.rebase("main")

        assert result.success is False
        assert result.has_conflicts is True
        assert result.conflicting_files == ["a.py", "b.py"]


@pytest.mark.unit
async def test_git_operations_commit() -> None:
    """GitOperations.commit stages files and creates commit."""
    git = GitOperations(Path("/tmp/fake-clone"))

    add_proc = _make_proc_mock()
    commit_proc = _make_proc_mock(stdout="abc1234")

    call_count = 0

    async def mock_exec(*args: str, **kwargs: object) -> AsyncMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return add_proc
        return commit_proc

    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", side_effect=mock_exec):
        sha = await git.commit("fix: something", paths=["src/a.py"])

        assert sha == "abc1234"


@pytest.mark.unit
async def test_git_operations_push() -> None:
    """GitOperations.push uses force-with-lease by default."""
    git = GitOperations(Path("/tmp/fake-clone"))

    proc_mock = _make_proc_mock()
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock) as mock_exec:
        result = await git.push("feature-branch")

        assert result.success is True
        call_args = mock_exec.call_args[0]
        assert "--force-with-lease" in call_args


@pytest.mark.unit
async def test_git_operations_push_no_force() -> None:
    """GitOperations.push without force-with-lease when disabled."""
    git = GitOperations(Path("/tmp/fake-clone"))

    proc_mock = _make_proc_mock()
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock) as mock_exec:
        await git.push("feature-branch", force_with_lease=False)

        call_args = mock_exec.call_args[0]
        assert "--force-with-lease" not in call_args


@pytest.mark.unit
async def test_git_operations_push_failure() -> None:
    """GitOperations.push returns failure when push is rejected."""
    git = GitOperations(Path("/tmp/fake-clone"))

    proc_mock = _make_proc_mock(stderr="rejected", returncode=1)
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock):
        result = await git.push("feature-branch")

        assert result.success is False
        assert "rejected" in (result.error or "")


@pytest.mark.unit
async def test_git_operations_get_head_sha() -> None:
    """GitOperations.get_head_sha returns current HEAD SHA."""
    git = GitOperations(Path("/tmp/fake-clone"))

    proc_mock = _make_proc_mock(stdout="a" * 40)
    with patch("molecules.services.clone_manager.asyncio.create_subprocess_exec", return_value=proc_mock) as mock_exec:
        sha = await git.get_head_sha()

        assert sha == "a" * 40
        call_args = mock_exec.call_args[0]
        assert call_args == ("git", "rev-parse", "HEAD")
