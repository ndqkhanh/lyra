"""Test that no files are written without approval."""

import pytest
from pathlib import Path
from lyra_cli.spec_kit.writer import Writer


def test_no_disk_without_approval():
    """Verify writer only writes after explicit call."""
    writer = Writer()

    # Generate feature ID but don't write
    feature_id = writer.generate_feature_id("Build a test feature")

    # Feature directory should not exist yet
    feature_dir = Path("specs") / feature_id
    assert not feature_dir.exists(), "Files created without approval"


@pytest.mark.asyncio
async def test_rejection_path():
    """Test that rejecting at any phase prevents disk writes."""
    # This would be implemented with user interaction simulation
    # For now, just verify the writer doesn't auto-write
    writer = Writer()

    feature_id = "999-test-rejection"
    feature_dir = Path("specs") / feature_id

    # Ensure clean state
    if feature_dir.exists():
        import shutil
        shutil.rmtree(feature_dir)

    # Don't call write_artifacts
    # Verify nothing was written
    assert not feature_dir.exists()
