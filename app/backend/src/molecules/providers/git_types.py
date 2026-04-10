"""Shared types, DTOs, and parsing utilities for git adapters.

These are protocol-level types used by both GitHubAdapter and LocalGitAdapter.
Extracted from github_adapter.py for reuse without coupling to a specific adapter.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Protocol

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

    async def get_behind_count(self, owner: str, repo: str, base_ref: str, head_ref: str) -> int: ...


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
    """Build a recursive FileTreeNode from a flat tree array.

    Works with both GitHub API entries (with explicit tree/blob types)
    and local git ls-tree output (blobs only, directories implied).
    """
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
