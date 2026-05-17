"""Tests for evolution harness permission boundaries."""
import pytest
from pathlib import Path


def test_workspace_read_allowed(mock_harness):
    """Test that agent can read from workspace."""
    # Write test file
    test_file = mock_harness.workspace_dir / "test.txt"
    test_file.write_text("test content")

    # Read should succeed
    content = mock_harness.workspace_read("test.txt")
    assert content == "test content"


def test_workspace_read_nonexistent(mock_harness):
    """Test reading nonexistent file returns None."""
    content = mock_harness.workspace_read("nonexistent.txt")
    assert content is None


def test_workspace_read_blocked_evaluator(mock_harness):
    """Test that agent cannot read evaluator internals."""
    # Try to read evaluator file via path traversal
    with pytest.raises(PermissionError, match="Access denied"):
        mock_harness.workspace_read("../evaluator/test_cases.py")


def test_workspace_read_blocked_scores(mock_harness):
    """Test that agent cannot read score files."""
    # Try to read scores via path traversal
    with pytest.raises(PermissionError, match="Access denied"):
        mock_harness.workspace_read("../archive/scores/score.json")


def test_workspace_write_allowed(mock_harness):
    """Test that agent can write to workspace."""
    # Write should succeed
    success = mock_harness.workspace_write("output.txt", "test output")
    assert success is True

    # Verify file was written
    output_file = mock_harness.workspace_dir / "output.txt"
    assert output_file.exists()
    assert output_file.read_text() == "test output"


def test_workspace_write_creates_subdirs(mock_harness):
    """Test that workspace_write creates parent directories."""
    # Write to nested path
    success = mock_harness.workspace_write("subdir/nested/file.txt", "nested content")
    assert success is True

    # Verify file was written
    nested_file = mock_harness.workspace_dir / "subdir" / "nested" / "file.txt"
    assert nested_file.exists()
    assert nested_file.read_text() == "nested content"


def test_workspace_write_blocked_evaluator(mock_harness):
    """Test that agent cannot write to evaluator directory."""
    # Try to write to evaluator via path traversal
    with pytest.raises(PermissionError, match="Access denied"):
        mock_harness.workspace_write("../evaluator/malicious.py", "hacked")


def test_workspace_write_blocked_scores(mock_harness):
    """Test that agent cannot write to scores directory."""
    # Try to write to scores via path traversal
    with pytest.raises(PermissionError, match="Access denied"):
        mock_harness.workspace_write("../archive/scores/fake.json", "hacked")


def test_score_submission_write_only(mock_harness):
    """Test that score submission is write-only."""
    # Submit score (should succeed)
    success = mock_harness.submit("candidate_001")
    assert success is True

    # Try to read submitted score (should fail)
    with pytest.raises(PermissionError, match="Access denied"):
        mock_harness.workspace_read("../archive/scores/candidate_001.json")


def test_path_traversal_absolute_blocked(mock_harness):
    """Test that absolute paths are blocked."""
    # Try to read absolute path
    with pytest.raises(PermissionError, match="Access denied"):
        mock_harness.workspace_read("/etc/passwd")


def test_path_traversal_parent_blocked(mock_harness):
    """Test that parent directory traversal is blocked."""
    # Try multiple levels of parent traversal
    with pytest.raises(PermissionError, match="Access denied"):
        mock_harness.workspace_read("../../../../../../etc/passwd")


def test_legitimate_workflow_succeeds(mock_harness):
    """Test that legitimate evolution workflow succeeds."""
    # 1. Read workspace file
    mock_harness.workspace_write("candidate.py", "def solve(): return 42")
    content = mock_harness.workspace_read("candidate.py")
    assert content == "def solve(): return 42"

    # 2. Modify candidate
    mock_harness.workspace_write("candidate.py", "def solve(): return 43")

    # 3. Submit score
    success = mock_harness.submit("candidate_001")
    assert success is True


def test_evaluate_candidate(mock_harness):
    """Test candidate evaluation through harness."""
    # Create candidate file
    candidate_path = mock_harness.archive_dir / "candidates" / "candidate_001.json"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text('{"code": "def solve(): return 42"}')

    # Evaluate candidate
    result = mock_harness.evaluate("candidate_001")

    # Check result
    assert "score" in result
    assert "candidate_id" in result
    assert result["candidate_id"] == "candidate_001"

    # Verify score was written to protected directory
    score_path = mock_harness.archive_dir / "scores" / "candidate_001.json"
    assert score_path.exists()


def test_evaluate_nonexistent_candidate(mock_harness):
    """Test evaluating nonexistent candidate returns error."""
    result = mock_harness.evaluate("nonexistent")

    assert "error" in result
    assert result["score"] == 0.0


def test_harness_error_messages_clear(mock_harness):
    """Test that permission errors have clear messages."""
    # Try to access protected path
    try:
        mock_harness.workspace_read("../evaluator/secret.py")
        assert False, "Should have raised PermissionError"
    except PermissionError as e:
        # Error message should be clear
        assert "Access denied" in str(e)
        assert "outside workspace" in str(e)
