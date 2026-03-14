from uuid import UUID

from fastapi import APIRouter
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


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    data: CreateConversationRequest,
    api: ConversationAPIDep,
) -> ConversationResponse:
    return await api.create(data.agent_name, data.model)


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    api: ConversationAPIDep,
) -> list[ConversationResponse]:
    return await api.list()


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


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    api: ConversationAPIDep,
) -> None:
    await api.delete(conversation_id)
