"""add task management tables

Revision ID: a3f7c8d91e42
Revises: 1505160361ec
Create Date: 2026-03-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f7c8d91e42"
down_revision: str | None = "1505160361ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. task_projects (EventPattern — no FKs to other new tables)
    op.create_table(
        "task_projects",
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=False, comment="Current state in the state machine"),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when the record was soft deleted",
        ),
        sa.Column("reference_number", sa.String(length=50), nullable=True, comment="Unique reference number"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_projects_name"), "task_projects", ["name"], unique=False)
    op.create_index(op.f("ix_task_projects_lead_id"), "task_projects", ["lead_id"], unique=False)
    op.create_index(op.f("ix_task_projects_external_id"), "task_projects", ["external_id"], unique=False)
    op.create_index(op.f("ix_task_projects_state"), "task_projects", ["state"], unique=False)
    op.create_index(
        op.f("ix_task_projects_reference_number"), "task_projects", ["reference_number"], unique=True
    )

    # 2. sprints (EventPattern — FK to task_projects)
    op.create_table(
        "sprints",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=False, comment="Current state in the state machine"),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when the record was soft deleted",
        ),
        sa.Column("reference_number", sa.String(length=50), nullable=True, comment="Unique reference number"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["task_projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sprints_name"), "sprints", ["name"], unique=False)
    op.create_index(op.f("ix_sprints_number"), "sprints", ["number"], unique=False)
    op.create_index(op.f("ix_sprints_project_id"), "sprints", ["project_id"], unique=False)
    op.create_index(op.f("ix_sprints_external_id"), "sprints", ["external_id"], unique=False)
    op.create_index(op.f("ix_sprints_starts_at"), "sprints", ["starts_at"], unique=False)
    op.create_index(op.f("ix_sprints_state"), "sprints", ["state"], unique=False)
    op.create_index(op.f("ix_sprints_reference_number"), "sprints", ["reference_number"], unique=True)

    # 3. tasks (EventPattern — FKs to task_projects and sprints)
    op.create_table(
        "tasks",
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("issue_type", sa.String(length=20), nullable=True),
        sa.Column("work_phase", sa.String(length=20), nullable=True),
        sa.Column("status_category", sa.String(length=20), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("assignee_id", sa.UUID(), nullable=True),
        sa.Column("sprint_id", sa.UUID(), nullable=True),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=False, comment="Current state in the state machine"),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when the record was soft deleted",
        ),
        sa.Column("reference_number", sa.String(length=50), nullable=True, comment="Unique reference number"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["task_projects.id"]),
        sa.ForeignKeyConstraint(["sprint_id"], ["sprints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_title"), "tasks", ["title"], unique=False)
    op.create_index(op.f("ix_tasks_project_id"), "tasks", ["project_id"], unique=False)
    op.create_index(op.f("ix_tasks_assignee_id"), "tasks", ["assignee_id"], unique=False)
    op.create_index(op.f("ix_tasks_sprint_id"), "tasks", ["sprint_id"], unique=False)
    op.create_index(op.f("ix_tasks_external_id"), "tasks", ["external_id"], unique=False)
    op.create_index(op.f("ix_tasks_state"), "tasks", ["state"], unique=False)
    op.create_index(op.f("ix_tasks_reference_number"), "tasks", ["reference_number"], unique=True)

    # 4. task_comments (BasePattern — FKs to tasks, self-ref parent_id)
    op.create_table(
        "task_comments",
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["task_comments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_comments_task_id"), "task_comments", ["task_id"], unique=False)
    op.create_index(op.f("ix_task_comments_author_id"), "task_comments", ["author_id"], unique=False)
    op.create_index(op.f("ix_task_comments_parent_id"), "task_comments", ["parent_id"], unique=False)
    op.create_index(op.f("ix_task_comments_external_id"), "task_comments", ["external_id"], unique=False)

    # 5. task_tags (BasePattern — no FKs, unique on name)
    op.create_table(
        "task_tags",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("group", sa.String(length=100), nullable=True),
        sa.Column("is_exclusive", sa.Boolean(), nullable=True),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_tags_name"), "task_tags", ["name"], unique=True)
    op.create_index(op.f("ix_task_tags_external_id"), "task_tags", ["external_id"], unique=False)

    # 6. task_tag_assignments (junction table — composite PK)
    op.create_table(
        "task_tag_assignments",
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["task_tags.id"]),
        sa.PrimaryKeyConstraint("task_id", "tag_id"),
    )

    # 7. task_relations (BasePattern — FKs to tasks, unique constraint)
    op.create_table(
        "task_relations",
        sa.Column("source_task_id", sa.UUID(), nullable=False),
        sa.Column("target_task_id", sa.UUID(), nullable=False),
        sa.Column("relation_type", sa.String(length=20), nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["source_task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["target_task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_task_id", "target_task_id", "relation_type", name="uq_task_relation"),
    )
    op.create_index(op.f("ix_task_relations_source_task_id"), "task_relations", ["source_task_id"], unique=False)
    op.create_index(op.f("ix_task_relations_target_task_id"), "task_relations", ["target_task_id"], unique=False)
    op.create_index(op.f("ix_task_relations_external_id"), "task_relations", ["external_id"], unique=False)


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index(op.f("ix_task_relations_external_id"), table_name="task_relations")
    op.drop_index(op.f("ix_task_relations_target_task_id"), table_name="task_relations")
    op.drop_index(op.f("ix_task_relations_source_task_id"), table_name="task_relations")
    op.drop_table("task_relations")

    op.drop_table("task_tag_assignments")

    op.drop_index(op.f("ix_task_tags_external_id"), table_name="task_tags")
    op.drop_index(op.f("ix_task_tags_name"), table_name="task_tags")
    op.drop_table("task_tags")

    op.drop_index(op.f("ix_task_comments_external_id"), table_name="task_comments")
    op.drop_index(op.f("ix_task_comments_parent_id"), table_name="task_comments")
    op.drop_index(op.f("ix_task_comments_author_id"), table_name="task_comments")
    op.drop_index(op.f("ix_task_comments_task_id"), table_name="task_comments")
    op.drop_table("task_comments")

    op.drop_index(op.f("ix_tasks_reference_number"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_state"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_external_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_sprint_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_assignee_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_project_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_title"), table_name="tasks")
    op.drop_table("tasks")

    op.drop_index(op.f("ix_sprints_reference_number"), table_name="sprints")
    op.drop_index(op.f("ix_sprints_state"), table_name="sprints")
    op.drop_index(op.f("ix_sprints_starts_at"), table_name="sprints")
    op.drop_index(op.f("ix_sprints_external_id"), table_name="sprints")
    op.drop_index(op.f("ix_sprints_project_id"), table_name="sprints")
    op.drop_index(op.f("ix_sprints_number"), table_name="sprints")
    op.drop_index(op.f("ix_sprints_name"), table_name="sprints")
    op.drop_table("sprints")

    op.drop_index(op.f("ix_task_projects_reference_number"), table_name="task_projects")
    op.drop_index(op.f("ix_task_projects_state"), table_name="task_projects")
    op.drop_index(op.f("ix_task_projects_external_id"), table_name="task_projects")
    op.drop_index(op.f("ix_task_projects_lead_id"), table_name="task_projects")
    op.drop_index(op.f("ix_task_projects_name"), table_name="task_projects")
    op.drop_table("task_projects")
