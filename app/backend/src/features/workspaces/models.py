from uuid import UUID

from pattern_stack.atoms.patterns import BasePattern, Field


class Workspace(BasePattern):
    __tablename__ = "workspaces"

    class Pattern:
        entity = "workspace"
        reference_prefix = "WKSP"
        track_changes = True

    project_id = Field(UUID, foreign_key="projects.id", required=True, index=True)
    name = Field(str, required=True, max_length=200)
    repo_url = Field(str, required=True, max_length=500)
    provider = Field(str, required=True, max_length=20, choices=["github", "gitlab", "bitbucket"])
    default_branch = Field(str, required=True, max_length=200, default="main")
    local_path = Field(str, nullable=True, max_length=500)
    metadata_ = Field(dict, default=dict)
    is_active = Field(bool, default=True, index=True)
