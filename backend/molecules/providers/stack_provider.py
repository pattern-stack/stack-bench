from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class StackResult:
    """Result of a stack CLI operation."""

    success: bool
    output: str
    error: str | None = None


@dataclass
class BranchInfo:
    """Information about a branch from the CLI."""

    name: str
    position: int
    head_sha: str | None = None
    pr_number: int | None = None
    pr_url: str | None = None


@dataclass
class StackInfo:
    """Information about a stack from the CLI."""

    name: str
    trunk: str
    branches: list[BranchInfo]


class StackProvider(Protocol):
    """Contract for git stacking operations.

    Implementations wrap a stacking tool (CLI binary or native git+GitHub API)
    to perform git operations and report results back to the domain layer.
    """

    async def create_stack(
        self, name: str, *, trunk: str = "main"
    ) -> StackResult:
        """Create a new stack in the git tool."""
        ...

    async def get_status(self, stack_name: str) -> StackInfo:
        """Get current status of a stack from the git tool."""
        ...

    async def push(
        self, stack_name: str, *, branch_positions: list[int] | None = None
    ) -> StackResult:
        """Push branches to remote. If branch_positions is None, push all."""
        ...

    async def submit(self, stack_name: str) -> StackResult:
        """Submit stack -- create/update GitHub PRs."""
        ...

    async def restack(self, stack_name: str) -> StackResult:
        """Rebase downstream branches after mid-stack edits."""
        ...

    async def sync(self, stack_name: str) -> StackResult:
        """Sync stack -- clean up after PRs merge."""
        ...
