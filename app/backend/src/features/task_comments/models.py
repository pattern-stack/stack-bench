from datetime import datetime
from uuid import UUID

from pattern_stack.atoms.patterns import BasePattern, Field


class TaskComment(BasePattern):
    __tablename__ = "task_comments"

    class Pattern:
        entity = "task_comment"
        reference_prefix = "TCM"

    # Domain fields
    body = Field(str, required=True)
    edited_at = Field(datetime, nullable=True)

    # Foreign keys
    task_id = Field(UUID, foreign_key="tasks.id", required=True, index=True)
    author_id = Field(UUID, nullable=True, index=True)
    parent_id = Field(UUID, foreign_key="task_comments.id", nullable=True, index=True)

    # External sync
    external_id = Field(str, nullable=True, max_length=200, index=True)
    external_url = Field(str, nullable=True, max_length=500)
    provider = Field(str, default="local", choices=["github", "linear", "local"])
    last_synced_at = Field(datetime, nullable=True)
