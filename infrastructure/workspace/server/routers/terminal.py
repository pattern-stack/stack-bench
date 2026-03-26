"""Terminal command execution endpoint for workspace server."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

WORKSPACE_ROOT = Path("/workspace")
MAX_TIMEOUT = 300  # seconds


class TerminalRequest(BaseModel):
    command: str
    cwd: str = "/workspace/main"
    timeout: int = 30


class TerminalResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False


@router.post("")
async def execute_command(body: TerminalRequest) -> TerminalResult:
    """Execute a shell command in the workspace."""
    # Validate cwd is within /workspace/
    cwd = Path(body.cwd).resolve()
    if not str(cwd).startswith(str(WORKSPACE_ROOT)):
        raise HTTPException(status_code=403, detail="Working directory must be within /workspace/")

    if not cwd.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {body.cwd}")

    timeout = min(body.timeout, MAX_TIMEOUT)

    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_shell(
            body.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        return TerminalResult(
            exit_code=proc.returncode or 0,
            stdout=stdout_bytes.decode(errors="replace"),
            stderr=stderr_bytes.decode(errors="replace"),
            duration_ms=duration_ms,
        )

    except asyncio.TimeoutError:
        duration_ms = int((time.monotonic() - start) * 1000)
        proc.kill()
        await proc.wait()
        return TerminalResult(
            exit_code=-1,
            stdout="",
            stderr="Command timed out",
            duration_ms=duration_ms,
            timed_out=True,
        )
