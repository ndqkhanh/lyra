"""
Tests for RepoBench-Memory evaluation harness.

Tests cover:
- Dataset loading and parsing
- Metric computation (EM, ES, CodeBLEU, Accuracy@k)
- Completion evaluation
- Retrieval evaluation
- Result serialization/deserialization
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from lyra_core.eval.repobench_memory import (
    EvalContext,
    EvalMetrics,
    EvalResult,
    EvalTask,
    RepoBenchMemoryEval,
    RepoBenchSample,
)


@pytest.fixture
def eval_harness():
    """Create RepoBenchMemoryEval instance with temp cache dir."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield RepoBenchMemoryEval(cache_dir=tmpdir)


@pytest.fixture
def sample_data():
    """Create sample RepoBench data for testing."""
    return [
        RepoBenchSample(
            repo_name="test/repo1",
            file_path="src/main.py",
            context="def add(a, b):\n    ",
            target="return a + b",
            cross_file_context=["from utils import helper", "import math"],
            metadata={"line_number": 10},
        ),
        RepoBenchSample(
            repo_name="test/repo2",
            file_path="src/utils.py",
            context="class Calculator:\n    def multiply(self, x, y):\n        ",
            target="return x * y",
            cross_file_context=["from typing import Union"],
            metadata={"line_number": 5},
        ),
    ]


class TestMetricComputation:
    """Test metric computation functions."""

    def test_exact_match_positive(self, eval_harness):
        """Test exact match with identical strings."""
        prediction = "return a + b"
        target = "return a + b"
        score = eval_harness.compute_exact_match(prediction, target)
        assert score == 1.0

    def test_exact_match_negative(self, eval_harness):
        """Test exact match with different strings."""
        prediction = "return a + b"
        target = "return a - b"
        score = eval_harness.compute_exact_match(prediction, target)
        assert score == 0.0

    def test_exact_match_whitespace_normalized(self, eval_harness):
        """Test exact match normalizes whitespace."""
        prediction = "  return a + b  "
        target = "return a + b"
        score = eval_harness.compute_exact_match(prediction, target)
        assert score == 1.0

    def test_edit_similarity_identical(self, eval_harness):
        """Test edit similarity with identical strings."""
        prediction = "return a + b"
        target = "return a + b"
        score = eval_harness.compute_edit_similarity(prediction, target)
        assert score == 1.0

    def test_edit_similarity_partial(self, eval_harness):
        """Test edit similarity with partial match."""
        prediction = "return a + b"
        target = "return a - b"
        score = eval_harness.compute_edit_similarity(prediction, target)
        assert 0.8 < score < 1.0  # High similarity, only one char different

    def test_edit_similarity_empty(self, eval_harness):
        """Test edit similarity with empty strings."""
        assert eval_harness.compute_edit_similarity("", "") == 1.0
        assert eval_harness.compute_edit_similarity("test", "") == 0.0
        assert eval_harness.compute_edit_similarity("", "test") == 0.0

    def test_codebleu_computation(self, eval_harness):
        """Test CodeBLEU computation."""
        prediction = "return a + b"
        target = "return a + b"
        score = eval_harness.compute_codebleu(prediction, target, "python")
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be high for identical code

    def test_codebleu_different_code(self, eval_harness):
        """Test CodeBLEU with different code."""
        prediction = "return a + b"
        target = "return x * y"
        score = eval_harness.compute_codebleu(prediction, target, "python")
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should be low for different code

    def test_accuracy_at_k_hit(self, eval_harness):
        """Test Accuracy@k with relevant item in top-k."""
        retrieved = ["snippet1", "snippet2", "snippet3", "snippet4"]
        relevant = ["snippet2", "snippet5"]

        assert eval_harness.compute_accuracy_at_k(retrieved, relevant, k=1) == 0.0
        assert eval_harness.compute_accuracy_at_k(retrieved, relevant, k=2) == 1.0
        assert eval_harness.compute_accuracy_at_k(retrieved, relevant, k=3) == 1.0

    def test_accuracy_at_k_miss(self, eval_harness):
        """Test Accuracy@k with no relevant items in top-k."""
        retrieved = ["snippet1", "snippet2", "snippet3"]
        relevant = ["snippet4", "snippet5"]

        assert eval_harness.compute_accuracy_at_k(retrieved, relevant, k=1) == 0.0
        assert eval_harness.compute_accuracy_at_k(retrieved, relevant, k=3) == 0.0

    def test_accuracy_at_k_empty_relevant(self, eval_harness):
        """Test Accuracy@k with no relevant items."""
        retrieved = ["snippet1", "snippet2"]
        relevant = []

        assert eval_harness.compute_accuracy_at_k(retrieved, relevant, k=1) == 1.0


class TestCompletionEvaluation:
    """Test completion task evaluation."""

    def test_evaluate_completion_basic(self, eval_harness, sample_data):
        """Test basic completion evaluation."""
        def generate_fn(_context, _cross_file_context):
            # Simple mock generator that returns target
            if "add" in _context:
                return "return a + b"
            return "return x * y"

        result = eval_harness.evaluate_completion(
            samples=sample_data,
            generate_fn=generate_fn,
            language="python",
            context=EvalContext.CROSS_FILE_FIRST,
        )

        assert result.task == EvalTask.COMPLETION
        assert result.context == EvalContext.CROSS_FILE_FIRST
        assert result.language == "python"
        assert result.metrics.num_samples == 2
        assert result.metrics.exact_match == 1.0  # Both predictions match
        assert result.metrics.edit_similarity == 1.0
        assert len(result.per_sample_results) == 2

    def test_evaluate_completion_partial_match(self, eval_harness, sample_data):
        """Test completion evaluation with partial matches."""
        def generate_fn(_context, _cross_file_context):
            # Generator that returns slightly different predictions
            if "add" in _context:
                return "return a + b + 0"  # Close but not exact
            return "return x * y"

        result = eval_harness.evaluate_completion(
            samples=sample_data,
            generate_fn=generate_fn,
            language="python",
            context=EvalContext.CROSS_FILE_RANDOM,
        )

        assert result.metrics.num_samples == 2
        assert result.metrics.exact_match == 0.5  # Only one exact match
        assert result.metrics.edit_similarity > 0.5  # High similarity overall

    def test_evaluate_completion_empty_samples(self, eval_harness):
        """Test completion evaluation with empty sample list."""
        def generate_fn(_context, _cross_file_context):
            return "dummy"

        result = eval_harness.evaluate_completion(
            samples=[],
            generate_fn=generate_fn,
            language="python",
            context=EvalContext.IN_FILE,
        )

        assert result.metrics.num_samples == 0
        assert result.metrics.exact_match == 0.0
        assert len(result.per_sample_results) == 0


class TestRetrievalEvaluation:
    """Test retrieval task evaluation."""

    def test_evaluate_retrieval_basic(self, eval_harness, sample_data):
        """Test basic retrieval evaluation."""
        def retrieve_fn(_context):
            # Mock retriever that returns relevant snippets
            if "add" in _context:
                return ["from utils import helper", "import math", "other"]
            return ["from typing import Union", "import sys"]

        result = eval_harness.evaluate_retrieval(
            samples=sample_data,
            retrieve_fn=retrieve_fn,
            context=EvalContext.CROSS_FILE_FIRST,
        )

        assert result.task == EvalTask.RETRIEVAL
        assert result.context == EvalContext.CROSS_FILE_FIRST
        assert result.metrics.num_samples == 2
        assert result.metrics.accuracy_at_1 == 1.0  # Both have relevant in top-1
        assert result.metrics.accuracy_at_3 == 1.0
        assert len(result.per_sample_results) == 2

    def test_evaluate_retrieval_partial_accuracy(self, eval_harness, sample_data):
        """Test retrieval evaluation with partial accuracy."""
        def retrieve_fn(_context):
            # Mock retriever with varying accuracy
            if "add" in _context:
                return ["irrelevant1", "from utils import helper", "irrelevant2"]
            return ["irrelevant", "from typing import Union"]

        result = eval_harness.evaluate_retrieval(
            samples=sample_data,
            retrieve_fn=retrieve_fn,
            context=EvalContext.CROSS_FILE_RANDOM,
        )

        assert result.metrics.num_samples == 2
        assert result.metrics.accuracy_at_1 == 0.0  # No relevant in top-1
        assert result.metrics.accuracy_at_3 == 1.0  # All relevant in top-3

    def test_evaluate_retrieval_empty_samples(self, eval_harness):
        """Test retrieval evaluation with empty sample list."""
        def retrieve_fn(_context):
            return ["dummy"]

        result = eval_harness.evaluate_retrieval(
            samples=[],
            retrieve_fn=retrieve_fn,
            context=EvalContext.IN_FILE,
        )

        assert result.metrics.num_samples == 0
        assert result.metrics.accuracy_at_1 == 0.0


class TestResultSerialization:
    """Test result saving and loading."""

    def test_save_and_load_results(self, eval_harness, sample_data):
        """Test saving and loading evaluation results."""
        # Create a result
        def generate_fn(_context, _cross_file_context):
            return "return a + b"

        result = eval_harness.evaluate_completion(
            samples=sample_data[:1],  # Use one sample
            generate_fn=generate_fn,
            language="python",
            context=EvalContext.CROSS_FILE_FIRST,
        )

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            eval_harness.save_results(result, temp_path)

            # Verify file exists and is valid JSON
            assert temp_path.exists()
            with open(temp_path) as f:
                data = json.load(f)
            assert "task" in data
            assert "metrics" in data

            # Load back
            loaded_result = eval_harness.load_results(temp_path)

            # Verify loaded result matches original
            assert loaded_result.task == result.task
            assert loaded_result.context == result.context
            assert loaded_result.language == result.language
            assert loaded_result.metrics.num_samples == result.metrics.num_samples
            assert loaded_result.metrics.exact_match == result.metrics.exact_match

        finally:
            temp_path.unlink(missing_ok=True)

    def test_save_results_creates_directory(self, eval_harness):
        """Test that save_results creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "results.json"

            # Create minimal result
            result = EvalResult(
                task=EvalTask.COMPLETION,
                context=EvalContext.IN_FILE,
                language="python",
                metrics=EvalMetrics(num_samples=0),
            )

            eval_harness.save_results(result, output_path)
            assert output_path.exists()


class TestDatasetLoading:
    """Test dataset loading from Hugging Face."""

    @patch("lyra_core.eval.repobench_memory.load_dataset")
    def test_load_dataset_success(self, mock_load_dataset, eval_harness):
        """Test successful dataset loading."""
        # Mock dataset
        mock_dataset = [
            {
                "repo_name": "test/repo",
                "file_path": "main.py",
                "context": "def foo():\n    ",
                "target": "return 42",
                "cross_file_context": ["import bar"],
                "metadata": {"line": 10},
            }
        ]
        mock_load_dataset.return_value = mock_dataset

        samples = eval_harness.load_dataset(
            language="python",
            context=EvalContext.CROSS_FILE_FIRST,
            split="test",
        )

        assert len(samples) == 1
        assert samples[0].repo_name == "test/repo"
        assert samples[0].target == "return 42"
        mock_load_dataset.assert_called_once()

    @patch("lyra_core.eval.repobench_memory.load_dataset")
    def test_load_dataset_max_samples(self, mock_load_dataset, eval_harness):
        """Test dataset loading with max_samples limit."""
        # Mock dataset with 5 items
        mock_dataset = [
            {
                "repo_name": f"repo{i}",
                "file_path": "main.py",
                "context": "code",
                "target": "target",
                "cross_file_context": [],
                "metadata": {},
            }
            for i in range(5)
        ]
        mock_load_dataset.return_value = mock_dataset

        samples = eval_harness.load_dataset(
            language="python",
            context=EvalContext.IN_FILE,
            split="test",
            max_samples=3,
        )

        assert len(samples) == 3

    @patch("lyra_core.eval.repobench_memory.load_dataset")
    def test_load_dataset_failure(self, mock_load_dataset, eval_harness):
        """Test dataset loading failure handling."""
        mock_load_dataset.side_effect = Exception("Network error")

        with pytest.raises(RuntimeError, match="Failed to load RepoBench dataset"):
            eval_harness.load_dataset(
                language="python",
                context=EvalContext.CROSS_FILE_FIRST,
                split="test",
            )


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_initialization_without_datasets_library(self):
        """Test initialization fails gracefully without datasets library."""
        with patch("lyra_core.eval.repobench_memory.HAS_DATASETS", False):
            with pytest.raises(ImportError, match="datasets library is required"):
                RepoBenchMemoryEval()

    def test_metrics_with_zero_samples(self):
        """Test metrics computation with zero samples."""
        metrics = EvalMetrics(num_samples=0)
        assert metrics.exact_match == 0.0
        assert metrics.edit_similarity == 0.0
        assert metrics.codebleu == 0.0

    def test_sample_with_missing_fields(self):
        """Test RepoBenchSample handles missing optional fields."""
        sample = RepoBenchSample(
            repo_name="test",
            file_path="main.py",
            context="code",
            target="target",
        )
        assert sample.cross_file_context == []
        assert sample.metadata == {}
