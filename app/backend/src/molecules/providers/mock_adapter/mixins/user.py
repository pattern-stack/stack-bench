# mypy: disable-error-code="attr-defined"
"""Mock implementation of UserProtocol."""

from __future__ import annotations

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import Team, User, UserFilter


class MockUserMixin:
    """In-memory UserProtocol implementation."""

    async def get_user(self, id: str) -> User:
        if id not in self._users:
            raise NotFoundError("User", id)
        return User(**self._users[id])

    async def get_current_user(self) -> User:
        return await self.get_user(self._current_user_id)

    async def list_users(self, filter: UserFilter | None = None) -> list[User]:
        results = list(self._users.values())
        if filter is not None:
            if filter.user_type is not None:
                ut_val = filter.user_type.value if hasattr(filter.user_type, "value") else filter.user_type
                results = [
                    u
                    for u in results
                    if (u["user_type"].value if hasattr(u["user_type"], "value") else u["user_type"]) == ut_val
                ]
            if filter.role is not None:
                role_val = filter.role.value if hasattr(filter.role, "value") else filter.role
                results = [
                    u for u in results if (u["role"].value if hasattr(u["role"], "value") else u["role"]) == role_val
                ]
            if filter.is_active is not None:
                results = [u for u in results if u["is_active"] == filter.is_active]
            if filter.team_id is not None:
                team_data = self._teams.get(filter.team_id)
                if team_data:
                    member_ids = set(team_data["member_ids"])
                    results = [u for u in results if u["id"] in member_ids]
                else:
                    results = []
        return [User(**u) for u in results]

    async def get_users(self, ids: list[str]) -> list[User]:
        return [await self.get_user(id) for id in ids]

    async def get_team(self, id: str) -> Team:
        if id not in self._teams:
            raise NotFoundError("Team", id)
        return Team(**self._teams[id])

    async def list_teams(self) -> list[Team]:
        return [Team(**t) for t in self._teams.values()]

    async def get_team_members(self, team_id: str) -> list[User]:
        if team_id not in self._teams:
            raise NotFoundError("Team", team_id)
        member_ids = self._teams[team_id]["member_ids"]
        return [User(**self._users[uid]) for uid in member_ids if uid in self._users]
