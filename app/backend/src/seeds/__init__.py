"""Seed specifications for pts db seed."""

from pattern_stack.atoms.seeding.loaders.yaml_loader import register_spec

from seeds.specs import AgentDefinitionSeed, RoleTemplateSeed

register_spec("role_templates", RoleTemplateSeed)
register_spec("agent_definitions", AgentDefinitionSeed)
