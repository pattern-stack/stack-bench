from uuid import UUID


class MoleculeError(Exception):
    """Base for all molecule errors."""


class ConversationNotFoundError(MoleculeError):
    def __init__(self, conversation_id: UUID) -> None:
        super().__init__(f"Conversation {conversation_id} not found")
        self.conversation_id = conversation_id


class AgentNotFoundError(MoleculeError):
    def __init__(self, name: str, available: list[str] | None = None) -> None:
        available_str = ", ".join(available) if available else "(none)"
        super().__init__(f"Agent '{name}' not found. Available: {available_str}")
        self.name = name
        self.available = available or []
