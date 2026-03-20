from uuid import UUID

from pattern_stack.atoms.patterns import BasePattern, Field
from sqlalchemy import UniqueConstraint


class MessagePart(BasePattern):
    __tablename__ = "message_parts"

    __table_args__ = (UniqueConstraint("message_id", "position", name="uq_message_part_position"),)

    class Pattern:
        entity = "message_part"
        reference_prefix = "MPART"

    message_id = Field(UUID, foreign_key="messages.id", required=True, index=True)
    position = Field(int, required=True)
    part_type = Field(str, required=True, max_length=50)
    content = Field(str, nullable=True)
    tool_call_id = Field(str, nullable=True, max_length=200)
    tool_name = Field(str, nullable=True, max_length=200)
    tool_arguments = Field(dict, nullable=True)
