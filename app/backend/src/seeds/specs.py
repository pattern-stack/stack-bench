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


@dataclass
class ProjectSeed(SeedSpec):
    entity_type: ClassVar[str] = "Project"

    name: str = ""
    description: str | None = None

    async def create(self, ctx: SeedContext) -> UUID:
        from features.projects.schemas.input import ProjectCreate
        from features.projects.service import ProjectService

        service = ProjectService()
        project = await service.create(
            ctx.db,
            ProjectCreate(name=self.name, description=self.description, local_path="/tmp/seeds", github_repo="https://github.com/example/seed-project"),
        )
        return project.id


@dataclass
class WorkspaceSeed(SeedSpec):
    entity_type: ClassVar[str] = "Workspace"

    project: str = ""
    name: str = ""
    repo_url: str = ""
    provider: str = "github"
    default_branch: str = "main"
    local_path: str | None = None

    async def create(self, ctx: SeedContext) -> UUID:
        from features.workspaces.schemas.input import WorkspaceCreate
        from features.workspaces.service import WorkspaceService

        project_id = self.resolve_ref_required(ctx, self.project)
        service = WorkspaceService()
        workspace = await service.create(
            ctx.db,
            WorkspaceCreate(
                project_id=project_id,
                name=self.name,
                repo_url=self.repo_url,
                provider=self.provider,
                default_branch=self.default_branch,
                local_path=self.local_path,
            ),
        )
        return workspace.id


@dataclass
class StackSeed(SeedSpec):
    entity_type: ClassVar[str] = "Stack"

    project: str = ""
    name: str = ""
    trunk: str = "main"

    async def create(self, ctx: SeedContext) -> UUID:
        from features.stacks.schemas.input import StackCreate
        from features.stacks.service import StackService

        project_id = self.resolve_ref_required(ctx, self.project)
        service = StackService()
        stack = await service.create(
            ctx.db,
            StackCreate(project_id=project_id, name=self.name, trunk=self.trunk),
        )
        return stack.id


@dataclass
class BranchSeed(SeedSpec):
    entity_type: ClassVar[str] = "Branch"

    stack: str = ""
    workspace: str = ""
    name: str = ""
    position: int = 1
    head_sha: str | None = None

    async def create(self, ctx: SeedContext) -> UUID:
        from features.branches.schemas.input import BranchCreate
        from features.branches.service import BranchService

        stack_id = self.resolve_ref_required(ctx, self.stack)
        workspace_id = self.resolve_ref_required(ctx, self.workspace)
        service = BranchService()
        branch = await service.create(
            ctx.db,
            BranchCreate(
                stack_id=stack_id,
                workspace_id=workspace_id,
                name=self.name,
                position=self.position,
                head_sha=self.head_sha,
            ),
        )
        return branch.id


@dataclass
class PullRequestSeed(SeedSpec):
    entity_type: ClassVar[str] = "PullRequest"

    branch: str = ""
    title: str = ""
    description: str | None = None
    external_id: int | None = None
    external_url: str | None = None

    async def create(self, ctx: SeedContext) -> UUID:
        from features.pull_requests.schemas.input import PullRequestCreate
        from features.pull_requests.service import PullRequestService

        branch_id = self.resolve_ref_required(ctx, self.branch)
        service = PullRequestService()
        pr = await service.create(
            ctx.db,
            PullRequestCreate(
                branch_id=branch_id,
                title=self.title,
                description=self.description,
                external_id=self.external_id,
                external_url=self.external_url,
            ),
        )
        return pr.id
