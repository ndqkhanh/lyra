"""
Tests for Evolution Harness

Tests the AEVO-inspired harness with OS-level capability boundaries.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from lyra_evolution.harness import EvaluationResult, EvolutionHarness


@pytest.fixture
def temp_harness():
    """Create temporary harness for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    workspace = temp_dir / "workspace"
    archive = temp_dir / "archive"

    harness = EvolutionHarness(workspace_dir=workspace, archive_dir=archive)

    yield harness

    # Cleanup
    shutil.rmtree(temp_dir)


def test_harness_initialization(temp_harness):
    """Test harness initializes correctly."""
    assert temp_harness.workspace_dir.exists()
    assert temp_harness.archive_dir.exists()
    assert (temp_harness.archive_dir / "candidates").exists()
    assert (temp_harness.archive_dir / "scores").exists()
    assert (temp_harness.archive_dir / "meta_edits").exists()


def test_add_candidate(temp_harness):
    """Test adding candidate to archive."""
    candidate_id = temp_harness.add_candidate(
        config={"skills": ["skill1"]},
        generation=0,
        metadata={"test": True}
    )

    assert candidate_id.startswith("c000_")

    # Verify candidate file exists
    candidate_file = temp_harness.archive_dir / "candidates" / f"{candidate_id}.json"
    assert candidate_file.exists()


def test_evaluate_candidate(temp_harness):
    """Test evaluating candidate."""
    # Add candidate
    candidate_id = temp_harness.add_candidate(
        config={"skills": ["skill1", "skill2"]},
        generation=0
    )

    # Evaluate
    result = temp_harness.evaluate(candidate_id)

    assert isinstance(result, EvaluationResult)
    assert result.candidate_id == candidate_id
    assert 0.0 <= result.score <= 1.0
    assert result.evaluator_version == "1.0.0"


def test_submit_candidate(temp_harness):
    """Test submitting candidate."""
    # Add and submit candidate
    candidate_id = temp_harness.add_candidate(
        config={"skills": ["skill1"]},
        generation=0
    )

    success = temp_harness.submit(candidate_id)
    assert success

    # Verify submission file exists
    submission_file = temp_harness.archive_dir / "scores" / "official_submissions.jsonl"
    assert submission_file.exists()


def test_workspace_read_write(temp_harness):
    """Test workspace read/write operations."""
    # Write to workspace
    content = "Test content"
    temp_harness.workspace_write("test.txt", content)

    # Read from workspace
    read_content = temp_harness.workspace_read("test.txt")
    assert read_content == content


def test_workspace_path_confinement(temp_harness):
    """Test workspace path confinement (security)."""
    # Attempt to write outside workspace
    with pytest.raises(PermissionError):
        temp_harness.workspace_write("../outside.txt", "malicious")

    # Attempt to read outside workspace
    with pytest.raises(PermissionError):
        temp_harness.workspace_read("../outside.txt")


def test_audit_trail(temp_harness):
    """Test audit trail logging."""
    # Perform operations
    candidate_id = temp_harness.add_candidate(
        config={"skills": ["skill1"]},
        generation=0
    )
    temp_harness.evaluate(candidate_id)
    temp_harness.workspace_write("test.txt", "content")

    # Check audit trail
    audit = temp_harness.get_audit_trail()
    assert len(audit) >= 3

    # Verify operations logged
    operations = [entry["operation"] for entry in audit]
    assert "add_candidate" in operations
    assert "evaluate" in operations
    assert "workspace_write" in operations


def test_candidate_generations(temp_harness):
    """Test multiple generations of candidates."""
    # Generation 0
    parent_id = temp_harness.add_candidate(
        config={"skills": ["skill1"]},
        generation=0
    )

    # Generation 1 (child)
    child_id = temp_harness.add_candidate(
        config={"skills": ["skill1", "skill2"]},
        generation=1,
        parent_id=parent_id
    )

    assert child_id.startswith("c001_")
    assert child_id != parent_id


def test_evaluate_nonexistent_candidate(temp_harness):
    """Test evaluating non-existent candidate raises error."""
    with pytest.raises(ValueError, match="not found"):
        temp_harness.evaluate("nonexistent_id")


def test_submit_nonexistent_candidate(temp_harness):
    """Test submitting non-existent candidate raises error."""
    with pytest.raises(ValueError, match="not found"):
        temp_harness.submit("nonexistent_id")


def test_workspace_read_nonexistent_file(temp_harness):
    """Test reading non-existent file raises error."""
    with pytest.raises(FileNotFoundError):
        temp_harness.workspace_read("nonexistent.txt")


def test_multiple_candidates_same_generation(temp_harness):
    """Test multiple candidates in same generation have unique IDs."""
    id1 = temp_harness.add_candidate(
        config={"skills": ["skill1"]},
        generation=0
    )

    id2 = temp_harness.add_candidate(
        config={"skills": ["skill2"]},
        generation=0
    )

    assert id1 != id2
    assert id1.startswith("c000_")
    assert id2.startswith("c000_")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
