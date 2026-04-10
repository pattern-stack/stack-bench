from __future__ import annotations

import base64

import httpx
from pattern_stack.atoms.cache import get_cache

# Re-export shared types from git_types so existing imports keep working.
# The ``as`` aliases tell mypy these are explicit re-exports (strict mode).
from molecules.providers.git_types import _MAX_CONTENT_SIZE as _MAX_CONTENT_SIZE
from molecules.providers.git_types import _STATUS_MAP as _STATUS_MAP
from molecules.providers.git_types import DiffData as DiffData
from molecules.providers.git_types import DiffFile as DiffFile
from molecules.providers.git_types import DiffHunk as DiffHunk
from molecules.providers.git_types import DiffLine as DiffLine
from molecules.providers.git_types import FileContent as FileContent
from molecules.providers.git_types import FileTreeNode as FileTreeNode
from molecules.providers.git_types import GitRepoProtocol as GitRepoProtocol
from molecules.providers.git_types import _build_file_tree as _build_file_tree
from molecules.providers.git_types import _detect_language as _detect_language
from molecules.providers.git_types import _parse_patch as _parse_patch

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GitHubAPIError(Exception):
    """Base error for GitHub API failures."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubNotFoundError(GitHubAPIError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(404, message)


class GitHubRateLimitError(GitHubAPIError):
    def __init__(self) -> None:
        super().__init__(403, "GitHub API rate limit exceeded")


_CACHE_NS = "github"
_CACHE_TTL = 3600  # 1 hour — git SHAs are content-addressed, safe to cache long


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------


def parse_owner_repo(repo_url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL.

    Supports:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git
    """
    url = repo_url.rstrip("/")

    # SSH format
    if url.startswith("git@"):
        # git@github.com:owner/repo.git
        _, path = url.split(":", 1)
        path = path.removesuffix(".git")
        parts = path.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]

    # HTTPS format
    url = url.removesuffix(".git")
    parts = url.split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]

    msg = f"Cannot parse owner/repo from URL: {repo_url}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# GitHubAdapter
# ---------------------------------------------------------------------------


class GitHubAdapter:
    """Implements GitRepoProtocol using GitHub REST API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str = "") -> None:
        headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, headers=headers, timeout=30.0)
        self._cache = get_cache()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Raise appropriate exception for HTTP errors."""
        if response.status_code == 404:
            raise GitHubNotFoundError()
        if response.status_code == 403:
            remaining = response.headers.get("x-ratelimit-remaining", "")
            if remaining == "0":
                raise GitHubRateLimitError()
            raise GitHubAPIError(403, "Forbidden")
        if response.status_code >= 400:
            raise GitHubAPIError(response.status_code, f"GitHub API error: {response.status_code}")

    async def get_diff(self, owner: str, repo: str, base_ref: str, head_ref: str) -> DiffData:
        """Get diff between two refs via GitHub compare API."""
        cache_key = f"diff:{owner}/{repo}:{base_ref}:{head_ref}"
        cached = await self._cache.get(cache_key, namespace=_CACHE_NS)
        if cached is not None:
            return DiffData.model_validate(cached)

        response = await self._client.get(f"/repos/{owner}/{repo}/compare/{base_ref}...{head_ref}")
        self._raise_for_status(response)
        data = response.json()

        total_additions = 0
        total_deletions = 0
        files: list[DiffFile] = []

        for file_entry in data.get("files", []):
            patch = file_entry.get("patch", "")
            hunks = _parse_patch(patch) if patch else []
            status = str(file_entry.get("status", "modified"))
            change_type = _STATUS_MAP.get(status, "modified")
            additions = int(file_entry.get("additions", 0))
            deletions = int(file_entry.get("deletions", 0))
            total_additions += additions
            total_deletions += deletions

            files.append(
                DiffFile(
                    path=str(file_entry.get("filename", "")),
                    change_type=change_type,
                    additions=additions,
                    deletions=deletions,
                    hunks=hunks,
                )
            )

        result = DiffData(
            files=files,
            total_additions=total_additions,
            total_deletions=total_deletions,
        )
        await self._cache.set(cache_key, result.model_dump(), ttl=_CACHE_TTL, namespace=_CACHE_NS)
        return result

    async def get_file_tree(self, owner: str, repo: str, ref: str) -> FileTreeNode:
        """Get file tree at a ref via GitHub git trees API."""
        cache_key = f"tree:{owner}/{repo}:{ref}"
        cached = await self._cache.get(cache_key, namespace=_CACHE_NS)
        if cached is not None:
            return FileTreeNode.model_validate(cached)

        response = await self._client.get(
            f"/repos/{owner}/{repo}/git/trees/{ref}",
            params={"recursive": "1"},
        )
        self._raise_for_status(response)
        data = response.json()

        entries: list[dict[str, object]] = data.get("tree", [])
        result = _build_file_tree(entries)
        await self._cache.set(cache_key, result.model_dump(), ttl=_CACHE_TTL, namespace=_CACHE_NS)
        return result

    async def get_file_content(self, owner: str, repo: str, ref: str, path: str) -> FileContent:
        """Get file content at a ref via GitHub contents API."""
        cache_key = f"file:{owner}/{repo}:{ref}:{path}"
        cached = await self._cache.get(cache_key, namespace=_CACHE_NS)
        if cached is not None:
            return FileContent.model_validate(cached)

        response = await self._client.get(
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )
        self._raise_for_status(response)
        data = response.json()

        raw_content = data.get("content", "")
        encoding = data.get("encoding", "")
        size = int(data.get("size", 0))

        if encoding == "base64":
            decoded = base64.b64decode(raw_content).decode("utf-8", errors="replace")
        else:
            decoded = str(raw_content)

        truncated = len(decoded) > _MAX_CONTENT_SIZE
        if truncated:
            decoded = decoded[:_MAX_CONTENT_SIZE]

        line_count = decoded.count("\n") + (1 if decoded and not decoded.endswith("\n") else 0)
        language = _detect_language(path)

        result = FileContent(
            path=path,
            content=decoded,
            size=size,
            language=language,
            lines=line_count,
            truncated=truncated,
        )
        await self._cache.set(cache_key, result.model_dump(), ttl=_CACHE_TTL, namespace=_CACHE_NS)
        return result

    async def get_behind_count(self, owner: str, repo: str, base_ref: str, head_ref: str) -> int:
        """Return how many commits head_ref is behind base_ref.

        Uses the compare API: GET /repos/{owner}/{repo}/compare/{base}...{head}
        The response includes `behind_by` which counts commits on base not on head.
        """
        cache_key = f"behind:{owner}/{repo}:{base_ref}:{head_ref}"
        cached = await self._cache.get(cache_key, namespace=_CACHE_NS)
        if cached is not None:
            return int(cached)

        response = await self._client.get(f"/repos/{owner}/{repo}/compare/{base_ref}...{head_ref}")
        self._raise_for_status(response)
        data = response.json()
        behind_by = int(data.get("behind_by", 0))

        await self._cache.set(cache_key, behind_by, ttl=_CACHE_TTL, namespace=_CACHE_NS)
        return behind_by

    async def merge_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        merge_method: str = "squash",
    ) -> dict[str, object]:
        """Merge a pull request via GitHub API."""
        response = await self._client.put(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/merge",
            json={"merge_method": merge_method},
        )
        self._raise_for_status(response)
        data: dict[str, object] = response.json()
        return data

    async def mark_pr_ready(self, owner: str, repo: str, pr_number: int) -> None:
        """Remove draft status from a pull request.

        GitHub REST API v3 does not support removing draft status via PATCH.
        This requires the GraphQL mutation ``markPullRequestReadyForReview``.
        We first look up the PR's GraphQL node ID via REST, then call the
        mutation on api.github.com/graphql.
        """
        # Step 1: Get the node_id from the REST API
        rest_response = await self._client.get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
        )
        self._raise_for_status(rest_response)
        node_id = str(rest_response.json().get("node_id", ""))
        if not node_id:
            raise GitHubAPIError(500, "PR response missing node_id")

        # Step 2: Call the GraphQL mutation
        mutation = """
            mutation MarkReady($pullRequestId: ID!) {
                markPullRequestReadyForReview(input: {pullRequestId: $pullRequestId}) {
                    pullRequest { id }
                }
            }
        """
        gql_response = await self._client.post(
            "https://api.github.com/graphql",
            json={"query": mutation, "variables": {"pullRequestId": node_id}},
        )
        self._raise_for_status(gql_response)
        gql_data = gql_response.json()
        if "errors" in gql_data:
            error_msg = gql_data["errors"][0].get("message", "GraphQL error")
            raise GitHubAPIError(422, f"GraphQL markPullRequestReadyForReview failed: {error_msg}")

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        *,
        body: str | None = None,
        draft: bool = True,
    ) -> dict[str, object]:
        """Create a pull request on GitHub.

        Args:
            owner: Repository owner (org or user).
            repo: Repository name.
            title: PR title.
            head: Head branch name.
            base: Base branch name (parent branch or trunk).
            body: Optional PR description/body.
            draft: Whether to create as draft (default True).

        Returns:
            GitHub API response dict with at least 'number', 'html_url', 'state'.
        """
        payload: dict[str, object] = {
            "title": title,
            "head": head,
            "base": base,
            "draft": draft,
        }
        if body is not None:
            payload["body"] = body
        response = await self._client.post(
            f"/repos/{owner}/{repo}/pulls",
            json=payload,
        )
        self._raise_for_status(response)
        data: dict[str, object] = response.json()
        return data

    async def update_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        *,
        title: str | None = None,
        body: str | None = None,
        base: str | None = None,
    ) -> dict[str, object]:
        """Update an existing pull request on GitHub.

        Used when a branch's base changes after restack (need to update PR base).
        """
        payload: dict[str, object] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if base is not None:
            payload["base"] = base
        response = await self._client.patch(
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
            json=payload,
        )
        self._raise_for_status(response)
        data: dict[str, object] = response.json()
        return data

    async def create_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        path: str,
        line: int,
        commit_id: str,
        side: str = "RIGHT",
    ) -> dict[str, object]:
        """Create an inline review comment on a PR."""
        response = await self._client.post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
            json={"body": body, "path": path, "line": line, "side": side, "commit_id": commit_id},
        )
        self._raise_for_status(response)
        data: dict[str, object] = response.json()
        return data

    async def list_review_comments(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[dict[str, object]]:
        """List all inline review comments on a PR."""
        response = await self._client.get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
        )
        self._raise_for_status(response)
        result: list[dict[str, object]] = response.json()
        return result

    async def hydrate_stack(self, owner: str, repo: str, branches: list[tuple[str, str, str]]) -> None:
        """Pre-load cache for an entire stack's diffs.

        Args:
            branches: List of (branch_name, base_ref, head_ref) tuples
        """
        import asyncio

        tasks = [self.get_diff(owner, repo, base, head) for _, base, head in branches]
        await asyncio.gather(*tasks, return_exceptions=True)
