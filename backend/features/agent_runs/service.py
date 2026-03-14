from pattern_stack.atoms.patterns.services import BaseService

from .models import AgentRun
from .schemas.input import AgentRunCreate, AgentRunUpdate


class AgentRunService(BaseService[AgentRun, AgentRunCreate, AgentRunUpdate]):  # type: ignore[misc]
    model = AgentRun
