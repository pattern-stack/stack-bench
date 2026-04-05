from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from features.conversations.schemas.output import ConversationResponse
from molecules.apis.conversation_api import ConversationDetailResponse
from organisms.api.dependencies import ConversationAPIDep

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
    entity_id: UUID = Query(...),
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
    api: ConversationAPIDep,
) -> dict[str, str]:
    """Send message — placeholder until Claude integration in SB-007."""
    await api.get(conversation_id)
    return {
        "status": "received",
        "conversation_id": str(conversation_id),
        "message": data.message,
    }


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
