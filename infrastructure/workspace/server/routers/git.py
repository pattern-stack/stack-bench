"""Git operation endpoints for workspace server."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

MAIN_CHECKOUT = Path("/workspace/main")


class GitStatus(BaseModel):
    branch: str
    clean: bool
    staged: list[str]
    modified: list[str]
    untracked: list[str]
    ahead: int
    behind: int


class CheckoutRequest(BaseModel):
    ref: str


class CommitRequest(BaseModel):
    message: str
    paths: list[str] | None = None


class DiffRequest(BaseModel):
    base: str = "main"
    head: str = "HEAD"


class LogRequest(BaseModel):
    max_count: int = 20


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


@router.get("/status")
async def git_status() -> GitStatus:
    """Return working tree status."""
    branch_out, _, _ = await _run_git("branch", "--show-current")

    # Staged files
    staged_out, _, _ = await _run_git("diff", "--cached", "--name-only")
    staged = [f for f in staged_out.split("\n") if f.strip()]

    # Modified files
    modified_out, _, _ = await _run_git("diff", "--name-only")
    modified = [f for f in modified_out.split("\n") if f.strip()]

    # Untracked files
    untracked_out, _, _ = await _run_git("ls-files", "--others", "--exclude-standard")
    untracked = [f for f in untracked_out.split("\n") if f.strip()]

    # Ahead/behind
    ahead = 0
    behind = 0
    ab_out, _, code = await _run_git("rev-list", "--left-right", "--count", f"HEAD...@{{u}}")
    if code == 0 and ab_out:
        parts = ab_out.split("\t")
        if len(parts) == 2:
            ahead = int(parts[0])
            behind = int(parts[1])

    clean = not staged and not modified and not untracked

    return GitStatus(
        branch=branch_out,
        clean=clean,
        staged=staged,
        modified=modified,
        untracked=untracked,
        ahead=ahead,
        behind=behind,
    )


@router.post("/checkout")
async def git_checkout(body: CheckoutRequest) -> dict:
    """Checkout a branch or commit."""
    stdout, stderr, code = await _run_git("checkout", body.ref)
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr)
    return {"ref": body.ref, "output": stdout or stderr}


@router.post("/commit")
async def git_commit(body: CommitRequest) -> dict:
    """Stage files and create a commit."""
    add_args = ["add"] + (body.paths or ["."])
    await _run_git(*add_args)

    stdout, stderr, code = await _run_git("commit", "-m", body.message)
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr)

    sha_out, _, _ = await _run_git("rev-parse", "HEAD")
    return {"sha": sha_out, "message": body.message}


@router.post("/diff")
async def git_diff(body: DiffRequest) -> dict:
    """Get diff between two refs."""
    stdout, stderr, code = await _run_git("diff", f"{body.base}...{body.head}")
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr)
    return {"diff": stdout, "base": body.base, "head": body.head}


@router.post("/log")
async def git_log(body: LogRequest) -> dict:
    """Get commit log."""
    stdout, stderr, code = await _run_git(
        "log", f"--max-count={body.max_count}",
        "--format=%H|%an|%ae|%s|%aI",
    )
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr)

    commits = []
    for line in stdout.split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 4)
        if len(parts) == 5:
            commits.append({
                "sha": parts[0],
                "author_name": parts[1],
                "author_email": parts[2],
                "message": parts[3],
                "date": parts[4],
            })
    return {"commits": commits}


@router.post("/fetch")
async def git_fetch() -> dict:
    """Fetch from remote."""
    stdout, stderr, code = await _run_git("fetch", "--all")
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr)
    return {"output": stdout or stderr}


@router.post("/pull")
async def git_pull() -> dict:
    """Pull from remote."""
    stdout, stderr, code = await _run_git("pull")
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr)
    return {"output": stdout or stderr}
