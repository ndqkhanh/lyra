"""Tests for code analysis module."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lyra_evolution.analysis.analyzer import CodeAnalyzer
from lyra_evolution.analysis.models import AnalysisResult, Bottleneck, ComplexityMetrics


@pytest.fixture
def sample_code():
    """Sample Python code for testing."""
    return """
def calculate_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)

def process_data(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        if item.get("active"):
            result.append(item)
    return result
"""


@pytest.fixture
def analyzer():
    """Create CodeAnalyzer instance."""
    return CodeAnalyzer()


class TestCodeAnalyzer:
    """Test suite for CodeAnalyzer."""

    def test_parse_code(self, analyzer: CodeAnalyzer, sample_code: str):
        """Test parsing Python code into AST."""
        tree = analyzer.parse_code(sample_code)
        assert isinstance(tree, ast.Module)
        assert len(tree.body) == 2  # Two function definitions

    def test_analyze_complexity(self, analyzer: CodeAnalyzer, sample_code: str):
        """Test complexity analysis."""
        metrics = analyzer.analyze_complexity(sample_code)
        assert isinstance(metrics, ComplexityMetrics)
        assert metrics.cyclomatic_complexity > 0
        assert metrics.cognitive_complexity > 0
        assert len(metrics.functions) == 2

    def test_detect_bottlenecks(self, analyzer: CodeAnalyzer, sample_code: str):
        """Test bottleneck detection."""
        bottlenecks = analyzer.detect_bottlenecks(sample_code)
        assert isinstance(bottlenecks, list)
        # Fibonacci should be detected as bottleneck (recursive)
        assert any(b.function_name == "calculate_fibonacci" for b in bottlenecks)

    def test_analyze_file(self, analyzer: CodeAnalyzer, tmp_path: Path):
        """Test analyzing a file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        result = analyzer.analyze_file(test_file)
        assert isinstance(result, AnalysisResult)
        assert result.file_path == test_file
        assert result.metrics is not None

    def test_analyze_directory(self, analyzer: CodeAnalyzer, tmp_path: Path):
        """Test analyzing a directory."""
        (tmp_path / "file1.py").write_text("def foo(): pass")
        (tmp_path / "file2.py").write_text("def bar(): pass")

        results = analyzer.analyze_directory(tmp_path)
        assert len(results) == 2
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_detect_recursive_functions(self, analyzer: CodeAnalyzer, sample_code: str):
        """Test detecting recursive functions."""
        tree = analyzer.parse_code(sample_code)
        recursive = analyzer.detect_recursive_functions(tree)
        assert "calculate_fibonacci" in recursive

    def test_detect_inefficient_loops(self, analyzer: CodeAnalyzer):
        """Test detecting inefficient loops."""
        code = """
def process(items):
    result = []
    for item in items:
        result.append(item)  # Could use list comprehension
    return result
"""
        bottlenecks = analyzer.detect_bottlenecks(code)
        assert any(b.type == "inefficient_loop" for b in bottlenecks)

    def test_empty_code(self, analyzer: CodeAnalyzer):
        """Test handling empty code."""
        metrics = analyzer.analyze_complexity("")
        assert metrics.cyclomatic_complexity == 0
        assert len(metrics.functions) == 0

    def test_invalid_syntax(self, analyzer: CodeAnalyzer):
        """Test handling invalid syntax."""
        with pytest.raises(SyntaxError):
            analyzer.parse_code("def foo(")


@pytest.mark.integration
class TestCodeAnalyzerIntegration:
    """Integration tests for CodeAnalyzer."""

    def test_analyze_real_codebase(self, analyzer: CodeAnalyzer):
        """Test analyzing actual lyra-evolution codebase."""
        base_path = Path(__file__).parent.parent.parent / "src" / "lyra_evolution"
        if not base_path.exists():
            pytest.skip("Source directory not found")

        results = analyzer.analyze_directory(base_path)
        assert len(results) > 0

        # Check that we found some complexity
        total_complexity = sum(r.metrics.cyclomatic_complexity for r in results)
        assert total_complexity > 0
