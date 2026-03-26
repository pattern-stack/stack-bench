"""Workspace server -- lightweight FastAPI app running inside Cloud Run.

Provides file, git, worktree, and terminal access for agents working
on a repository. NOT part of the main stack-bench backend.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI

from server.routers import files, git, health, terminal, worktrees

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

WORKSPACE_ROOT = Path("/workspace")
MAIN_CHECKOUT = WORKSPACE_ROOT / "main"
WORKTREES_DIR = WORKSPACE_ROOT / "worktrees"


async def _clone_repo() -> None:
    """Clone the repository on startup if not already present."""
    repo_url = os.environ.get("REPO_URL", "")
    branch = os.environ.get("DEFAULT_BRANCH", "main")

    if not repo_url:
        return

    if (MAIN_CHECKOUT / ".git").exists():
        return

    MAIN_CHECKOUT.mkdir(parents=True, exist_ok=True)
    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--single-branch", "--branch", branch,
        "--filter=blob:none", repo_url, str(MAIN_CHECKOUT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Clone failed: {stderr.decode().strip()}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Clone repo on startup."""
    await _clone_repo()
    yield


app = FastAPI(title="Workspace Server", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(files.router, prefix="/files", tags=["files"])
app.include_router(git.router, prefix="/git", tags=["git"])
app.include_router(worktrees.router, prefix="/worktrees", tags=["worktrees"])
app.include_router(terminal.router, prefix="/terminal", tags=["terminal"])
