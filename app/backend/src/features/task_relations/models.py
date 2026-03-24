from datetime import datetime
from uuid import UUID

from pattern_stack.atoms.patterns import BasePattern, Field
from sqlalchemy import UniqueConstraint


class TaskRelation(BasePattern):
    __tablename__ = "task_relations"

    __table_args__ = (UniqueConstraint("source_task_id", "target_task_id", "relation_type", name="uq_task_relation"),)

    class Pattern:
        entity = "task_relation"
        reference_prefix = "TRL"

    # Domain fields
    source_task_id = Field(UUID, foreign_key="tasks.id", required=True, index=True)
    target_task_id = Field(UUID, foreign_key="tasks.id", required=True, index=True)
    relation_type = Field(
        str, required=True, max_length=20, choices=["parent_of", "blocks", "relates_to", "duplicates"]
    )

    # External sync
    external_id = Field(str, nullable=True, max_length=200, index=True)
    external_url = Field(str, nullable=True, max_length=500)
    provider = Field(str, default="local", choices=["github", "linear", "local"])
    last_synced_at = Field(datetime, nullable=True)
