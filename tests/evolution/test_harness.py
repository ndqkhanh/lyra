"""Unit tests for EvolutionHarness boundary enforcement."""
import pytest
from pathlib import Path
from lyra_cli.evolution.harness import EvolutionHarness


class TestEvolutionHarness:
    """Test harness security boundaries."""

    @pytest.fixture
    def harness(self, tmp_path):
        """Create test harness with temporary directories."""
        evolution_dir = tmp_path / ".lyra" / "evolution"
        evolution_dir.mkdir(parents=True)
        (evolution_dir / "workspace").mkdir()
        (evolution_dir / "archive").mkdir()
        (evolution_dir / "evaluator").mkdir()
        return EvolutionHarness(evolution_dir)

    def test_workspace_read_valid_path(self, harness):
        """Valid workspace reads should succeed."""
        harness.workspace_write("test.txt", "content")
        result = harness.workspace_read("test.txt")
        assert result == "content"

    def test_workspace_read_invalid_path(self, harness):
        """Reads outside workspace should fail."""
        result = harness.workspace_read("../evaluator/test.py")
        assert result is None

    def test_workspace_read_path_traversal(self, harness):
        """Path traversal attacks should be blocked."""
        attacks = [
            "../../../etc/passwd",
            "../../evaluator/scorer.py",
            "../archive/scores/fake.json",
            "workspace/../../evaluator/test.py",
        ]
        for attack_path in attacks:
            result = harness.workspace_read(attack_path)
            assert result is None, f"Should block: {attack_path}"

    def test_workspace_write_valid_path(self, harness):
        """Valid workspace writes should succeed."""
        result = harness.workspace_write("test.txt", "content")
        assert result is True

        # Verify content was written
        content = harness.workspace_read("test.txt")
        assert content == "content"

    def test_workspace_write_invalid_path(self, harness):
        """Writes outside workspace should fail."""
        result = harness.workspace_write("../archive/fake.json", "hack")
        assert result is False

    def test_workspace_write_path_traversal(self, harness):
        """Path traversal in writes should be blocked."""
        attacks = [
            "../evaluator/malicious.py",
            "../../archive/scores/fake_score.json",
            "../../../tmp/exploit.sh",
        ]
        for attack_path in attacks:
            result = harness.workspace_write(attack_path, "malicious")
            assert result is False, f"Should block: {attack_path}"

    def test_evaluate_returns_redacted_results(self, harness):
        """Evaluate should return score but not test cases."""
        # Create mock candidate
        candidate_path = harness.workspace_dir / "candidate.py"
        candidate_path.write_text("def solve(x): return x * 2")

        result = harness.evaluate("test_001")

        # Should return score
        assert "score" in result

        # Should NOT leak internals
        assert "test_cases" not in result
        assert "evaluator_code" not in result
        assert "scorer_logic" not in result

    def test_harness_prevents_archive_access(self, harness):
        """Harness should block direct archive access."""
        # Create fake score file
        scores_dir = harness.archive_dir / "scores"
        scores_dir.mkdir(parents=True, exist_ok=True)
        (scores_dir / "candidate_001.json").write_text('{"score": 100}')

        # Attempt to read it (should fail)
        result = harness.workspace_read("../archive/scores/candidate_001.json")
        assert result is None

    def test_harness_prevents_evaluator_access(self, harness):
        """Harness should block evaluator internals."""
        # Create fake evaluator file
        (harness.evaluator_dir / "test_cases.py").write_text("SECRET_TESTS = []")

        # Attempt to read it (should fail)
        result = harness.workspace_read("../evaluator/test_cases.py")
        assert result is None

    def test_workspace_subdirectories_allowed(self, harness):
        """Subdirectories within workspace should be allowed."""
        # Create subdirectory
        result = harness.workspace_write("subdir/file.txt", "content")
        assert result is True

        # Read from subdirectory
        content = harness.workspace_read("subdir/file.txt")
        assert content == "content"

    def test_empty_path_rejected(self, harness):
        """Empty paths should be rejected."""
        assert harness.workspace_read("") is None
        assert harness.workspace_write("", "content") is False

    def test_absolute_path_rejected(self, harness):
        """Absolute paths should be rejected."""
        assert harness.workspace_read("/etc/passwd") is None
        assert harness.workspace_write("/tmp/exploit", "hack") is False
