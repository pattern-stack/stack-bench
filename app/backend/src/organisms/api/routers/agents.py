from fastapi import APIRouter

from molecules.apis.conversation_api import AgentDetailResponse
from organisms.api.dependencies import ConversationAPIDep

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=list[str])
async def list_agents(api: ConversationAPIDep) -> list[str]:
    return await api.list_agents()


@router.get("/{name}", response_model=AgentDetailResponse)
async def get_agent(name: str, api: ConversationAPIDep) -> AgentDetailResponse:
    return await api.get_agent(name)
