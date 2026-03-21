from uuid import UUID

from pattern_stack.atoms.patterns import BasePattern, Field
from sqlalchemy import UniqueConstraint


class Message(BasePattern):
    __tablename__ = "messages"

    __table_args__ = (UniqueConstraint("conversation_id", "sequence", name="uq_message_sequence"),)

    class Pattern:
        entity = "message"
        reference_prefix = "MSG"

    conversation_id = Field(UUID, foreign_key="conversations.id", required=True, index=True)
    kind = Field(str, required=True, max_length=20)
    sequence = Field(int, required=True)
    run_id = Field(str, nullable=True, max_length=100)
    input_tokens = Field(int, nullable=True, min=0)
    output_tokens = Field(int, nullable=True, min=0)
