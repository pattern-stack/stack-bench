from uuid import UUID


class MoleculeError(Exception):
    """Base for all molecule errors."""


class ConversationNotFoundError(MoleculeError):
    def __init__(self, conversation_id: UUID) -> None:
        super().__init__(f"Conversation {conversation_id} not found")
        self.conversation_id = conversation_id


class AgentNotFoundError(MoleculeError):
    def __init__(self, name: str, available: list[str] | None = None) -> None:
        available_str = ", ".join(available) if available else "(none)"
        super().__init__(f"Agent '{name}' not found. Available: {available_str}")
        self.name = name
        self.available = available or []


class StackNotFoundError(MoleculeError):
    def __init__(self, stack_id: UUID) -> None:
        super().__init__(f"Stack {stack_id} not found")
        self.stack_id = stack_id


class BranchNotFoundError(MoleculeError):
    def __init__(self, branch_id: UUID) -> None:
        super().__init__(f"Branch {branch_id} not found")
        self.branch_id = branch_id


class PullRequestNotFoundError(MoleculeError):
    def __init__(self, pull_request_id: UUID) -> None:
        super().__init__(f"PullRequest {pull_request_id} not found")
        self.pull_request_id = pull_request_id


class StackCycleError(MoleculeError):
    def __init__(self, stack_id: UUID, base_branch_id: UUID) -> None:
        super().__init__(f"Setting base_branch_id={base_branch_id} on stack {stack_id} would create a cycle")
        self.stack_id = stack_id
        self.base_branch_id = base_branch_id


# --- Task management errors ---


class TaskNotFoundError(MoleculeError):
    def __init__(self, task_id: UUID) -> None:
        super().__init__(f"Task {task_id} not found")
        self.task_id = task_id


class TaskProjectNotFoundError(MoleculeError):
    def __init__(self, project_id: UUID) -> None:
        super().__init__(f"TaskProject {project_id} not found")
        self.project_id = project_id


class SprintNotFoundError(MoleculeError):
    def __init__(self, sprint_id: UUID) -> None:
        super().__init__(f"Sprint {sprint_id} not found")
        self.sprint_id = sprint_id


class TaskHasBlockersError(MoleculeError):
    def __init__(self, task_id: UUID, blocker_ids: list[UUID]) -> None:
        super().__init__(f"Task {task_id} has open blockers: {blocker_ids}")
        self.task_id = task_id
        self.blocker_ids = blocker_ids


class RelationCycleError(MoleculeError):
    def __init__(self, source_id: UUID, target_id: UUID, relation_type: str) -> None:
        super().__init__(f"Creating {relation_type} relation from {source_id} to {target_id} would create a cycle")
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type


class SyncNotConfiguredError(MoleculeError):
    def __init__(self) -> None:
        super().__init__("Sync is not configured — no adapter was provided")
