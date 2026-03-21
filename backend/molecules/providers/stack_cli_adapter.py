from __future__ import annotations

import asyncio
import shutil

from molecules.providers.stack_provider import BranchInfo, StackInfo, StackResult


class StackCLIAdapter:
    """Wraps the existing `stack` CLI binary (dugshub/stack).

    Installed globally via Bun at ~/.bun/bin/stack. Executes CLI commands
    as async subprocesses and parses output.

    This is a short-term adapter. The long-term plan (NativeStackAdapter)
    will use direct git + GitHub API calls.
    """

    def __init__(self, binary_path: str | None = None) -> None:
        self.binary_path = binary_path or self._find_binary()

    @staticmethod
    def _find_binary() -> str:
        """Find the stack binary on PATH or at known locations."""
        # Check PATH first
        found = shutil.which("stack")
        if found:
            return found
        # Known Bun global install location
        import os

        bun_path = os.path.expanduser("~/.bun/bin/stack")
        if os.path.isfile(bun_path):
            return bun_path
        raise FileNotFoundError("stack CLI binary not found. Install via: bun install -g @pattern-stack/stack")

    async def _run(self, *args: str) -> tuple[str, str, int]:
        """Run a stack CLI command and return (stdout, stderr, returncode)."""
        proc = await asyncio.create_subprocess_exec(
            self.binary_path,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (
            stdout.decode().strip(),
            stderr.decode().strip(),
            proc.returncode or 0,
        )

    async def create_stack(self, name: str, *, trunk: str = "main") -> StackResult:
        """Create a new stack via CLI."""
        stdout, stderr, code = await self._run("create", name)
        return StackResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )

    async def get_status(self, stack_name: str) -> StackInfo:
        """Get stack status via CLI.

        Parses the output of `stack status` to extract branch info.
        """
        # Switch to the stack first
        await self._run(stack_name)
        stdout, stderr, code = await self._run("status")

        # Parse output -- this is fragile and will be replaced
        # by the NativeStackAdapter. For now, return minimal info.
        branches: list[BranchInfo] = []
        return StackInfo(name=stack_name, trunk="main", branches=branches)

    async def push(self, stack_name: str, *, branch_positions: list[int] | None = None) -> StackResult:
        """Push via CLI. Maps to `stack submit` (which pushes + creates PRs)."""
        args = ["submit"]
        if branch_positions:
            args.extend(str(p) for p in branch_positions)
        stdout, stderr, code = await self._run(*args)
        return StackResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )

    async def submit(self, stack_name: str) -> StackResult:
        """Submit via CLI. Maps to `stack submit`."""
        stdout, stderr, code = await self._run("submit")
        return StackResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )

    async def restack(self, stack_name: str) -> StackResult:
        """Restack via CLI. Maps to `stack restack`."""
        stdout, stderr, code = await self._run("restack")
        return StackResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )

    async def sync(self, stack_name: str) -> StackResult:
        """Sync via CLI. Maps to `stack sync`."""
        stdout, stderr, code = await self._run("sync")
        return StackResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )
