"""Tests for code generation module."""

from __future__ import annotations

from pathlib import Path

import pytest

from lyra_evolution.analysis.models import Bottleneck
from lyra_evolution.generation.generator import CodeGenerator
from lyra_evolution.generation.models import GeneratedPatch, RefactoringSuggestion


@pytest.fixture
def generator():
    """Create CodeGenerator instance."""
    return CodeGenerator()


@pytest.fixture
def sample_bottleneck():
    """Sample bottleneck for testing."""
    return Bottleneck(
        function_name="calculate_fibonacci",
        type="recursive",
        severity="high",
        line_number=10,
        description="Recursive function may cause stack overflow",
        suggestion="Consider iterative approach or memoization",
    )


class TestCodeGenerator:
    """Test suite for CodeGenerator."""

    def test_generate_optimization_patch(
        self, generator: CodeGenerator, sample_bottleneck: Bottleneck
    ):
        """Test generating optimization patch for bottleneck."""
        patch = generator.generate_optimization_patch(sample_bottleneck)
        assert isinstance(patch, GeneratedPatch)
        assert patch.target_function == "calculate_fibonacci"
        assert (
            "memoization" in patch.description.lower() or "iterative" in patch.description.lower()
        )
        assert len(patch.new_code) > 0

    def test_generate_memoization_patch(self, generator: CodeGenerator):
        """Test generating memoization patch."""
        original_code = """
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""
        patch = generator.generate_memoization_patch("fibonacci", original_code)
        assert isinstance(patch, GeneratedPatch)
        assert "cache" in patch.new_code.lower() or "memo" in patch.new_code.lower()

    def test_generate_iterative_patch(self, generator: CodeGenerator):
        """Test generating iterative patch."""
        original_code = """
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""
        patch = generator.generate_iterative_patch("fibonacci", original_code)
        assert isinstance(patch, GeneratedPatch)
        assert "while" in patch.new_code.lower() or "for" in patch.new_code.lower()

    def test_suggest_refactoring(self, generator: CodeGenerator):
        """Test generating refactoring suggestions."""
        code = """
def process_data(items):
    result = []
    for item in items:
        if item.get("active"):
            result.append(item)
    return result
"""
        suggestions = generator.suggest_refactoring(code)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert all(isinstance(s, RefactoringSuggestion) for s in suggestions)

    def test_suggest_list_comprehension(self, generator: CodeGenerator):
        """Test suggesting list comprehension."""
        code = """
def process(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
"""
        suggestions = generator.suggest_refactoring(code)
        assert any("comprehension" in s.description.lower() for s in suggestions)

    def test_apply_patch(self, generator: CodeGenerator, tmp_path: Path):
        """Test applying a patch to a file."""
        original_file = tmp_path / "test.py"
        original_code = "def foo(): pass"
        original_file.write_text(original_code)

        patch = GeneratedPatch(
            target_function="foo",
            original_code=original_code,
            new_code="def foo():\n    return 42",
            description="Add return value",
            confidence=0.9,
        )

        success = generator.apply_patch(original_file, patch)
        assert success
        assert "return 42" in original_file.read_text()

    def test_validate_patch(self, generator: CodeGenerator):
        """Test patch validation."""
        valid_patch = GeneratedPatch(
            target_function="foo",
            original_code="def foo(): pass",
            new_code="def foo():\n    return 42",
            description="Valid patch",
            confidence=0.9,
        )
        assert generator.validate_patch(valid_patch)

        invalid_patch = GeneratedPatch(
            target_function="foo",
            original_code="def foo(): pass",
            new_code="def foo(",  # Invalid syntax
            description="Invalid patch",
            confidence=0.9,
        )
        assert not generator.validate_patch(invalid_patch)

    def test_generate_type_hints(self, generator: CodeGenerator):
        """Test generating type hints."""
        code = """
def add(a, b):
    return a + b
"""
        patch = generator.generate_type_hints(code)
        assert isinstance(patch, GeneratedPatch)
        assert "->" in patch.new_code  # Return type hint
        assert ":" in patch.new_code  # Parameter type hints

    def test_empty_code(self, generator: CodeGenerator):
        """Test handling empty code."""
        suggestions = generator.suggest_refactoring("")
        assert len(suggestions) == 0


@pytest.mark.integration
class TestCodeGeneratorIntegration:
    """Integration tests for CodeGenerator."""

    def test_full_optimization_workflow(self, generator: CodeGenerator, tmp_path: Path):
        """Test complete optimization workflow."""
        # Create a file with inefficient code
        test_file = tmp_path / "inefficient.py"
        test_file.write_text("""
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
""")

        # Generate optimization patch
        bottleneck = Bottleneck(
            function_name="fibonacci",
            type="recursive",
            severity="high",
            line_number=2,
            description="Recursive function",
            suggestion="Use memoization",
        )

        patch = generator.generate_optimization_patch(bottleneck)
        assert generator.validate_patch(patch)

        # Apply patch
        success = generator.apply_patch(test_file, patch)
        assert success

        # Verify the optimized code is valid Python
        optimized_code = test_file.read_text()
        compile(optimized_code, str(test_file), "exec")
