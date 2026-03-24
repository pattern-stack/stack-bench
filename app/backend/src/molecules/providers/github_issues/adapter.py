"""GitHub Issues adapter implementing all domain protocols."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .mixins import (
    GitHubCommentMixin,
    GitHubDocumentMixin,
    GitHubProjectMixin,
    GitHubSprintMixin,
    GitHubTagMixin,
    GitHubTaskMixin,
    GitHubUserMixin,
)

if TYPE_CHECKING:
    from .client import GitHubClient


class GitHubIssuesAdapter(
    GitHubTaskMixin,
    GitHubCommentMixin,
    GitHubProjectMixin,
    GitHubSprintMixin,
    GitHubTagMixin,
    GitHubUserMixin,
    GitHubDocumentMixin,
):
    """Adapter implementing all task management protocols for GitHub Issues.

    Maps GitHub concepts to our primitives:
    - GitHub Issue -> Task
    - GitHub Issue Comment -> Comment
    - GitHub Milestone -> Sprint
    - GitHub Label -> Tag
    - GitHub User/Team -> User/Team
    - GitHub meta-issues (label: meta:project) -> Project
    - Documents -> Not supported (stub)

    Status encoding uses label conventions:
    - phase:planning / phase:implementation
    - status:todo / status:in-progress / status:in-review / status:done / status:cancelled
    - type:epic / type:story / type:task / type:bug / type:subtask
    - priority:urgent / priority:high / priority:medium / priority:low

    Issue closed state = DONE or CANCELLED (based on labels).
    """

    def __init__(self, client: GitHubClient, owner: str, repo: str) -> None:
        self.client = client
        self.owner = owner
        self.repo = repo

    @property
    def _repo_path(self) -> str:
        return f"/repos/{self.owner}/{self.repo}"
