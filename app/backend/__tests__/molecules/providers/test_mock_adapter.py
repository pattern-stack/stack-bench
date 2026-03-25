"""MockAdapter conformance tests."""

import pytest

from molecules.providers.mock_adapter import MockAdapter

from .conformance import AdapterConformanceTests


class TestMockAdapter(AdapterConformanceTests):
    @pytest.fixture(autouse=True)
    def adapter(self):
        adapter = MockAdapter()
        yield adapter
        adapter.reset()
