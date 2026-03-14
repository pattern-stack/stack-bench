from pattern_stack.atoms.patterns import BasePattern, Field


class RoleTemplate(BasePattern):  # type: ignore[misc]
    __tablename__ = "role_templates"

    class Pattern:
        entity = "role_template"
        reference_prefix = "ROLE"
        track_changes = True

    name = Field(str, required=True, max_length=100, unique=True, index=True)
    source = Field(str, default="custom", max_length=20)
    archetype = Field(str, nullable=True, max_length=100)
    default_model = Field(str, nullable=True, max_length=100)
    persona = Field(dict, default=dict)
    judgments = Field(list, default=list)
    responsibilities = Field(list, default=list)
    description = Field(str, nullable=True)
    is_active = Field(bool, default=True, index=True)
