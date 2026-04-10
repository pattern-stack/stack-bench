"""LocalGitAdapter — read diffs, trees, and files from local git clones.

Implements GitRepoProtocol by running git commands against a local clone
on disk, so stack-bench can serve diffs, file trees, and file content for
workspaces that have a local_path without needing a GitHub token.
"""

from __future__ import annotations

import asyncio
import re

from molecules.providers.git_types import (
    _MAX_CONTENT_SIZE,
    DiffData,
    DiffFile,
    FileContent,
    FileTreeNode,
    _build_file_tree,
    _detect_language,
    _parse_patch,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LocalGitError(Exception):
    """Base error for local git operations."""

    def __init__(self, message: str, returncode: int = 1) -> None:
        super().__init__(message)
        self.returncode = returncode


class LocalGitRefNotFoundError(LocalGitError):
    """A requested ref (branch, SHA) does not exist in the local repo."""


# ---------------------------------------------------------------------------
# Status code mapping (git --name-status letters to our change_type)
# ---------------------------------------------------------------------------

_NAME_STATUS_MAP: dict[str, str] = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "T": "modified",  # type change
    "C": "added",  # copied
}

# Regex to split full `git diff` output by file boundary
_DIFF_FILE_RE = re.compile(r"^diff --git a/.+ b/(.+)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# LocalGitAdapter
# ---------------------------------------------------------------------------


class LocalGitAdapter:
    """Implements GitRepoProtocol using local git subprocess calls.

    The owner/repo parameters required by the protocol are accepted but
    ignored -- the adapter uses repo_path from __init__ instead.
    """

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path

    async def _run(self, *args: str, errors: str = "strict") -> str:
        """Run a git command in the repo directory, return stdout.

        Raises LocalGitRefNotFoundError for exit code 128 with revision errors.
        Raises LocalGitError for other non-zero exit codes.
        """
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.repo_path,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors=errors)
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            # Detect missing ref / bad revision errors (exit code 128)
            if proc.returncode == 128 or "bad revision" in stderr or "does not exist" in stderr:
                raise LocalGitRefNotFoundError(stderr.strip(), returncode=proc.returncode or 128)
            raise LocalGitError(stderr.strip(), returncode=proc.returncode or 1)

        return stdout

    # --- Protocol methods ---

    async def get_diff(self, owner: str, repo: str, base_ref: str, head_ref: str) -> DiffData:
        """Get diff between two refs using local git.

        Uses three-dot diff (base...head) to match GitHub PR behavior.
        """
        # Step 1: Get name-status for change types
        name_status_raw = await self._run("diff", "--name-status", f"{base_ref}...{head_ref}")

        # Step 2: Get full unified diff
        diff_raw = await self._run("diff", f"{base_ref}...{head_ref}")

        # Parse name-status into a lookup: path -> change_type
        status_map: dict[str, str] = {}
        rename_map: dict[str, str] = {}  # old_path -> new_path for renames
        for line in name_status_raw.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            status_code = parts[0]
            if status_code.startswith("R"):
                # Rename: R100\told_path\tnew_path
                old_path = parts[1] if len(parts) > 1 else ""
                new_path = parts[2] if len(parts) > 2 else old_path
                status_map[new_path] = "renamed"
                rename_map[old_path] = new_path
            else:
                file_path = parts[1] if len(parts) > 1 else ""
                status_map[file_path] = _NAME_STATUS_MAP.get(status_code, "modified")

        # Split diff output by file boundaries
        file_patches = self._split_diff(diff_raw)

        # Build DiffFile list
        files: list[DiffFile] = []
        total_additions = 0
        total_deletions = 0
        seen_paths: set[str] = set()

        for file_path, patch_text in file_patches.items():
            # Detect binary files
            if "Binary files" in patch_text and "differ" in patch_text:
                change_type = status_map.get(file_path, "modified")
                files.append(
                    DiffFile(
                        path=file_path,
                        change_type=change_type,
                        additions=0,
                        deletions=0,
                        hunks=[],
                    )
                )
                seen_paths.add(file_path)
                continue

            hunks = _parse_patch(patch_text)
            additions = sum(1 for h in hunks for ln in h.lines if ln.type == "add")
            deletions = sum(1 for h in hunks for ln in h.lines if ln.type == "del")
            total_additions += additions
            total_deletions += deletions

            change_type = status_map.get(file_path, "modified")

            files.append(
                DiffFile(
                    path=file_path,
                    change_type=change_type,
                    additions=additions,
                    deletions=deletions,
                    hunks=hunks,
                )
            )
            seen_paths.add(file_path)

        # Include files from name-status that had no diff output (e.g. renames with 100% similarity)
        for path, change_type in status_map.items():
            if path not in seen_paths:
                files.append(
                    DiffFile(
                        path=path,
                        change_type=change_type,
                        additions=0,
                        deletions=0,
                        hunks=[],
                    )
                )

        return DiffData(
            files=files,
            total_additions=total_additions,
            total_deletions=total_deletions,
        )

    async def get_file_tree(self, owner: str, repo: str, ref: str) -> FileTreeNode:
        """Get file tree at a ref using git ls-tree."""
        ls_output = await self._run("ls-tree", "-r", "--long", ref)

        entries: list[dict[str, object]] = []
        for line in ls_output.strip().split("\n"):
            if not line.strip():
                continue
            # Format: <mode> <type> <hash> <size>\t<path>
            meta, path = line.split("\t", 1)
            parts = meta.split()
            if len(parts) < 4:
                continue
            mode = parts[0]
            entry_type = parts[1]
            size_str = parts[3].strip()

            # Skip submodules (mode 160000, type commit)
            if entry_type == "commit" or mode == "160000":
                continue

            size = int(size_str) if size_str.isdigit() else None
            entries.append({"path": path, "type": entry_type, "size": size})

        return _build_file_tree(entries)

    async def get_file_content(self, owner: str, repo: str, ref: str, path: str) -> FileContent:
        """Get file content at a ref using git show."""
        # Get file size first
        size_str = await self._run("cat-file", "-s", f"{ref}:{path}")
        size = int(size_str.strip())

        # Get content (use replace for binary safety)
        content = await self._run("show", f"{ref}:{path}", errors="replace")

        # Truncate if too large
        truncated = len(content) > _MAX_CONTENT_SIZE
        if truncated:
            content = content[:_MAX_CONTENT_SIZE]

        # Count lines
        line_count = content.count("\n") + (1 if not content.endswith("\n") else 0) if content else 0

        language = _detect_language(path)

        return FileContent(
            path=path,
            content=content,
            size=size,
            language=language,
            lines=line_count,
            truncated=truncated,
        )

    async def get_behind_count(self, owner: str, repo: str, base_ref: str, head_ref: str) -> int:
        """Count commits on base not on head using git rev-list."""
        output = await self._run("rev-list", "--count", f"{head_ref}..{base_ref}")
        return int(output.strip())

    # --- Internal helpers ---

    @staticmethod
    def _split_diff(diff_raw: str) -> dict[str, str]:
        """Split a full git diff output into per-file patches.

        Returns a dict of {file_path: patch_text}.
        """
        if not diff_raw.strip():
            return {}

        result: dict[str, str] = {}
        # Find all file boundary positions
        boundaries: list[tuple[int, str]] = []
        for match in _DIFF_FILE_RE.finditer(diff_raw):
            boundaries.append((match.start(), match.group(1)))

        for i, (start, file_path) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(diff_raw)
            result[file_path] = diff_raw[start:end]

        return result
