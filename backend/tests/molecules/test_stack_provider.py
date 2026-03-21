import pytest

from molecules.providers.stack_provider import (
    BranchInfo,
    StackInfo,
    StackProvider,
    StackResult,
)


@pytest.mark.unit
def test_stack_result_dataclass() -> None:
    """Verify StackResult fields and defaults."""
    result = StackResult(success=True, output="ok")
    assert result.success is True
    assert result.output == "ok"
    assert result.error is None


@pytest.mark.unit
def test_stack_result_with_error() -> None:
    """Verify StackResult with error."""
    result = StackResult(success=False, output="", error="failed")
    assert result.success is False
    assert result.error == "failed"


@pytest.mark.unit
def test_branch_info_dataclass() -> None:
    """Verify BranchInfo fields and defaults."""
    info = BranchInfo(name="user/stack/1-feat", position=1)
    assert info.name == "user/stack/1-feat"
    assert info.position == 1
    assert info.head_sha is None
    assert info.pr_number is None


@pytest.mark.unit
def test_branch_info_full() -> None:
    """Verify BranchInfo with all fields."""
    info = BranchInfo(
        name="user/stack/1-feat",
        position=1,
        head_sha="a" * 40,
        pr_number=42,
        pr_url="https://github.com/org/repo/pull/42",
    )
    assert info.head_sha == "a" * 40
    assert info.pr_number == 42
    assert info.pr_url == "https://github.com/org/repo/pull/42"


@pytest.mark.unit
def test_stack_info_dataclass() -> None:
    """Verify StackInfo fields."""
    info = StackInfo(name="my-stack", trunk="main", branches=[])
    assert info.name == "my-stack"
    assert info.trunk == "main"
    assert info.branches == []


@pytest.mark.unit
def test_stack_provider_is_protocol() -> None:
    """Verify StackProvider has expected methods."""
    assert hasattr(StackProvider, "create_stack")
    assert hasattr(StackProvider, "get_status")
    assert hasattr(StackProvider, "push")
    assert hasattr(StackProvider, "submit")
    assert hasattr(StackProvider, "restack")
    assert hasattr(StackProvider, "sync")
