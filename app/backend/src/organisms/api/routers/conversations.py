from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TCH003

from fastapi import APIRouter, Query
from pattern_stack.atoms.broadcast import get_broadcast
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from features.conversations.schemas.output import ConversationResponse
from molecules.apis.conversation_api import ConversationDetailResponse
from organisms.api.dependencies import ConversationAPIDep, ConversationRunnerDep  # noqa: TCH001

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=100)
    model: str | None = None


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)


class BranchConversationRequest(BaseModel):
    at_sequence: int = Field(..., ge=1)


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    data: CreateConversationRequest,
    api: ConversationAPIDep,
) -> ConversationResponse:
    return await api.create(data.agent_name, data.model)


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    api: ConversationAPIDep,
    agent_name: str | None = Query(None),
    state: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[ConversationResponse]:
    return await api.list(
        agent_name=agent_name,
        state=state,
        limit=limit,
        offset=offset,
    )


@router.get("/by-entity", response_model=ConversationResponse | None)
async def get_conversation_by_entity(
    api: ConversationAPIDep,
    entity_type: str = Query(..., min_length=1),
    entity_id: UUID = Query(...),  # noqa: B008
    role: str = Query(..., min_length=1),
) -> ConversationResponse | None:
    """Get the active conversation linked to an entity with a specific role."""
    return await api.get_by_entity(
        entity_type=entity_type,
        entity_id=entity_id,
        role=role,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    api: ConversationAPIDep,
) -> ConversationDetailResponse:
    return await api.get(conversation_id)


@router.post("/{conversation_id}/send")
async def send_message(
    conversation_id: UUID,
    data: SendMessageRequest,
    runner: ConversationRunnerDep,
) -> StreamingResponse:
    """Send a message and stream SSE events from the agent runner."""

    async def generate() -> AsyncGenerator[str, None]:
        broadcast = get_broadcast()
        async for sse_chunk in runner.send(conversation_id, data.message):
            yield sse_chunk
            await _broadcast_sse_chunk(broadcast, conversation_id, sse_chunk)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _broadcast_sse_chunk(
    broadcast: object,
    conversation_id: UUID,
    sse_chunk: str,
) -> None:
    """Parse an SSE-formatted string and broadcast to the conversation channel."""
    event_type = "message"
    data_str = ""
    for line in sse_chunk.strip().split("\n"):
        if line.startswith("event: "):
            event_type = line[7:]
        elif line.startswith("data: "):
            data_str = line[6:]

    try:
        data = json.loads(data_str) if data_str else {}
    except json.JSONDecodeError:
        data = {"raw": data_str}

    await broadcast.broadcast(  # type: ignore[attr-defined]
        f"conversation:{conversation_id}",
        event_type,
        data,
    )


@router.post(
    "/{conversation_id}/branch",
    response_model=ConversationResponse,
    status_code=201,
)
async def branch_conversation(
    conversation_id: UUID,
    data: BranchConversationRequest,
    api: ConversationAPIDep,
) -> ConversationResponse:
    """Branch a conversation at a given message sequence.

    Creates a new conversation linked to the original, copying all
    messages up to and including at_sequence.
    """
    return await api.branch(conversation_id, data.at_sequence)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    api: ConversationAPIDep,
) -> None:
    await api.delete(conversation_id)
