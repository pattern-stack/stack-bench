"""GitHub Issues adapter for task management protocols."""

from .adapter import GitHubIssuesAdapter
from .client import GitHubClient

__all__ = ["GitHubIssuesAdapter", "GitHubClient"]
