from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from molecules.providers.stack_cli_adapter import StackCLIAdapter
from molecules.providers.stack_provider import StackResult


@pytest.mark.unit
def test_stack_cli_adapter_init_with_path() -> None:
    """Verify binary_path is set when provided."""
    adapter = StackCLIAdapter(binary_path="/usr/bin/stack")
    assert adapter.binary_path == "/usr/bin/stack"


@pytest.mark.unit
def test_stack_cli_adapter_find_binary_not_found() -> None:
    """Verify FileNotFoundError when binary not found."""
    with (
        patch("shutil.which", return_value=None),
        patch("os.path.isfile", return_value=False),
        pytest.raises(FileNotFoundError),
    ):
        StackCLIAdapter()


@pytest.mark.unit
def test_stack_cli_adapter_has_provider_methods() -> None:
    """Verify adapter has all StackProvider methods."""
    assert hasattr(StackCLIAdapter, "create_stack")
    assert hasattr(StackCLIAdapter, "get_status")
    assert hasattr(StackCLIAdapter, "push")
    assert hasattr(StackCLIAdapter, "submit")
    assert hasattr(StackCLIAdapter, "restack")
    assert hasattr(StackCLIAdapter, "sync")


@pytest.mark.unit
async def test_stack_cli_adapter_run() -> None:
    """Verify _run passes binary path and args correctly."""
    adapter = StackCLIAdapter(binary_path="/usr/bin/stack")

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_proc
        stdout, stderr, code = await adapter._run("status")

    mock_exec.assert_called_once()
    call_args = mock_exec.call_args[0]
    assert call_args[0] == "/usr/bin/stack"
    assert call_args[1] == "status"


@pytest.mark.unit
async def test_stack_cli_adapter_create_stack() -> None:
    """Verify create_stack returns success StackResult."""
    adapter = StackCLIAdapter(binary_path="/usr/bin/stack")
    adapter._run = AsyncMock(return_value=("Created stack", "", 0))

    result = await adapter.create_stack("my-stack")
    assert isinstance(result, StackResult)
    assert result.success is True
    assert result.output == "Created stack"
    assert result.error is None


@pytest.mark.unit
async def test_stack_cli_adapter_create_stack_failure() -> None:
    """Verify create_stack returns failure StackResult."""
    adapter = StackCLIAdapter(binary_path="/usr/bin/stack")
    adapter._run = AsyncMock(return_value=("", "error msg", 1))

    result = await adapter.create_stack("my-stack")
    assert isinstance(result, StackResult)
    assert result.success is False
    assert result.error == "error msg"
