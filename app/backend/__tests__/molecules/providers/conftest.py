import pytest

from molecules.providers.mock_adapter import MockAdapter


@pytest.fixture
def mock_adapter():
    adapter = MockAdapter()
    yield adapter
    adapter.reset()
