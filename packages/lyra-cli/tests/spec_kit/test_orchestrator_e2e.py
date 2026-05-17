"""End-to-end orchestrator tests."""

import pytest
from pathlib import Path
from lyra_cli.spec_kit.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_e2e_happy_path():
    """Test full flow from detection to file creation."""
    orchestrator = Orchestrator()

    prompt = "Build me a deep-research orchestrator that runs 5 sub-agents in parallel"
    result = await orchestrator.maybe_intercept(prompt)

    # Should intercept
    assert result.intercepted
    assert result.feature_id is not None
    assert result.error is None

    # Check files created
    feature_dir = Path("specs") / result.feature_id
    assert feature_dir.exists()

    spec_file = feature_dir / "spec.md"
    plan_file = feature_dir / "plan.md"
    tasks_file = feature_dir / "tasks.md"

    assert spec_file.exists()
    assert plan_file.exists()
    assert tasks_file.exists()

    # Cleanup
    import shutil
    shutil.rmtree(feature_dir)


@pytest.mark.asyncio
async def test_e2e_not_spec_worthy():
    """Test that simple prompts pass through."""
    orchestrator = Orchestrator()

    prompt = "Fix the typo in README"
    result = await orchestrator.maybe_intercept(prompt)

    # Should not intercept
    assert not result.intercepted
    assert result.feature_id is None
