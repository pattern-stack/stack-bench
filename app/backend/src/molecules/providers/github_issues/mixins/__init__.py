"""GitHub Issues adapter protocol mixins."""

from .comment import GitHubCommentMixin
from .document import GitHubDocumentMixin
from .project import GitHubProjectMixin
from .sprint import GitHubSprintMixin
from .tag import GitHubTagMixin
from .task import GitHubTaskMixin
from .user import GitHubUserMixin

__all__ = [
    "GitHubCommentMixin",
    "GitHubDocumentMixin",
    "GitHubProjectMixin",
    "GitHubSprintMixin",
    "GitHubTagMixin",
    "GitHubTaskMixin",
    "GitHubUserMixin",
]
