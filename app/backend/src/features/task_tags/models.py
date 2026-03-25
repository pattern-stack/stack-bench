from datetime import datetime

from pattern_stack.atoms.patterns import BasePattern, Field
from sqlalchemy import Column, ForeignKey, Table

task_tag_assignments = Table(
    "task_tag_assignments",
    BasePattern.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", ForeignKey("task_tags.id"), primary_key=True),
)


class TaskTag(BasePattern):
    __tablename__ = "task_tags"

    class Pattern:
        entity = "task_tag"
        reference_prefix = "TTG"

    # Domain fields
    name = Field(str, required=True, unique=True, max_length=100)
    color = Field(str, nullable=True, max_length=7)
    description = Field(str, nullable=True)
    group = Field(str, nullable=True, max_length=100)
    is_exclusive = Field(bool, default=False)

    # External sync
    external_id = Field(str, nullable=True, max_length=200, index=True)
    external_url = Field(str, nullable=True, max_length=500)
    provider = Field(str, default="local", choices=["github", "linear", "local"])
    last_synced_at = Field(datetime, nullable=True)
