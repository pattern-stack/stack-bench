"""Seed specifications for pts db seed."""

from pattern_stack.atoms.seeding.loaders.yaml_loader import register_spec

from seeds.specs import (
    AgentDefinitionSeed,
    BranchSeed,
    ProjectSeed,
    PullRequestSeed,
    RoleTemplateSeed,
    StackSeed,
    WorkspaceSeed,
)

register_spec("role_templates", RoleTemplateSeed)
register_spec("agent_definitions", AgentDefinitionSeed)
register_spec("projects", ProjectSeed)
register_spec("workspaces", WorkspaceSeed)
register_spec("stacks", StackSeed)
register_spec("branches", BranchSeed)
register_spec("pull_requests", PullRequestSeed)
