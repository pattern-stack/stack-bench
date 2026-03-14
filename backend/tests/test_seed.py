import pytest


@pytest.mark.unit
def test_seed_module_importable() -> None:
    """Verify seed module can be imported."""
    from seeds.agents import seed_agents

    assert callable(seed_agents)


@pytest.mark.unit
def test_run_seed_module_importable() -> None:
    """Verify seed CLI entry point can be imported."""
    from seeds.run_seed import main

    assert callable(main)
