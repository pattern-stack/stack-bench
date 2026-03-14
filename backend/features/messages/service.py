from pattern_stack.atoms.patterns.services import BaseService

from .models import Message
from .schemas.input import MessageCreate, MessageUpdate


class MessageService(BaseService[Message, MessageCreate, MessageUpdate]):  # type: ignore[misc]
    model = Message
