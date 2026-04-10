from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class Workspace(EventPattern):
    __tablename__ = "workspaces"

    class Pattern:
        entity = "workspace"
        reference_prefix = "WKSP"
        initial_state = "created"
        states = {
            "created": ["provisioning"],
            "provisioning": ["ready", "created"],  # can fail back to created
            "ready": ["stopped", "destroying"],
            "stopped": ["provisioning", "destroying"],  # can re-provision
            "destroying": ["destroyed"],
            "destroyed": [],
        }
        state_phases = {
            "created": StatePhase.INITIAL,
            "provisioning": StatePhase.ACTIVE,
            "ready": StatePhase.ACTIVE,
            "stopped": StatePhase.ACTIVE,
            "destroying": StatePhase.ACTIVE,
            "destroyed": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    # Existing fields
    project_id = Field(UUID, foreign_key="projects.id", required=True, index=True)
    name = Field(str, required=True, max_length=200)
    repo_url = Field(str, required=True, max_length=500)
    provider = Field(str, required=True, max_length=20, choices=["github", "gitlab", "bitbucket", "local"])
    default_branch = Field(str, required=True, max_length=200, default="main")
    local_path = Field(str, nullable=True, max_length=500)
    metadata_ = Field(dict, default=dict)
    is_active = Field(bool, default=True, index=True)

    # New cloud provisioning fields
    resource_profile = Field(str, max_length=20, default="standard")
    region = Field(str, max_length=50, default="northamerica-northeast2")
    cloud_run_service = Field(str, nullable=True, max_length=200)
    cloud_run_url = Field(str, nullable=True, max_length=500)
    gcs_bucket = Field(str, nullable=True, max_length=200)
    config = Field(dict, default=dict)
