from fastapi import Request
from fastapi.responses import JSONResponse

from molecules.exceptions import (
    AgentNotFoundError,
    BranchNotFoundError,
    ConversationNotFoundError,
    MoleculeError,
    StackNotFoundError,
)
from molecules.providers.github_adapter import (
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)

EXCEPTION_MAP: dict[type[MoleculeError], tuple[int, str]] = {
    ConversationNotFoundError: (404, "Conversation not found"),
    AgentNotFoundError: (404, "Agent not found"),
    BranchNotFoundError: (404, "Branch not found"),
    StackNotFoundError: (404, "Stack not found"),
}


async def molecule_exception_handler(request: Request, exc: MoleculeError) -> JSONResponse:
    for exc_type, (status_code, _detail) in EXCEPTION_MAP.items():
        if isinstance(exc, exc_type):
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


async def github_exception_handler(request: Request, exc: GitHubAPIError) -> JSONResponse:
    if isinstance(exc, GitHubNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    if isinstance(exc, GitHubRateLimitError):
        return JSONResponse(status_code=429, content={"detail": str(exc)})
    return JSONResponse(status_code=502, content={"detail": str(exc)})
