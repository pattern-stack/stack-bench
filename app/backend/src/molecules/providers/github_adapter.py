from __future__ import annotations

import base64
import re
from pathlib import PurePosixPath
from typing import Protocol

import httpx
from pattern_stack.atoms.cache import get_cache
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Protocol DTOs
# ---------------------------------------------------------------------------


class DiffLine(BaseModel):
    type: str  # "context" | "add" | "del" | "hunk"
    old_num: int | None = None
    new_num: int | None = None
    content: str


class DiffHunk(BaseModel):
    header: str
    lines: list[DiffLine]


class DiffFile(BaseModel):
    path: str
    change_type: str  # "added" | "modified" | "deleted" | "renamed"
    additions: int
    deletions: int
    hunks: list[DiffHunk]


class DiffData(BaseModel):
    files: list[DiffFile]
    total_additions: int
    total_deletions: int


class FileTreeNode(BaseModel):
    name: str
    path: str
    type: str  # "file" | "dir"
    children: list[FileTreeNode] | None = None
    size: int | None = None


class FileContent(BaseModel):
    path: str
    content: str
    size: int
    language: str | None = None
    lines: int
    truncated: bool = False


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class GitRepoProtocol(Protocol):
    """Read-only access to git repository data."""

    async def get_diff(self, owner: str, repo: str, base_ref: str, head_ref: str) -> DiffData: ...

    async def get_file_tree(self, owner: str, repo: str, ref: str) -> FileTreeNode: ...

    async def get_file_content(self, owner: str, repo: str, ref: str, path: str) -> FileContent: ...


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


# ---------------------------------------------------------------------------
# Language detection from file extension
# ---------------------------------------------------------------------------

_EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".css": "css",
    ".scss": "scss",
    ".html": "html",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".dockerfile": "dockerfile",
    ".xml": "xml",
    ".graphql": "graphql",
    ".proto": "protobuf",
    ".vue": "vue",
    ".svelte": "svelte",
}


def _detect_language(path: str) -> str | None:
    """Detect language from file extension."""
    name = PurePosixPath(path).name.lower()
    if name == "dockerfile":
        return "dockerfile"
    if name in ("makefile", "justfile"):
        return "makefile"
    suffix = PurePosixPath(path).suffix.lower()
    return _EXTENSION_LANGUAGE_MAP.get(suffix)


_MAX_CONTENT_SIZE = 100 * 1024  # 100KB
_CACHE_NS = "github"
_CACHE_TTL = 3600  # 1 hour — git SHAs are content-addressed, safe to cache long


# ---------------------------------------------------------------------------
# Diff parsing utilities
# ---------------------------------------------------------------------------

# Matches the hunk header: @@ -old_start[,old_count] +new_start[,new_count] @@ optional text
_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$")


def _parse_patch(patch: str) -> list[DiffHunk]:
    """Parse a unified-diff patch string into DiffHunk objects."""
    hunks: list[DiffHunk] = []
    current_hunk: DiffHunk | None = None
    old_num = 0
    new_num = 0

    for raw_line in patch.split("\n"):
        hunk_match = _HUNK_HEADER_RE.match(raw_line)
        if hunk_match:
            old_num = int(hunk_match.group(1))
            new_num = int(hunk_match.group(2))
            current_hunk = DiffHunk(header=raw_line, lines=[])
            hunks.append(current_hunk)
            current_hunk.lines.append(DiffLine(type="hunk", old_num=None, new_num=None, content=raw_line))
            continue

        if current_hunk is None:
            continue

        if raw_line.startswith("+"):
            current_hunk.lines.append(DiffLine(type="add", old_num=None, new_num=new_num, content=raw_line[1:]))
            new_num += 1
        elif raw_line.startswith("-"):
            current_hunk.lines.append(DiffLine(type="del", old_num=old_num, new_num=None, content=raw_line[1:]))
            old_num += 1
        else:
            # Context line (starts with space or is empty)
            content = raw_line[1:] if raw_line.startswith(" ") else raw_line
            current_hunk.lines.append(DiffLine(type="context", old_num=old_num, new_num=new_num, content=content))
            old_num += 1
            new_num += 1

    return hunks


def _build_file_tree(entries: list[dict[str, object]]) -> FileTreeNode:
    """Build a recursive FileTreeNode from GitHub's flat tree array."""
    root = FileTreeNode(name=".", path="", type="dir", children=[])
    # Map path -> node for quick parent lookup
    dir_map: dict[str, FileTreeNode] = {"": root}

    # Sort entries so directories come first and paths are alphabetical
    sorted_entries = sorted(entries, key=lambda e: str(e.get("path", "")))

    for entry in sorted_entries:
        path = str(entry.get("path", ""))
        entry_type = str(entry.get("type", ""))
        size = entry.get("size")

        parts = path.split("/")
        name = parts[-1]

        # Ensure all parent directories exist
        for i in range(1, len(parts)):
            dir_path = "/".join(parts[:i])
            if dir_path not in dir_map:
                dir_name = parts[i - 1]
                dir_node = FileTreeNode(name=dir_name, path=dir_path, type="dir", children=[])
                parent_path = "/".join(parts[: i - 1]) if i > 1 else ""
                parent = dir_map.get(parent_path, root)
                if parent.children is None:
                    parent.children = []
                parent.children.append(dir_node)
                dir_map[dir_path] = dir_node

        if entry_type == "tree":
            # Directory entry from GitHub
            if path not in dir_map:
                node = FileTreeNode(name=name, path=path, type="dir", children=[])
                parent_path = "/".join(parts[:-1])
                parent = dir_map.get(parent_path, root)
                if parent.children is None:
                    parent.children = []
                parent.children.append(node)
                dir_map[path] = node
        elif entry_type == "blob":
            # File entry
            node = FileTreeNode(
                name=name,
                path=path,
                type="file",
                children=None,
                size=int(str(size)) if size is not None else None,
            )
            parent_path = "/".join(parts[:-1])
            parent = dir_map.get(parent_path, root)
            if parent.children is None:
                parent.children = []
            parent.children.append(node)

    return root


# Map GitHub status values to our change_type
_STATUS_MAP: dict[str, str] = {
    "added": "added",
    "modified": "modified",
    "removed": "deleted",
    "renamed": "renamed",
    "changed": "modified",
    "copied": "added",
}


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
        """Remove draft status from a pull request."""
        response = await self._client.patch(
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
            json={"draft": False},
        )
        self._raise_for_status(response)

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

    async def hydrate_stack(
        self, owner: str, repo: str, branches: list[tuple[str, str, str]]
    ) -> None:
        """Pre-load cache for an entire stack's diffs.

        Args:
            branches: List of (branch_name, base_ref, head_ref) tuples
        """
        import asyncio

        tasks = [self.get_diff(owner, repo, base, head) for _, base, head in branches]
        await asyncio.gather(*tasks, return_exceptions=True)
