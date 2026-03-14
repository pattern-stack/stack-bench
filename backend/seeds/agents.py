"""Seed SDLC agent definitions from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

from features.agent_definitions.schemas.input import AgentDefinitionCreate
from features.agent_definitions.service import AgentDefinitionService
from features.role_templates.schemas.input import RoleTemplateCreate
from features.role_templates.service import RoleTemplateService


async def seed_agents(db: AsyncSession) -> dict[str, int]:
    """Load SDLC role templates and agent definitions from YAML.

    Idempotent — skips existing names.

    Returns:
        Counts of created records.
    """
    seed_path = Path(__file__).parent / "agents.yaml"
    with open(seed_path) as f:
        data = yaml.safe_load(f)

    role_service = RoleTemplateService()
    agent_service = AgentDefinitionService()

    roles_created = 0
    agents_created = 0
    role_ids: dict[str, UUID] = {}

    # Create role templates
    for rt_data in data["role_templates"]:
        existing = await role_service.get_by_name(db, rt_data["name"])
        if existing:
            role_ids[rt_data["name"]] = existing.id
            continue

        role = await role_service.create(
            db,
            RoleTemplateCreate(
                name=rt_data["name"],
                source=rt_data.get("source", "library"),
                archetype=rt_data.get("archetype"),
                default_model=rt_data.get("default_model"),
                persona=rt_data.get("persona", {}),
                judgments=rt_data.get("judgments", []),
                responsibilities=rt_data.get("responsibilities", []),
                description=rt_data.get("description"),
            ),
        )
        role_ids[rt_data["name"]] = role.id
        roles_created += 1

    # Create agent definitions
    for ad_data in data["agent_definitions"]:
        existing = await agent_service.get_by_name(db, ad_data["name"])
        if existing:
            continue

        role_template_name = ad_data["role_template"]
        role_template_id = role_ids.get(role_template_name)
        if not role_template_id:
            # Try to find it in DB
            role = await role_service.get_by_name(db, role_template_name)
            if role:
                role_template_id = role.id
            else:
                print(f"Warning: role template '{role_template_name}' not found, skipping agent '{ad_data['name']}'")
                continue

        await agent_service.create(
            db,
            AgentDefinitionCreate(
                name=ad_data["name"],
                role_template_id=role_template_id,
                model_override=ad_data.get("model_override"),
                mission=ad_data["mission"],
                background=ad_data.get("background"),
                awareness=ad_data.get("awareness", {}),
            ),
        )
        agents_created += 1

    await db.commit()
    return {"role_templates": roles_created, "agent_definitions": agents_created}
