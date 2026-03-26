"""Tests for event handler setup, teardown, and subsystem configuration."""

from unittest.mock import MagicMock, patch

import pytest

from molecules.events.setup import (
    ALL_TOPICS,
    SubsystemRefs,
    configure_subsystems,
    setup_event_handlers,
    teardown_event_handlers,
    teardown_subsystems,
)


# ---------------------------------------------------------------------------
# setup_event_handlers / teardown_event_handlers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_setup_registers_all_topics() -> None:
    """setup_event_handlers subscribes the broadcast bridge to every topic plus reactive handlers."""
    mock_bus = MagicMock()

    with patch("molecules.events.setup.get_event_bus", return_value=mock_bus):
        setup_event_handlers()

        # One subscribe call per topic (broadcast bridge) + 1 reactive handler
        assert mock_bus.subscribe.call_count == len(ALL_TOPICS) + 1
        registered_topics = {c[0][0] for c in mock_bus.subscribe.call_args_list}
        assert set(ALL_TOPICS).issubset(registered_topics)


@pytest.mark.unit
def test_setup_registers_cascade_handler() -> None:
    """setup_event_handlers subscribes the cascade handler to PULL_REQUEST_MERGED."""
    mock_bus = MagicMock()

    with patch("molecules.events.setup.get_event_bus", return_value=mock_bus):
        setup_event_handlers()

        from molecules.events.handlers.cascade_handler import on_pull_request_merged
        from molecules.events.topics import PULL_REQUEST_MERGED

        # Find the cascade handler subscription
        cascade_calls = [
            c
            for c in mock_bus.subscribe.call_args_list
            if c[0] == (PULL_REQUEST_MERGED, on_pull_request_merged)
        ]
        assert len(cascade_calls) == 1


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


# ---------------------------------------------------------------------------
# configure_subsystems
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_configure_subsystems_initializes_all() -> None:
    """configure_subsystems initializes event bus, event store, broadcast, and jobs."""
    mock_bus = MagicMock()
    mock_store = MagicMock()
    mock_broadcast = MagicMock()
    mock_queue = MagicMock()

    with (
        patch("molecules.events.setup.get_event_bus", return_value=mock_bus),
        patch("molecules.events.setup.get_event_store", return_value=mock_store),
        patch("molecules.events.setup.get_broadcast", return_value=mock_broadcast),
        patch("molecules.events.setup.configure_jobs") as mock_configure_jobs,
        patch("molecules.events.setup.get_job_queue", return_value=mock_queue),
    ):
        from config.settings import AppSettings

        settings = AppSettings(
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            JOB_BACKEND="memory",
            JOB_MAX_CONCURRENT=3,
            JOB_POLL_INTERVAL=2.0,
        )

        refs = configure_subsystems(settings)

        # All subsystem references populated
        assert refs.event_bus is mock_bus
        assert refs.event_store is mock_store
        assert refs.broadcast is mock_broadcast
        assert refs.job_queue is mock_queue

        # Jobs configured with correct settings
        mock_configure_jobs.assert_called_once()
        call_args = mock_configure_jobs.call_args
        job_config = call_args[0][0]
        assert job_config.backend == "memory"
        assert job_config.max_concurrent == 3
        assert job_config.poll_interval == 2.0


@pytest.mark.unit
def test_configure_subsystems_passes_session_factory() -> None:
    """configure_subsystems forwards session_factory to configure_jobs."""
    mock_session_factory = MagicMock()

    with (
        patch("molecules.events.setup.get_event_bus"),
        patch("molecules.events.setup.get_event_store"),
        patch("molecules.events.setup.get_broadcast"),
        patch("molecules.events.setup.configure_jobs") as mock_configure_jobs,
        patch("molecules.events.setup.get_job_queue"),
    ):
        from config.settings import AppSettings

        settings = AppSettings(
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            JOB_BACKEND="database",
        )

        configure_subsystems(settings, session_factory=mock_session_factory)

        mock_configure_jobs.assert_called_once()
        call_kwargs = mock_configure_jobs.call_args[1]
        assert call_kwargs["session_factory"] is mock_session_factory


@pytest.mark.unit
def test_configure_subsystems_returns_subsystem_refs() -> None:
    """configure_subsystems returns a SubsystemRefs dataclass."""
    with (
        patch("molecules.events.setup.get_event_bus"),
        patch("molecules.events.setup.get_event_store"),
        patch("molecules.events.setup.get_broadcast"),
        patch("molecules.events.setup.configure_jobs"),
        patch("molecules.events.setup.get_job_queue"),
    ):
        from config.settings import AppSettings

        settings = AppSettings(
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        )

        refs = configure_subsystems(settings)
        assert isinstance(refs, SubsystemRefs)


# ---------------------------------------------------------------------------
# teardown_subsystems
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_teardown_subsystems_resets_all() -> None:
    """teardown_subsystems calls reset on jobs, broadcast, and event store."""
    with (
        patch("molecules.events.setup.reset_jobs") as mock_reset_jobs,
        patch("molecules.events.setup.reset_broadcast") as mock_reset_broadcast,
        patch("molecules.events.setup.reset_event_store") as mock_reset_event_store,
    ):
        teardown_subsystems()

        mock_reset_jobs.assert_called_once()
        mock_reset_broadcast.assert_called_once()
        mock_reset_event_store.assert_called_once()
