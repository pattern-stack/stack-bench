from uuid import UUID

from pattern_stack.atoms.patterns import BasePattern, Field


class AgentDefinition(BasePattern):  # type: ignore[misc]
    __tablename__ = "agent_definitions"

    class Pattern:
        entity = "agent_definition"
        reference_prefix = "AGNT"
        track_changes = True

    name = Field(str, required=True, max_length=100, unique=True, index=True)
    role_template_id = Field(UUID, foreign_key="role_templates.id", required=True, index=True)
    model_override = Field(str, nullable=True, max_length=100)
    mission = Field(str, required=True)
    background = Field(str, nullable=True)
    awareness = Field(dict, default=dict)
    is_active = Field(bool, default=True, index=True)
