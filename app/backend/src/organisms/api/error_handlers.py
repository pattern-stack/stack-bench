from fastapi import Request
from fastapi.responses import JSONResponse
from pattern_stack.atoms.patterns import InvalidStateTransitionError
from pattern_stack.features.auth.exceptions import AuthError

from molecules.exceptions import (
    AgentNotFoundError,
    BranchNotFoundError,
    ConversationNotFoundError,
    MoleculeError,
    StackNotFoundError,
    WorkspaceNotFoundError,
    WorkspaceProvisionError,
)
from molecules.providers.github_adapter import (
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from molecules.providers.local_git_adapter import (
    LocalGitError,
    LocalGitRefNotFoundError,
)

EXCEPTION_MAP: dict[type[MoleculeError], tuple[int, str]] = {
    ConversationNotFoundError: (404, "Conversation not found"),
    AgentNotFoundError: (404, "Agent not found"),
    BranchNotFoundError: (404, "Branch not found"),
    StackNotFoundError: (404, "Stack not found"),
    WorkspaceNotFoundError: (404, "Workspace not found"),
    WorkspaceProvisionError: (409, "Workspace provisioning failed"),
}


async def molecule_exception_handler(request: Request, exc: MoleculeError) -> JSONResponse:
    for exc_type, (status_code, _detail) in EXCEPTION_MAP.items():
        if isinstance(exc, exc_type):
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


async def auth_exception_handler(request: Request, exc: AuthError) -> JSONResponse:
    """Handle pattern-stack auth exceptions."""
    return JSONResponse(status_code=401, content={"detail": str(exc)})


async def state_transition_handler(request: Request, exc: InvalidStateTransitionError) -> JSONResponse:
    """Handle invalid state transitions as 409 Conflict."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def local_git_exception_handler(request: Request, exc: LocalGitError) -> JSONResponse:
    if isinstance(exc, LocalGitRefNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    return JSONResponse(status_code=500, content={"detail": f"Local git error: {exc}"})


async def github_exception_handler(request: Request, exc: GitHubAPIError) -> JSONResponse:
    if isinstance(exc, GitHubNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    if isinstance(exc, GitHubRateLimitError):
        return JSONResponse(status_code=429, content={"detail": str(exc)})
    return JSONResponse(status_code=502, content={"detail": str(exc)})
