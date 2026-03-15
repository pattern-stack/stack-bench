"""SeedSpec subclasses for pts db seed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from pattern_stack.atoms.seeding.spec import SeedSpec

if TYPE_CHECKING:
    from uuid import UUID

    from pattern_stack.atoms.seeding.context import SeedContext


@dataclass
class RoleTemplateSeed(SeedSpec):
    entity_type: ClassVar[str] = "RoleTemplate"

    name: str = ""
    source: str = "library"
    archetype: str | None = None
    default_model: str | None = None
    persona: dict[str, Any] = field(default_factory=dict)
    judgments: list[Any] = field(default_factory=list)
    responsibilities: list[Any] = field(default_factory=list)
    description: str | None = None

    async def create(self, ctx: SeedContext) -> UUID:
        from features.role_templates.schemas.input import RoleTemplateCreate
        from features.role_templates.service import RoleTemplateService

        service = RoleTemplateService()
        role = await service.create(
            ctx.db,
            RoleTemplateCreate(
                name=self.name,
                source=self.source,
                archetype=self.archetype,
                default_model=self.default_model,
                persona=self.persona,
                judgments=self.judgments,
                responsibilities=self.responsibilities,
                description=self.description,
            ),
        )
        return role.id


@dataclass
class AgentDefinitionSeed(SeedSpec):
    entity_type: ClassVar[str] = "AgentDefinition"

    name: str = ""
    role_template: str = ""
    model_override: str | None = None
    mission: str = ""
    background: str | None = None
    awareness: dict[str, Any] = field(default_factory=dict)

    async def create(self, ctx: SeedContext) -> UUID:
        from features.agent_definitions.schemas.input import AgentDefinitionCreate
        from features.agent_definitions.service import AgentDefinitionService

        role_template_id = self.resolve_ref_required(ctx, self.role_template)

        service = AgentDefinitionService()
        agent = await service.create(
            ctx.db,
            AgentDefinitionCreate(
                name=self.name,
                role_template_id=role_template_id,
                model_override=self.model_override,
                mission=self.mission,
                background=self.background,
                awareness=self.awareness,
            ),
        )
        return agent.id
