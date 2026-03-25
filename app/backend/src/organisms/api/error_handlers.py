from fastapi import Request
from fastapi.responses import JSONResponse

from molecules.exceptions import (
    AgentNotFoundError,
    ConversationNotFoundError,
    MoleculeError,
    RelationCycleError,
    SprintNotFoundError,
    SyncNotConfiguredError,
    TaskHasBlockersError,
    TaskNotFoundError,
    TaskProjectNotFoundError,
)

EXCEPTION_MAP: dict[type[MoleculeError], tuple[int, str]] = {
    ConversationNotFoundError: (404, "Conversation not found"),
    AgentNotFoundError: (404, "Agent not found"),
    TaskNotFoundError: (404, "Task not found"),
    TaskProjectNotFoundError: (404, "Project not found"),
    SprintNotFoundError: (404, "Sprint not found"),
    TaskHasBlockersError: (409, "Task has open blockers"),
    RelationCycleError: (409, "Relation would create a cycle"),
    SyncNotConfiguredError: (400, "Sync not configured"),
}


async def molecule_exception_handler(request: Request, exc: MoleculeError) -> JSONResponse:
    for exc_type, (status_code, _detail) in EXCEPTION_MAP.items():
        if isinstance(exc, exc_type):
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
