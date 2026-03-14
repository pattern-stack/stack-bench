from pattern_stack.atoms.patterns.services import BaseService

from .models import MessagePart
from .schemas.input import MessagePartCreate, MessagePartUpdate


class MessagePartService(BaseService[MessagePart, MessagePartCreate, MessagePartUpdate]):  # type: ignore[misc]
    model = MessagePart
