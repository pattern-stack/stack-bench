"""Worktree management endpoints for workspace server."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

MAIN_CHECKOUT = Path("/workspace/main")
WORKTREES_DIR = Path("/workspace/worktrees")


class WorktreeCreate(BaseModel):
    name: str
    ref: str = "main"


class WorktreeInfo(BaseModel):
    name: str
    path: str
    branch: str
    head_sha: str
    is_main: bool


async def _run_git(*args: str, cwd: Path = MAIN_CHECKOUT) -> tuple[str, str, int]:
    """Run a git command and return stdout, stderr, return code."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd),
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode().strip(), stderr.decode().strip(), proc.returncode or 0


@router.get("")
async def list_worktrees() -> list[WorktreeInfo]:
    """List all worktrees."""
    stdout, _, code = await _run_git("worktree", "list", "--porcelain")
    if code != 0:
        return []

    worktrees = []
    current: dict[str, str] = {}

    for line in stdout.split("\n"):
        if not line.strip():
            if current:
                wt_path = current.get("worktree", "")
                branch = current.get("branch", "").replace("refs/heads/", "")
                head_sha = current.get("HEAD", "")
                is_main = wt_path == str(MAIN_CHECKOUT)
                name = Path(wt_path).name if wt_path else ""
                worktrees.append(WorktreeInfo(
                    name=name,
                    path=wt_path,
                    branch=branch,
                    head_sha=head_sha,
                    is_main=is_main,
                ))
                current = {}
            continue

        if line.startswith("worktree "):
            current["worktree"] = line.split(" ", 1)[1]
        elif line.startswith("HEAD "):
            current["HEAD"] = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1]

    # Handle last entry
    if current:
        wt_path = current.get("worktree", "")
        branch = current.get("branch", "").replace("refs/heads/", "")
        head_sha = current.get("HEAD", "")
        is_main = wt_path == str(MAIN_CHECKOUT)
        name = Path(wt_path).name if wt_path else ""
        worktrees.append(WorktreeInfo(
            name=name,
            path=wt_path,
            branch=branch,
            head_sha=head_sha,
            is_main=is_main,
        ))

    return worktrees


@router.post("")
async def create_worktree(body: WorktreeCreate) -> WorktreeInfo:
    """Create a new worktree."""
    worktree_path = WORKTREES_DIR / body.name
    if worktree_path.exists():
        raise HTTPException(status_code=409, detail=f"Worktree '{body.name}' already exists")

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)

    stdout, stderr, code = await _run_git(
        "worktree", "add", str(worktree_path), body.ref,
    )
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr)

    # Get HEAD sha of the new worktree
    sha_out, _, _ = await _run_git("rev-parse", "HEAD", cwd=worktree_path)

    # Get branch name
    branch_out, _, _ = await _run_git("branch", "--show-current", cwd=worktree_path)

    return WorktreeInfo(
        name=body.name,
        path=str(worktree_path),
        branch=branch_out or body.ref,
        head_sha=sha_out,
        is_main=False,
    )


@router.delete("/{name}")
async def delete_worktree(name: str) -> dict:
    """Remove a worktree."""
    worktree_path = WORKTREES_DIR / name
    if not worktree_path.exists():
        raise HTTPException(status_code=404, detail=f"Worktree '{name}' not found")

    stdout, stderr, code = await _run_git(
        "worktree", "remove", str(worktree_path), "--force",
    )
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr)

    return {"deleted": name}
