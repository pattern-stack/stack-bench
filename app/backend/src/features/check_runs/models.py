from uuid import UUID

from pattern_stack.atoms.patterns import BasePattern, Field


class CheckRun(BasePattern):
    __tablename__ = "check_runs"

    class Pattern:
        entity = "check_run"
        reference_prefix = "CHK"
        track_changes = True

    pull_request_id = Field(UUID, foreign_key="pull_requests.id", required=True, index=True)
    external_id = Field(int, required=True, unique=True, index=True)
    head_sha = Field(str, required=True, max_length=40, index=True)
    name = Field(str, required=True, max_length=200)
    status = Field(str, required=True, max_length=20, choices=["queued", "in_progress", "completed"])
    conclusion = Field(str, nullable=True, max_length=20, choices=["success", "failure", "cancelled"])
