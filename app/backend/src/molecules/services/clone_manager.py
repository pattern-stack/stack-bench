"""Ephemeral clone manager for server-side git operations.

Creates temporary git checkouts from GitHub for agent operations such as
remote rebase, code review, auto-fix, and test runs -- without depending
on the developer's local repo.
"""

from __future__ import annotations

import asyncio
import shutil
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class CloneError(Exception):
    """Raised when a clone operation fails."""


@dataclass
class CloneOptions:
    """Options for creating an ephemeral clone."""

    ref: str = "main"
    depth: int | None = None
    sparse_paths: list[str] | None = None
    filter_blobs: bool = True


@dataclass
class CloneContext:
    """Metadata about an active ephemeral clone."""

    path: Path
    repo_url: str
    ref: str
    created_at: datetime
    clone_id: str


@dataclass
class GitResult:
    """Result of a git command execution."""

    success: bool
    output: str
    error: str | None = None


@dataclass
class RebaseResult:
    """Result of a git rebase operation."""

    success: bool
    output: str
    has_conflicts: bool = False
    conflicting_files: list[str] = field(default_factory=list)
    error: str | None = None


class CloneManager:
    """Manages temporary git clones for server-side operations.

    Usage::

        manager = CloneManager(base_dir=Path("/tmp/clones"))
        async with manager.clone("https://github.com/org/repo.git") as ctx:
            git = GitOperations(ctx.path)
            await git.checkout("feature-branch")
            result = await git.rebase("main")
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        max_clones: int = 5,
        ttl_seconds: int = 3600,
        github_token: str | None = None,
    ) -> None:
        self.base_dir = base_dir or Path("/tmp/stack-bench-clones")
        self.max_clones = max_clones
        self.ttl_seconds = ttl_seconds
        self.github_token = github_token
        self._active: dict[str, CloneContext] = {}

    @property
    def active_clones(self) -> dict[str, CloneContext]:
        """Read-only view of active clones."""
        return dict(self._active)

    @asynccontextmanager
    async def clone(
        self,
        repo_url: str,
        options: CloneOptions | None = None,
    ) -> AsyncGenerator[CloneContext, None]:
        """Clone a repo into a temp directory, yield context, clean up on exit.

        Raises:
            CloneError: If max concurrent clones is reached or clone fails.
        """
        if len(self._active) >= self.max_clones:
            msg = f"Maximum concurrent clones ({self.max_clones}) reached"
            raise CloneError(msg)

        opts = options or CloneOptions()
        clone_id = uuid.uuid4().hex[:12]
        clone_dir = self.base_dir / clone_id
        clone_dir.mkdir(parents=True, exist_ok=True)

        ctx = CloneContext(
            path=clone_dir,
            repo_url=repo_url,
            ref=opts.ref,
            created_at=datetime.now(tz=UTC),
            clone_id=clone_id,
        )

        try:
            await self._git_clone(repo_url, clone_dir, opts)
            self._active[clone_id] = ctx
            yield ctx
        finally:
            self._active.pop(clone_id, None)
            await self._cleanup(ctx)

    async def _git_clone(self, repo_url: str, target: Path, options: CloneOptions) -> None:
        """Run git clone as an async subprocess."""
        clone_url = self._inject_token(repo_url)

        cmd: list[str] = ["git", "clone", "--single-branch", "--branch", options.ref]

        if options.filter_blobs:
            cmd.append("--filter=blob:none")

        if options.depth is not None:
            cmd.extend(["--depth", str(options.depth)])

        cmd.extend([clone_url, str(target)])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_bytes = await proc.communicate()

        if proc.returncode != 0:
            stderr_text = stderr_bytes.decode().strip()
            msg = f"Clone failed (exit {proc.returncode}): {stderr_text}"
            raise CloneError(msg)

    def _inject_token(self, repo_url: str) -> str:
        """Inject GitHub token into HTTPS URL for authentication.

        Transforms: https://github.com/org/repo.git
        Into:       https://x-access-token:TOKEN@github.com/org/repo.git
        """
        if not self.github_token:
            return repo_url

        if repo_url.startswith("https://github.com/"):
            return repo_url.replace(
                "https://github.com/",
                f"https://x-access-token:{self.github_token}@github.com/",
            )

        return repo_url

    async def _cleanup(self, ctx: CloneContext) -> None:
        """Remove clone directory from disk."""
        if ctx.path.exists():
            # Use a thread to avoid blocking the event loop on large dirs
            await asyncio.to_thread(shutil.rmtree, ctx.path, ignore_errors=True)

    async def cleanup_stale(self) -> None:
        """Remove clones that have exceeded their TTL.

        Should be called on startup or periodically to catch orphans
        from process crashes.
        """
        now = datetime.now(tz=UTC)
        stale_ids = []

        for clone_id, ctx in self._active.items():
            age_seconds = (now - ctx.created_at).total_seconds()
            if age_seconds > self.ttl_seconds:
                stale_ids.append(clone_id)

        for clone_id in stale_ids:
            ctx = self._active.pop(clone_id)
            await self._cleanup(ctx)


class GitOperations:
    """Git operations within an ephemeral clone.

    Provides high-level async methods for common git operations
    (checkout, rebase, push, commit) scoped to a clone directory.
    """

    def __init__(self, clone_path: Path) -> None:
        self.path = clone_path

    async def _run(self, *args: str) -> tuple[str, str, int]:
        """Run a git command in the clone directory."""
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.path),
        )
        stdout, stderr = await proc.communicate()
        return (
            stdout.decode().strip(),
            stderr.decode().strip(),
            proc.returncode or 0,
        )

    async def checkout(self, branch: str) -> GitResult:
        """Checkout a branch."""
        stdout, stderr, code = await self._run("checkout", branch)
        return GitResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )

    async def rebase(self, onto: str) -> RebaseResult:
        """Rebase current branch onto another.

        If conflicts are detected, the rebase is aborted and conflicting
        files are reported.
        """
        stdout, stderr, code = await self._run("rebase", onto)

        if code == 0:
            return RebaseResult(success=True, output=stdout)

        # Detect conflicts
        if "CONFLICT" in stderr or "conflict" in stderr.lower():
            # Get list of conflicting files
            diff_stdout, _, _ = await self._run("diff", "--name-only", "--diff-filter=U")
            conflicting = [f for f in diff_stdout.split("\n") if f.strip()]

            # Abort the rebase to leave the repo in a clean state
            await self._run("rebase", "--abort")

            return RebaseResult(
                success=False,
                output=stdout,
                has_conflicts=True,
                conflicting_files=conflicting,
                error=stderr,
            )

        return RebaseResult(
            success=False,
            output=stdout,
            error=stderr,
        )

    async def push(self, branch: str, *, force_with_lease: bool = True) -> GitResult:
        """Push a branch to the remote."""
        args = ["push", "origin", branch]
        if force_with_lease:
            args.append("--force-with-lease")

        stdout, stderr, code = await self._run(*args)
        return GitResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )

    async def commit(self, message: str, paths: list[str] | None = None) -> str:
        """Stage files and create a commit. Returns the commit SHA."""
        # Stage files
        add_args = ["add"] + (paths or ["."])
        await self._run(*add_args)

        # Commit
        stdout, stderr, code = await self._run("commit", "-m", message, "--format=%H")

        if code != 0:
            msg = f"Commit failed: {stderr}"
            raise CloneError(msg)

        # Get the SHA of the new commit
        sha_stdout, _, _ = await self._run("rev-parse", "HEAD")
        return sha_stdout or stdout

    async def get_head_sha(self) -> str:
        """Return the SHA of HEAD."""
        stdout, _, _ = await self._run("rev-parse", "HEAD")
        return stdout
