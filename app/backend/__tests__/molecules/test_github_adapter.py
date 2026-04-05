"""Unit tests for GitHubAdapter -- DTOs, parsing, caching, error handling.

All tests use httpx.MockTransport to avoid real HTTP calls.
"""

from __future__ import annotations

import base64

import httpx
import pytest
from pattern_stack.atoms.cache import reset_cache

from molecules.providers.github_adapter import (
    DiffData,
    DiffFile,
    DiffHunk,
    DiffLine,
    FileContent,
    FileTreeNode,
    GitHubAdapter,
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    _build_file_tree,
    _detect_language,
    _parse_patch,
    parse_owner_repo,
)

# ---------------------------------------------------------------------------
# parse_owner_repo
# ---------------------------------------------------------------------------


class TestParseOwnerRepo:
    @pytest.mark.unit
    def test_https_url(self) -> None:
        owner, repo = parse_owner_repo("https://github.com/pattern-stack/stack-bench")
        assert owner == "pattern-stack"
        assert repo == "stack-bench"

    @pytest.mark.unit
    def test_https_url_with_git_suffix(self) -> None:
        owner, repo = parse_owner_repo("https://github.com/pattern-stack/stack-bench.git")
        assert owner == "pattern-stack"
        assert repo == "stack-bench"

    @pytest.mark.unit
    def test_https_url_with_trailing_slash(self) -> None:
        owner, repo = parse_owner_repo("https://github.com/pattern-stack/stack-bench/")
        assert owner == "pattern-stack"
        assert repo == "stack-bench"

    @pytest.mark.unit
    def test_ssh_url(self) -> None:
        owner, repo = parse_owner_repo("git@github.com:pattern-stack/stack-bench.git")
        assert owner == "pattern-stack"
        assert repo == "stack-bench"

    @pytest.mark.unit
    def test_ssh_url_without_git_suffix(self) -> None:
        owner, repo = parse_owner_repo("git@github.com:myorg/myrepo")
        assert owner == "myorg"
        assert repo == "myrepo"

    @pytest.mark.unit
    def test_invalid_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_owner_repo("notaurl")


# ---------------------------------------------------------------------------
# _detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    @pytest.mark.unit
    def test_python(self) -> None:
        assert _detect_language("app/main.py") == "python"

    @pytest.mark.unit
    def test_typescript(self) -> None:
        assert _detect_language("src/App.tsx") == "typescript"

    @pytest.mark.unit
    def test_dockerfile(self) -> None:
        assert _detect_language("Dockerfile") == "dockerfile"

    @pytest.mark.unit
    def test_makefile(self) -> None:
        assert _detect_language("Makefile") == "makefile"

    @pytest.mark.unit
    def test_justfile(self) -> None:
        assert _detect_language("Justfile") == "makefile"

    @pytest.mark.unit
    def test_unknown_extension(self) -> None:
        assert _detect_language("file.xyz") is None


# ---------------------------------------------------------------------------
# _parse_patch
# ---------------------------------------------------------------------------


class TestParsePatch:
    @pytest.mark.unit
    def test_simple_addition(self) -> None:
        patch = "@@ -1,3 +1,4 @@\n foo\n bar\n+baz\n qux"
        hunks = _parse_patch(patch)
        assert len(hunks) == 1
        assert hunks[0].header == "@@ -1,3 +1,4 @@"
        # Lines: hunk header, context foo, context bar, add baz, context qux
        lines = hunks[0].lines
        assert lines[0].type == "hunk"
        assert lines[1].type == "context"
        assert lines[1].content == "foo"
        assert lines[2].type == "context"
        assert lines[3].type == "add"
        assert lines[3].content == "baz"
        assert lines[3].new_num == 3
        assert lines[3].old_num is None
        assert lines[4].type == "context"

    @pytest.mark.unit
    def test_simple_deletion(self) -> None:
        patch = "@@ -1,3 +1,2 @@\n foo\n-bar\n baz"
        hunks = _parse_patch(patch)
        lines = hunks[0].lines
        del_line = [ln for ln in lines if ln.type == "del"][0]
        assert del_line.content == "bar"
        assert del_line.old_num is not None
        assert del_line.new_num is None

    @pytest.mark.unit
    def test_multiple_hunks(self) -> None:
        patch = "@@ -1,2 +1,2 @@\n-old\n+new\n@@ -10,2 +10,2 @@\n-old2\n+new2"
        hunks = _parse_patch(patch)
        assert len(hunks) == 2

    @pytest.mark.unit
    def test_empty_patch(self) -> None:
        hunks = _parse_patch("")
        assert hunks == []

    @pytest.mark.unit
    def test_hunk_header_with_context_text(self) -> None:
        patch = "@@ -5,3 +5,4 @@ def my_function():\n foo\n+bar"
        hunks = _parse_patch(patch)
        assert "def my_function()" in hunks[0].header

    @pytest.mark.unit
    def test_line_numbers_track_correctly(self) -> None:
        patch = "@@ -10,4 +10,5 @@\n ctx\n+add1\n+add2\n ctx2\n-del1"
        hunks = _parse_patch(patch)
        lines = hunks[0].lines
        # hunk header: old=10, new=10
        ctx1 = lines[1]
        assert ctx1.old_num == 10
        assert ctx1.new_num == 10
        add1 = lines[2]
        assert add1.old_num is None
        assert add1.new_num == 11
        add2 = lines[3]
        assert add2.new_num == 12
        ctx2 = lines[4]
        assert ctx2.old_num == 11
        assert ctx2.new_num == 13
        del1 = lines[5]
        assert del1.old_num == 12
        assert del1.new_num is None


# ---------------------------------------------------------------------------
# _build_file_tree
# ---------------------------------------------------------------------------


class TestBuildFileTree:
    @pytest.mark.unit
    def test_flat_files(self) -> None:
        entries = [
            {"path": "README.md", "type": "blob", "size": 100},
            {"path": "main.py", "type": "blob", "size": 200},
        ]
        root = _build_file_tree(entries)
        assert root.name == "."
        assert root.type == "dir"
        assert root.children is not None
        assert len(root.children) == 2
        names = {c.name for c in root.children}
        assert names == {"README.md", "main.py"}

    @pytest.mark.unit
    def test_nested_directories(self) -> None:
        entries = [
            {"path": "src", "type": "tree"},
            {"path": "src/main.py", "type": "blob", "size": 100},
            {"path": "src/lib", "type": "tree"},
            {"path": "src/lib/utils.py", "type": "blob", "size": 50},
        ]
        root = _build_file_tree(entries)
        assert root.children is not None
        src = [c for c in root.children if c.name == "src"][0]
        assert src.type == "dir"
        assert src.children is not None
        assert len(src.children) == 2  # main.py + lib/
        lib = [c for c in src.children if c.name == "lib"][0]
        assert lib.type == "dir"
        assert lib.children is not None
        assert lib.children[0].name == "utils.py"

    @pytest.mark.unit
    def test_implicit_parent_dirs(self) -> None:
        """When GitHub omits directory entries, parents should be auto-created."""
        entries = [
            {"path": "a/b/c.txt", "type": "blob", "size": 10},
        ]
        root = _build_file_tree(entries)
        assert root.children is not None
        a = root.children[0]
        assert a.name == "a"
        assert a.type == "dir"
        assert a.children is not None
        b = a.children[0]
        assert b.name == "b"
        assert b.children is not None
        c = b.children[0]
        assert c.name == "c.txt"
        assert c.type == "file"

    @pytest.mark.unit
    def test_empty_entries(self) -> None:
        root = _build_file_tree([])
        assert root.name == "."
        assert root.children == []

    @pytest.mark.unit
    def test_file_has_size(self) -> None:
        entries = [{"path": "big.dat", "type": "blob", "size": 999}]
        root = _build_file_tree(entries)
        assert root.children is not None
        assert root.children[0].size == 999

    @pytest.mark.unit
    def test_dir_has_no_size(self) -> None:
        entries = [{"path": "src", "type": "tree"}]
        root = _build_file_tree(entries)
        assert root.children is not None
        assert root.children[0].size is None


# ---------------------------------------------------------------------------
# GitHubAdapter (using httpx.MockTransport)
# ---------------------------------------------------------------------------


def _make_response(data: dict | list, status_code: int = 200, headers: dict[str, str] | None = None) -> httpx.Response:
    """Build an httpx.Response from JSON data."""
    return httpx.Response(
        status_code=status_code,
        json=data,
        headers=headers or {},
    )


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Reset cache singleton between tests to avoid cross-test pollution."""
    reset_cache()


def _make_adapter(handler: httpx.MockTransport | None = None) -> GitHubAdapter:
    """Create a GitHubAdapter with a mock transport."""
    adapter = GitHubAdapter(token="test-token")
    if handler is not None:
        adapter._client = httpx.AsyncClient(transport=handler, base_url=GitHubAdapter.BASE_URL)
    return adapter


class TestGitHubAdapterGetDiff:
    @pytest.mark.unit
    async def test_parses_compare_response(self) -> None:
        compare_response = {
            "files": [
                {
                    "filename": "src/main.py",
                    "status": "modified",
                    "additions": 5,
                    "deletions": 2,
                    "patch": "@@ -1,3 +1,4 @@\n foo\n-old\n+new\n+extra",
                },
                {
                    "filename": "README.md",
                    "status": "added",
                    "additions": 10,
                    "deletions": 0,
                    "patch": "@@ -0,0 +1,10 @@\n+# Hello",
                },
            ]
        }

        async def handler(request: httpx.Request) -> httpx.Response:
            assert "/repos/org/repo/compare/main...feat" in str(request.url)
            return _make_response(compare_response)

        adapter = _make_adapter(httpx.MockTransport(handler))
        result = await adapter.get_diff("org", "repo", "main", "feat")

        assert isinstance(result, DiffData)
        assert len(result.files) == 2
        assert result.total_additions == 15
        assert result.total_deletions == 2
        assert result.files[0].path == "src/main.py"
        assert result.files[0].change_type == "modified"
        assert len(result.files[0].hunks) == 1
        assert result.files[1].change_type == "added"

    @pytest.mark.unit
    async def test_maps_removed_to_deleted(self) -> None:
        compare_response = {
            "files": [
                {
                    "filename": "old.py",
                    "status": "removed",
                    "additions": 0,
                    "deletions": 5,
                    "patch": "@@ -1,5 +0,0 @@\n-a\n-b\n-c\n-d\n-e",
                }
            ]
        }

        async def handler(request: httpx.Request) -> httpx.Response:
            return _make_response(compare_response)

        adapter = _make_adapter(httpx.MockTransport(handler))
        result = await adapter.get_diff("o", "r", "main", "feat")
        assert result.files[0].change_type == "deleted"

    @pytest.mark.unit
    async def test_binary_file_no_patch(self) -> None:
        """Binary files have no patch -- should produce empty hunks list."""
        compare_response = {
            "files": [
                {
                    "filename": "image.png",
                    "status": "added",
                    "additions": 0,
                    "deletions": 0,
                }
            ]
        }

        async def handler(request: httpx.Request) -> httpx.Response:
            return _make_response(compare_response)

        adapter = _make_adapter(httpx.MockTransport(handler))
        result = await adapter.get_diff("o", "r", "main", "feat")
        assert result.files[0].hunks == []

    @pytest.mark.unit
    async def test_diff_is_cached(self) -> None:
        call_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return _make_response({"files": []})

        adapter = _make_adapter(httpx.MockTransport(handler))
        await adapter.get_diff("o", "r", "main", "feat")
        await adapter.get_diff("o", "r", "main", "feat")
        assert call_count == 1  # Second call should hit cache


class TestGitHubAdapterGetFileTree:
    @pytest.mark.unit
    async def test_parses_tree_response(self) -> None:
        tree_response = {
            "sha": "abc123",
            "tree": [
                {"path": "src", "type": "tree", "mode": "040000"},
                {"path": "src/main.py", "type": "blob", "size": 100, "mode": "100644"},
                {"path": "README.md", "type": "blob", "size": 50, "mode": "100644"},
            ],
        }

        async def handler(request: httpx.Request) -> httpx.Response:
            assert "recursive=1" in str(request.url)
            return _make_response(tree_response)

        adapter = _make_adapter(httpx.MockTransport(handler))
        result = await adapter.get_file_tree("o", "r", "abc123")

        assert isinstance(result, FileTreeNode)
        assert result.name == "."
        assert result.type == "dir"
        assert result.children is not None
        names = {c.name for c in result.children}
        assert "src" in names
        assert "README.md" in names

    @pytest.mark.unit
    async def test_tree_is_cached(self) -> None:
        call_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return _make_response({"tree": []})

        adapter = _make_adapter(httpx.MockTransport(handler))
        await adapter.get_file_tree("o", "r", "sha1")
        await adapter.get_file_tree("o", "r", "sha1")
        assert call_count == 1


class TestGitHubAdapterGetFileContent:
    @pytest.mark.unit
    async def test_decodes_base64_content(self) -> None:
        text = "Hello, world!\nLine 2\n"
        encoded = base64.b64encode(text.encode()).decode()
        content_response = {
            "content": encoded,
            "encoding": "base64",
            "size": len(text),
            "name": "hello.py",
            "path": "src/hello.py",
        }

        async def handler(request: httpx.Request) -> httpx.Response:
            return _make_response(content_response)

        adapter = _make_adapter(httpx.MockTransport(handler))
        result = await adapter.get_file_content("o", "r", "sha", "src/hello.py")

        assert isinstance(result, FileContent)
        assert result.path == "src/hello.py"
        assert result.content == text
        assert result.language == "python"
        assert result.lines == 2
        assert result.truncated is False

    @pytest.mark.unit
    async def test_truncates_large_content(self) -> None:
        big_text = "x" * (200 * 1024)  # 200KB
        encoded = base64.b64encode(big_text.encode()).decode()
        content_response = {
            "content": encoded,
            "encoding": "base64",
            "size": len(big_text),
        }

        async def handler(request: httpx.Request) -> httpx.Response:
            return _make_response(content_response)

        adapter = _make_adapter(httpx.MockTransport(handler))
        result = await adapter.get_file_content("o", "r", "sha", "big.txt")

        assert result.truncated is True
        assert len(result.content) == 100 * 1024  # 100KB cap

    @pytest.mark.unit
    async def test_content_is_cached(self) -> None:
        call_count = 0
        text = "hello"
        encoded = base64.b64encode(text.encode()).decode()

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return _make_response({"content": encoded, "encoding": "base64", "size": 5})

        adapter = _make_adapter(httpx.MockTransport(handler))
        await adapter.get_file_content("o", "r", "sha", "f.py")
        await adapter.get_file_content("o", "r", "sha", "f.py")
        assert call_count == 1


class TestGitHubAdapterErrorHandling:
    @pytest.mark.unit
    async def test_404_raises_not_found(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=404, json={"message": "Not Found"})

        adapter = _make_adapter(httpx.MockTransport(handler))
        with pytest.raises(GitHubNotFoundError):
            await adapter.get_diff("o", "r", "main", "missing")

    @pytest.mark.unit
    async def test_403_rate_limit_raises(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=403,
                json={"message": "rate limit"},
                headers={"x-ratelimit-remaining": "0"},
            )

        adapter = _make_adapter(httpx.MockTransport(handler))
        with pytest.raises(GitHubRateLimitError):
            await adapter.get_file_tree("o", "r", "sha")

    @pytest.mark.unit
    async def test_403_non_rate_limit(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=403, json={"message": "Forbidden"})

        adapter = _make_adapter(httpx.MockTransport(handler))
        with pytest.raises(GitHubAPIError) as exc_info:
            await adapter.get_file_tree("o", "r", "sha")
        assert exc_info.value.status_code == 403

    @pytest.mark.unit
    async def test_500_raises_generic_error(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=500, json={"message": "Server Error"})

        adapter = _make_adapter(httpx.MockTransport(handler))
        with pytest.raises(GitHubAPIError) as exc_info:
            await adapter.get_file_content("o", "r", "sha", "f.py")
        assert exc_info.value.status_code == 500


class TestGitHubAdapterAuth:
    @pytest.mark.unit
    async def test_token_included_in_headers(self) -> None:
        captured_headers: dict[str, str] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(request.headers))
            return _make_response({"files": []})

        # Create a fresh adapter with token and mock transport together.
        adapter2 = GitHubAdapter(token="my-secret-token")
        adapter2._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=GitHubAdapter.BASE_URL,
            headers={"Authorization": "Bearer my-secret-token", "Accept": "application/vnd.github.v3+json"},
        )
        await adapter2.get_diff("o", "r", "main", "feat")
        assert captured_headers.get("authorization") == "Bearer my-secret-token"

    @pytest.mark.unit
    def test_no_token_no_auth_header(self) -> None:
        adapter = GitHubAdapter(token="")
        headers = dict(adapter._client.headers)
        assert "authorization" not in {k.lower() for k in headers}


# ---------------------------------------------------------------------------
# DTO serialization round-trip
# ---------------------------------------------------------------------------


class TestDTOSerialization:
    @pytest.mark.unit
    def test_diff_data_round_trip(self) -> None:
        data = DiffData(
            files=[
                DiffFile(
                    path="a.py",
                    change_type="added",
                    additions=3,
                    deletions=0,
                    hunks=[
                        DiffHunk(
                            header="@@ -0,0 +1,3 @@",
                            lines=[DiffLine(type="add", old_num=None, new_num=1, content="hello")],
                        )
                    ],
                )
            ],
            total_additions=3,
            total_deletions=0,
        )
        json_str = data.model_dump_json()
        restored = DiffData.model_validate_json(json_str)
        assert restored == data

    @pytest.mark.unit
    def test_file_tree_node_recursive(self) -> None:
        node = FileTreeNode(
            name="src",
            path="src",
            type="dir",
            children=[
                FileTreeNode(name="main.py", path="src/main.py", type="file", size=100),
            ],
        )
        json_str = node.model_dump_json()
        restored = FileTreeNode.model_validate_json(json_str)
        assert restored.children is not None
        assert restored.children[0].name == "main.py"

    @pytest.mark.unit
    def test_file_content_serialization(self) -> None:
        fc = FileContent(
            path="a.py",
            content="print('hi')",
            size=11,
            language="python",
            lines=1,
            truncated=False,
        )
        d = fc.model_dump()
        assert d["language"] == "python"
        assert d["truncated"] is False


# ---------------------------------------------------------------------------
# Write operations: create_pull_request, update_pull_request, mark_pr_ready
# ---------------------------------------------------------------------------


class TestGitHubAdapterCreatePullRequest:
    @pytest.mark.unit
    async def test_sends_correct_payload(self) -> None:
        """Verify POST to /repos/{owner}/{repo}/pulls with draft=True."""
        captured_body: dict[str, object] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            import json as _json

            captured_body.update(_json.loads(request.content))
            return _make_response({"number": 42, "html_url": "https://github.com/o/r/pull/42", "state": "open"})

        adapter = _make_adapter(httpx.MockTransport(handler))
        result = await adapter.create_pull_request("o", "r", title="My PR", head="feature", base="main", draft=True)

        assert captured_body["title"] == "My PR"
        assert captured_body["head"] == "feature"
        assert captured_body["base"] == "main"
        assert captured_body["draft"] is True
        assert result["number"] == 42
        assert result["html_url"] == "https://github.com/o/r/pull/42"

    @pytest.mark.unit
    async def test_includes_body_when_provided(self) -> None:
        captured_body: dict[str, object] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            import json as _json

            captured_body.update(_json.loads(request.content))
            return _make_response({"number": 1, "html_url": "url", "state": "open"})

        adapter = _make_adapter(httpx.MockTransport(handler))
        await adapter.create_pull_request("o", "r", title="T", head="h", base="b", body="Description here")

        assert captured_body["body"] == "Description here"

    @pytest.mark.unit
    async def test_omits_body_when_none(self) -> None:
        captured_body: dict[str, object] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            import json as _json

            captured_body.update(_json.loads(request.content))
            return _make_response({"number": 1, "html_url": "url", "state": "open"})

        adapter = _make_adapter(httpx.MockTransport(handler))
        await adapter.create_pull_request("o", "r", title="T", head="h", base="b")

        assert "body" not in captured_body

    @pytest.mark.unit
    async def test_raises_on_error(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=422, json={"message": "Validation Failed"})

        adapter = _make_adapter(httpx.MockTransport(handler))
        with pytest.raises(GitHubAPIError):
            await adapter.create_pull_request("o", "r", title="T", head="h", base="b")


class TestGitHubAdapterUpdatePullRequest:
    @pytest.mark.unit
    async def test_sends_patch_with_base(self) -> None:
        captured: dict[str, object] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            import json as _json

            captured["method"] = request.method
            captured["body"] = _json.loads(request.content)
            return _make_response({"number": 10, "html_url": "url"})

        adapter = _make_adapter(httpx.MockTransport(handler))
        result = await adapter.update_pull_request("o", "r", 10, base="new-base")

        assert captured["method"] == "PATCH"
        assert captured["body"]["base"] == "new-base"
        assert result["number"] == 10

    @pytest.mark.unit
    async def test_sends_title_and_body(self) -> None:
        captured_body: dict[str, object] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            import json as _json

            captured_body.update(_json.loads(request.content))
            return _make_response({"number": 10, "html_url": "url"})

        adapter = _make_adapter(httpx.MockTransport(handler))
        await adapter.update_pull_request("o", "r", 10, title="New Title", body="New Body")

        assert captured_body["title"] == "New Title"
        assert captured_body["body"] == "New Body"


class TestGitHubAdapterMarkPrReady:
    @pytest.mark.unit
    async def test_uses_graphql_mutation(self) -> None:
        """Verify mark_pr_ready uses GraphQL, not REST PATCH with draft=false."""
        requests_made: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests_made.append(request)
            url_path = str(request.url.path) if hasattr(request.url, "path") else str(request.url)

            # REST GET for node_id
            if request.method == "GET" and "/pulls/" in url_path:
                return _make_response({"node_id": "PR_node123", "number": 42})

            # GraphQL mutation
            if "graphql" in str(request.url):
                return _make_response(
                    {"data": {"markPullRequestReadyForReview": {"pullRequest": {"id": "PR_node123"}}}}
                )

            return httpx.Response(status_code=404, json={})

        adapter = _make_adapter(httpx.MockTransport(handler))
        await adapter.mark_pr_ready("o", "r", 42)

        # Should have made exactly 2 requests: GET (node_id) + POST (GraphQL)
        assert len(requests_made) == 2
        assert requests_made[0].method == "GET"
        assert requests_made[1].method == "POST"
        assert "graphql" in str(requests_made[1].url)

    @pytest.mark.unit
    async def test_raises_on_graphql_error(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return _make_response({"node_id": "PR_node123"})
            # GraphQL error response
            return _make_response({"errors": [{"message": "Insufficient permissions"}]})

        adapter = _make_adapter(httpx.MockTransport(handler))
        with pytest.raises(GitHubAPIError, match="GraphQL"):
            await adapter.mark_pr_ready("o", "r", 42)
