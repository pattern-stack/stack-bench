"""Constants and mappings for GitHub Issues adapter."""

from agentic_patterns.core.atoms.protocols import (
    IssueType,
    Priority,
    ProjectStatus,
    StatusCategory,
    TagGroup,
    WorkPhase,
)

# Label prefix patterns for status encoding
# Labels: "phase:planning", "phase:implementation"
PHASE_LABELS: dict[str, WorkPhase] = {
    "phase:planning": WorkPhase.PLANNING,
    "phase:implementation": WorkPhase.IMPLEMENTATION,
}
REVERSE_PHASE_LABELS: dict[WorkPhase, str] = {v: k for k, v in PHASE_LABELS.items()}

# Labels: "status:todo", "status:in-progress", "status:in-review", etc.
STATUS_LABELS: dict[str, StatusCategory] = {
    "status:todo": StatusCategory.TODO,
    "status:in-progress": StatusCategory.IN_PROGRESS,
    "status:in-review": StatusCategory.IN_REVIEW,
    "status:done": StatusCategory.DONE,
    "status:cancelled": StatusCategory.CANCELLED,
}
REVERSE_STATUS_LABELS: dict[StatusCategory, str] = {v: k for k, v in STATUS_LABELS.items()}

# Labels: "type:epic", "type:story", etc.
TYPE_LABELS: dict[str, IssueType] = {
    "type:epic": IssueType.EPIC,
    "type:story": IssueType.STORY,
    "type:task": IssueType.TASK,
    "type:bug": IssueType.BUG,
    "type:subtask": IssueType.SUBTASK,
}
REVERSE_TYPE_LABELS: dict[IssueType, str] = {v: k for k, v in TYPE_LABELS.items()}

# Labels: "priority:urgent", "priority:high", etc.
PRIORITY_LABELS: dict[str, Priority] = {
    "priority:urgent": Priority.URGENT,
    "priority:high": Priority.HIGH,
    "priority:medium": Priority.MEDIUM,
    "priority:low": Priority.LOW,
}
REVERSE_PRIORITY_LABELS: dict[Priority, str] = {v: k for k, v in PRIORITY_LABELS.items()}

# Milestone status -> SprintStatus mapping (GitHub milestones = sprints)
# open milestone = PLANNED or ACTIVE, closed = COMPLETED

# Project status mapping
PROJECT_STATUS_MAP: dict[str, ProjectStatus] = {
    "open": ProjectStatus.ACTIVE,
    "closed": ProjectStatus.COMPLETED,
}

# Tag groups by label prefix
TAG_GROUP_PREFIXES: dict[str, TagGroup] = {
    "type:": TagGroup.ISSUE_TYPE,
    "phase:": TagGroup.PHASE,
    "status:": TagGroup.STATE,
    "priority:": TagGroup.PRIORITY,
    "domain:": TagGroup.DOMAIN,
    "stack:": TagGroup.STACK,
}

# GitHub reaction content -> emoji mapping
GITHUB_REACTION_EMOJI: dict[str, str] = {
    "+1": "+1",
    "-1": "-1",
    "laugh": "laugh",
    "confused": "confused",
    "heart": "heart",
    "hooray": "hooray",
    "rocket": "rocket",
    "eyes": "eyes",
}


def label_to_tag_group(label_name: str) -> TagGroup:
    """Determine TagGroup from label name prefix."""
    for prefix, group in TAG_GROUP_PREFIXES.items():
        if label_name.startswith(prefix):
            return group
    return TagGroup.CUSTOM
