from pattern_stack.atoms.patterns.services import BaseService

from .models import ToolCall
from .schemas.input import ToolCallCreate, ToolCallUpdate


class ToolCallService(BaseService[ToolCall, ToolCallCreate, ToolCallUpdate]):  # type: ignore[misc]
    model = ToolCall
