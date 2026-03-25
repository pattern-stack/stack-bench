"""GitHub Issues implementation of UserProtocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import (
    Team,
    User,
    UserFilter,
    UserRole,
    UserType,
)

if TYPE_CHECKING:
    from ..client import GitHubClient


class GitHubUserMixin:
    """GitHub users and teams as UserProtocol implementation."""

    client: GitHubClient
    owner: str
    repo: str

    # -- helpers --

    def _to_user(self, data: dict[str, Any]) -> User:
        """Convert a GitHub user JSON to a User."""
        user_type = UserType.BOT if data.get("type") == "Bot" else UserType.HUMAN

        # GitHub doesn't expose roles in user objects.
        # Collaborator permission could be checked separately but is expensive.
        role = UserRole.MEMBER

        return User(
            id=str(data["id"]),
            name=data.get("name") or data.get("login", "unknown"),
            email=data.get("email"),
            avatar_url=data.get("avatar_url"),
            user_type=user_type,
            role=role,
            is_active=True,
        )

    def _to_team(self, data: dict[str, Any]) -> Team:
        """Convert a GitHub team JSON to a Team."""
        return Team(
            id=str(data["id"]),
            name=data["name"],
            key=data.get("slug"),
            description=data.get("description"),
            member_ids=[],  # Populated lazily via get_team_members
        )

    # -- Users --

    async def get_user(self, id: str) -> User:
        try:
            data = await self.client.get(f"/users/{id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("User", id) from e
            raise
        return self._to_user(data)

    async def get_current_user(self) -> User:
        data = await self.client.get("/user")
        return self._to_user(data)

    async def list_users(self, filter: UserFilter | None = None) -> list[User]:
        """List repository collaborators."""
        items = await self.client.get_paginated(f"/repos/{self.owner}/{self.repo}/collaborators")
        users = [self._to_user(item) for item in items]

        if filter is not None:
            if filter.user_type is not None:
                users = [u for u in users if u.user_type == filter.user_type]
            if filter.role is not None:
                users = [u for u in users if u.role == filter.role]
            if filter.is_active is not None:
                users = [u for u in users if u.is_active == filter.is_active]
            if filter.team_id is not None:
                # Get team members and filter
                try:
                    members = await self.get_team_members(filter.team_id)
                    member_ids = {m.id for m in members}
                    users = [u for u in users if u.id in member_ids]
                except NotFoundError:
                    users = []

        return users

    async def get_users(self, ids: list[str]) -> list[User]:
        return [await self.get_user(id) for id in ids]

    # -- Teams --

    async def get_team(self, id: str) -> Team:
        """Get a team by slug (id is used as slug)."""
        try:
            data = await self.client.get(f"/orgs/{self.owner}/teams/{id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Team", id) from e
            raise
        team = self._to_team(data)
        # Populate member_ids
        try:
            members = await self.get_team_members(id)
            team = Team(
                id=team.id,
                name=team.name,
                key=team.key,
                description=team.description,
                member_ids=[m.id for m in members],
            )
        except Exception:
            pass  # May not have org permissions
        return team

    async def list_teams(self) -> list[Team]:
        try:
            items = await self.client.get_paginated(f"/orgs/{self.owner}/teams")
        except Exception:
            # Owner might not be an org, or no permission
            return []
        return [self._to_team(item) for item in items]

    async def get_team_members(self, team_id: str) -> list[User]:
        """Get members of a team (team_id is the team slug)."""
        try:
            items = await self.client.get_paginated(f"/orgs/{self.owner}/teams/{team_id}/members")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Team", team_id) from e
            raise
        return [self._to_user(item) for item in items]
