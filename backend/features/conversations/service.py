from pattern_stack.atoms.patterns.services import BaseService

from .models import Conversation
from .schemas.input import ConversationCreate, ConversationUpdate


class ConversationService(BaseService[Conversation, ConversationCreate, ConversationUpdate]):  # type: ignore[misc]
    model = Conversation
