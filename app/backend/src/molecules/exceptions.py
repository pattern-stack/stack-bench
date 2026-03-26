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


class WorkspaceNotFoundError(MoleculeError):
    def __init__(self, workspace_id: UUID) -> None:
        super().__init__(f"Workspace {workspace_id} not found")
        self.workspace_id = workspace_id


class WorkspaceProvisionError(MoleculeError):
    def __init__(self, workspace_id: UUID, reason: str) -> None:
        super().__init__(f"Workspace {workspace_id} provisioning failed: {reason}")
        self.workspace_id = workspace_id
        self.reason = reason
