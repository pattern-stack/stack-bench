"""Tests for event handler setup and teardown."""

from unittest.mock import MagicMock, patch

import pytest

from molecules.events.setup import ALL_TOPICS, setup_event_handlers, teardown_event_handlers


@pytest.mark.unit
def test_setup_registers_all_topics() -> None:
    """setup_event_handlers subscribes the broadcast bridge to every topic."""
    mock_bus = MagicMock()

    with patch("molecules.events.setup.get_event_bus", return_value=mock_bus):
        setup_event_handlers()

        # One subscribe call per topic
        assert mock_bus.subscribe.call_count == len(ALL_TOPICS)
        registered_topics = {c[0][0] for c in mock_bus.subscribe.call_args_list}
        assert registered_topics == set(ALL_TOPICS)


@pytest.mark.unit
def test_teardown_clears_bus() -> None:
    """teardown_event_handlers clears all handlers."""
    mock_bus = MagicMock()

    with patch("molecules.events.setup.get_event_bus", return_value=mock_bus):
        teardown_event_handlers()
        mock_bus.clear.assert_called_once()


@pytest.mark.unit
def test_all_topics_is_comprehensive() -> None:
    """ALL_TOPICS covers every topic constant defined in the topics module."""
    from molecules.events import topics

    # Collect all module-level string constants that look like topics
    defined_topics = {v for k, v in vars(topics).items() if k.isupper() and isinstance(v, str) and "." in v}
    assert set(ALL_TOPICS) == defined_topics
