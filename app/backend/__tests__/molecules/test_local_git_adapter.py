"""Unit tests for LocalGitAdapter -- subprocess-based git operations.

All tests mock asyncio.create_subprocess_exec to simulate git command output.
This matches the project's pattern: GitHub adapter tests mock httpx,
local adapter tests mock subprocess.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from molecules.providers.git_types import DiffData, FileContent, FileTreeNode
from molecules.providers.local_git_adapter import (
    LocalGitAdapter,
    LocalGitError,
    LocalGitRefNotFoundError,
)


def _make_process(stdout: str = "", stderr: str = "", returncode: int = 0) -> AsyncMock:
    """Create a mock subprocess that returns the given stdout/stderr."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    proc.returncode = returncode
    return proc


def _adapter(repo_path: str = "/tmp/test-repo") -> LocalGitAdapter:
    return LocalGitAdapter(repo_path)


# ---------------------------------------------------------------------------
# _run helper
# ---------------------------------------------------------------------------


class TestRun:
    @pytest.mark.unit
    async def test_returns_stdout(self) -> None:
        proc = _make_process(stdout="hello\n")
        with patch("molecules.providers.local_git_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            adapter = _adapter()
            result = await adapter._run("status")
            assert result == "hello\n"

    @pytest.mark.unit
    async def test_raises_on_nonzero_exit(self) -> None:
        proc = _make_process(stderr="fatal: not a git repository", returncode=128)
        with patch("molecules.providers.local_git_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            adapter = _adapter()
            with pytest.raises(LocalGitError, match="not a git repository"):
                await adapter._run("status")

    @pytest.mark.unit
    async def test_raises_ref_not_found_on_128_with_bad_revision(self) -> None:
        proc = _make_process(stderr="fatal: bad revision 'nonexistent'", returncode=128)
        with patch("molecules.providers.local_git_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            adapter = _adapter()
            with pytest.raises(LocalGitRefNotFoundError):
                await adapter._run("diff", "nonexistent...main")


# ---------------------------------------------------------------------------
# get_diff
# ---------------------------------------------------------------------------


class TestGetDiff:
    @pytest.mark.unit
    async def test_simple_modification(self) -> None:
        """Single file modified, one hunk."""
        name_status = "M\tsrc/main.py\n"
        diff_output = (
            "diff --git a/src/main.py b/src/main.py\n"
            "index abc..def 100644\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,3 +1,4 @@\n"
            " foo\n"
            "-old\n"
            "+new\n"
            "+extra\n"
        )
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=[name_status, diff_output])

        result = await adapter.get_diff("o", "r", "main", "feat")

        assert isinstance(result, DiffData)
        assert len(result.files) == 1
        assert result.files[0].path == "src/main.py"
        assert result.files[0].change_type == "modified"
        assert result.files[0].additions == 2
        assert result.files[0].deletions == 1
        assert result.total_additions == 2
        assert result.total_deletions == 1
        assert len(result.files[0].hunks) == 1

    @pytest.mark.unit
    async def test_multiple_files_mixed_types(self) -> None:
        """Multiple files: added, modified, deleted."""
        name_status = "A\tnew.py\nM\texisting.py\nD\told.py\n"
        diff_output = (
            "diff --git a/new.py b/new.py\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/new.py\n"
            "@@ -0,0 +1,2 @@\n"
            "+line1\n"
            "+line2\n"
            "diff --git a/existing.py b/existing.py\n"
            "--- a/existing.py\n"
            "+++ b/existing.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-old\n"
            "+new\n"
            "diff --git a/old.py b/old.py\n"
            "deleted file mode 100644\n"
            "--- a/old.py\n"
            "+++ /dev/null\n"
            "@@ -1,3 +0,0 @@\n"
            "-a\n"
            "-b\n"
            "-c\n"
        )
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=[name_status, diff_output])

        result = await adapter.get_diff("o", "r", "main", "feat")

        assert len(result.files) == 3
        types = {f.path: f.change_type for f in result.files}
        assert types["new.py"] == "added"
        assert types["existing.py"] == "modified"
        assert types["old.py"] == "deleted"
        assert result.total_additions == 3  # 2 in new.py + 1 in existing.py
        assert result.total_deletions == 4  # 1 in existing.py + 3 in old.py

    @pytest.mark.unit
    async def test_renamed_file(self) -> None:
        """Renamed file appears with R status."""
        name_status = "R100\told_name.py\tnew_name.py\n"
        diff_output = (
            "diff --git a/old_name.py b/new_name.py\n"
            "similarity index 100%\n"
            "rename from old_name.py\n"
            "rename to new_name.py\n"
        )
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=[name_status, diff_output])

        result = await adapter.get_diff("o", "r", "main", "feat")

        assert len(result.files) == 1
        assert result.files[0].path == "new_name.py"
        assert result.files[0].change_type == "renamed"

    @pytest.mark.unit
    async def test_binary_file(self) -> None:
        """Binary files produce no hunks."""
        name_status = "M\timage.png\n"
        diff_output = "diff --git a/image.png b/image.png\nBinary files a/image.png and b/image.png differ\n"
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=[name_status, diff_output])

        result = await adapter.get_diff("o", "r", "main", "feat")

        assert len(result.files) == 1
        assert result.files[0].path == "image.png"
        assert result.files[0].hunks == []
        assert result.files[0].additions == 0
        assert result.files[0].deletions == 0

    @pytest.mark.unit
    async def test_empty_diff(self) -> None:
        """No changes between refs."""
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=["", ""])

        result = await adapter.get_diff("o", "r", "main", "main")

        assert isinstance(result, DiffData)
        assert result.files == []
        assert result.total_additions == 0
        assert result.total_deletions == 0

    @pytest.mark.unit
    async def test_missing_ref_raises(self) -> None:
        """Missing ref should raise LocalGitRefNotFoundError."""
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=LocalGitRefNotFoundError("bad revision 'nonexistent'"))

        with pytest.raises(LocalGitRefNotFoundError):
            await adapter.get_diff("o", "r", "nonexistent", "main")

    @pytest.mark.unit
    async def test_multiple_hunks_per_file(self) -> None:
        name_status = "M\tfile.py\n"
        diff_output = (
            "diff --git a/file.py b/file.py\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-old1\n"
            "+new1\n"
            "@@ -10,2 +10,2 @@\n"
            "-old2\n"
            "+new2\n"
        )
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=[name_status, diff_output])

        result = await adapter.get_diff("o", "r", "main", "feat")

        assert len(result.files[0].hunks) == 2


# ---------------------------------------------------------------------------
# get_file_tree
# ---------------------------------------------------------------------------


class TestGetFileTree:
    @pytest.mark.unit
    async def test_flat_file_list(self) -> None:
        ls_tree_output = "100644 blob abc1234      150\tREADME.md\n100644 blob def5678       42\tmain.py\n"
        adapter = _adapter()
        adapter._run = AsyncMock(return_value=ls_tree_output)

        result = await adapter.get_file_tree("o", "r", "HEAD")

        assert isinstance(result, FileTreeNode)
        assert result.name == "."
        assert result.type == "dir"
        assert result.children is not None
        names = {c.name for c in result.children}
        assert names == {"README.md", "main.py"}

    @pytest.mark.unit
    async def test_nested_directories(self) -> None:
        ls_tree_output = "100644 blob abc1234      100\tsrc/main.py\n100644 blob def5678       50\tsrc/lib/utils.py\n"
        adapter = _adapter()
        adapter._run = AsyncMock(return_value=ls_tree_output)

        result = await adapter.get_file_tree("o", "r", "HEAD")

        assert result.children is not None
        src = [c for c in result.children if c.name == "src"][0]
        assert src.type == "dir"
        assert src.children is not None
        child_names = {c.name for c in src.children}
        assert "main.py" in child_names
        assert "lib" in child_names

    @pytest.mark.unit
    async def test_empty_tree(self) -> None:
        adapter = _adapter()
        adapter._run = AsyncMock(return_value="")

        result = await adapter.get_file_tree("o", "r", "HEAD")

        assert result.name == "."
        assert result.children == []

    @pytest.mark.unit
    async def test_file_sizes(self) -> None:
        ls_tree_output = "100644 blob abc1234      999\tbig.dat\n"
        adapter = _adapter()
        adapter._run = AsyncMock(return_value=ls_tree_output)

        result = await adapter.get_file_tree("o", "r", "HEAD")

        assert result.children is not None
        assert result.children[0].size == 999

    @pytest.mark.unit
    async def test_submodules_skipped(self) -> None:
        """Submodule entries (mode 160000 / type commit) should be skipped."""
        ls_tree_output = "100644 blob abc1234       42\tREADME.md\n160000 commit def5678        0\tvendor/lib\n"
        adapter = _adapter()
        adapter._run = AsyncMock(return_value=ls_tree_output)

        result = await adapter.get_file_tree("o", "r", "HEAD")

        assert result.children is not None
        names = {c.name for c in result.children}
        assert "README.md" in names
        assert "vendor" not in names


# ---------------------------------------------------------------------------
# get_file_content
# ---------------------------------------------------------------------------


class TestGetFileContent:
    @pytest.mark.unit
    async def test_normal_text_file(self) -> None:
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=["42", "print('hello')\nprint('world')\n"])

        result = await adapter.get_file_content("o", "r", "HEAD", "main.py")

        assert isinstance(result, FileContent)
        assert result.path == "main.py"
        assert result.content == "print('hello')\nprint('world')\n"
        assert result.size == 42
        assert result.language == "python"
        assert result.lines == 2
        assert result.truncated is False

    @pytest.mark.unit
    async def test_large_file_truncated(self) -> None:
        big_content = "x" * (200 * 1024)  # 200KB
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=[str(len(big_content)), big_content])

        result = await adapter.get_file_content("o", "r", "HEAD", "big.txt")

        assert result.truncated is True
        assert len(result.content) == 100 * 1024  # 100KB cap

    @pytest.mark.unit
    async def test_missing_file_raises(self) -> None:
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=LocalGitRefNotFoundError("path 'missing.py' does not exist in 'HEAD'"))

        with pytest.raises(LocalGitRefNotFoundError):
            await adapter.get_file_content("o", "r", "HEAD", "missing.py")

    @pytest.mark.unit
    async def test_empty_file(self) -> None:
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=["0", ""])

        result = await adapter.get_file_content("o", "r", "HEAD", "empty.py")

        assert result.content == ""
        assert result.size == 0
        assert result.lines == 0

    @pytest.mark.unit
    async def test_language_detection(self) -> None:
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=["10", "const x = 1;"])

        result = await adapter.get_file_content("o", "r", "HEAD", "app.ts")

        assert result.language == "typescript"


# ---------------------------------------------------------------------------
# get_behind_count
# ---------------------------------------------------------------------------


class TestGetBehindCount:
    @pytest.mark.unit
    async def test_normal_count(self) -> None:
        adapter = _adapter()
        adapter._run = AsyncMock(return_value="5\n")

        result = await adapter.get_behind_count("o", "r", "main", "feat")

        assert result == 5

    @pytest.mark.unit
    async def test_zero_count(self) -> None:
        adapter = _adapter()
        adapter._run = AsyncMock(return_value="0\n")

        result = await adapter.get_behind_count("o", "r", "main", "main")

        assert result == 0

    @pytest.mark.unit
    async def test_missing_ref_raises(self) -> None:
        adapter = _adapter()
        adapter._run = AsyncMock(side_effect=LocalGitRefNotFoundError("bad revision"))

        with pytest.raises(LocalGitRefNotFoundError):
            await adapter.get_behind_count("o", "r", "nonexistent", "main")
