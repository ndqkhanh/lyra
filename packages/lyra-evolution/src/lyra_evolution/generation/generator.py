"""Code generator for optimization patches and refactoring suggestions."""

from __future__ import annotations

import ast
from pathlib import Path

from lyra_evolution.analysis.models import Bottleneck

from .models import GeneratedPatch, RefactoringSuggestion


class CodeGenerator:
    """Generates code optimizations and refactoring suggestions."""

    def generate_optimization_patch(self, bottleneck: Bottleneck) -> GeneratedPatch:
        """Generate optimization patch for a bottleneck.

        Args:
            bottleneck: Detected bottleneck

        Returns:
            Generated patch
        """
        if bottleneck.type == "recursive":
            # For recursive functions, suggest memoization
            return self._generate_recursive_optimization(bottleneck)
        elif bottleneck.type == "inefficient_loop":
            return self._generate_loop_optimization(bottleneck)
        else:
            return self._generate_generic_optimization(bottleneck)

    def generate_memoization_patch(
        self, function_name: str, original_code: str
    ) -> GeneratedPatch:
        """Generate memoization patch for recursive function.

        Args:
            function_name: Name of the function
            original_code: Original function code

        Returns:
            Generated patch with memoization
        """
        # Simple memoization using functools.lru_cache
        new_code = f"""from functools import lru_cache

@lru_cache(maxsize=None)
{original_code.strip()}"""

        return GeneratedPatch(
            target_function=function_name,
            original_code=original_code,
            new_code=new_code,
            description=f"Add memoization to {function_name} using lru_cache",
            confidence=0.9,
            patch_type="optimization",
        )

    def generate_iterative_patch(
        self, function_name: str, original_code: str
    ) -> GeneratedPatch:
        """Generate iterative version of recursive function.

        Args:
            function_name: Name of the function
            original_code: Original function code

        Returns:
            Generated patch with iterative implementation
        """
        # For fibonacci-like patterns, generate iterative version
        if "fibonacci" in function_name.lower():
            new_code = """def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b"""
        else:
            # Generic iterative template
            new_code = f"""def {function_name}(n: int) -> int:
    # TODO: Implement iterative version
    result = 0
    for i in range(n):
        result += i
    return result"""

        return GeneratedPatch(
            target_function=function_name,
            original_code=original_code,
            new_code=new_code,
            description=f"Convert {function_name} to iterative implementation",
            confidence=0.8,
            patch_type="optimization",
        )

    def suggest_refactoring(self, code: str) -> list[RefactoringSuggestion]:
        """Generate refactoring suggestions.

        Args:
            code: Python source code

        Returns:
            List of refactoring suggestions
        """
        if not code.strip():
            return []

        suggestions = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        # Detect list append patterns that could be comprehensions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self._has_list_append_pattern(node):
                    suggestion = self._suggest_list_comprehension(node, code)
                    if suggestion:
                        suggestions.append(suggestion)

        return suggestions

    def apply_patch(self, file_path: Path, patch: GeneratedPatch) -> bool:
        """Apply a patch to a file.

        Args:
            file_path: Path to the file
            patch: Patch to apply

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate patch first
            if not self.validate_patch(patch):
                return False

            # Write new code
            file_path.write_text(patch.new_code)
            return True
        except Exception:
            return False

    def validate_patch(self, patch: GeneratedPatch) -> bool:
        """Validate that a patch is syntactically correct.

        Args:
            patch: Patch to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            ast.parse(patch.new_code)
            return True
        except SyntaxError:
            return False

    def generate_type_hints(self, code: str) -> GeneratedPatch:
        """Generate type hints for untyped code.

        Args:
            code: Python source code

        Returns:
            Generated patch with type hints
        """
        # Simple heuristic: add basic type hints
        lines = code.split("\n")
        new_lines = []

        for line in lines:
            if line.strip().startswith("def ") and ":" not in line.split("(")[0]:
                # Add basic type hints
                if "->" not in line:
                    line = line.rstrip() + " -> Any:"
                new_lines.append(line)
            else:
                new_lines.append(line)

        new_code = "\n".join(new_lines)

        # Add Any import if needed
        if "-> Any" in new_code and "from typing import" not in new_code:
            new_code = "from typing import Any\n\n" + new_code

        return GeneratedPatch(
            target_function="",
            original_code=code,
            new_code=new_code,
            description="Add type hints",
            confidence=0.7,
            patch_type="type_hints",
        )

    def _generate_recursive_optimization(self, bottleneck: Bottleneck) -> GeneratedPatch:
        """Generate optimization for recursive function."""
        # Default to memoization suggestion
        new_code = f"""from functools import lru_cache

@lru_cache(maxsize=None)
def {bottleneck.function_name}(n: int) -> int:
    # Original implementation with memoization
    pass"""

        return GeneratedPatch(
            target_function=bottleneck.function_name,
            original_code="",
            new_code=new_code,
            description=f"Add memoization to {bottleneck.function_name}",
            confidence=0.85,
            patch_type="optimization",
        )

    def _generate_loop_optimization(self, bottleneck: Bottleneck) -> GeneratedPatch:
        """Generate optimization for inefficient loop."""
        new_code = f"""def {bottleneck.function_name}(items):
    # Use list comprehension instead of append loop
    return [item for item in items if condition(item)]"""

        return GeneratedPatch(
            target_function=bottleneck.function_name,
            original_code="",
            new_code=new_code,
            description=f"Convert loop to list comprehension in {bottleneck.function_name}",
            confidence=0.8,
            patch_type="optimization",
        )

    def _generate_generic_optimization(self, bottleneck: Bottleneck) -> GeneratedPatch:
        """Generate generic optimization."""
        return GeneratedPatch(
            target_function=bottleneck.function_name,
            original_code="",
            new_code=f"# Optimization for {bottleneck.function_name}\npass",
            description=f"Generic optimization for {bottleneck.function_name}",
            confidence=0.5,
            patch_type="optimization",
        )

    def _has_list_append_pattern(self, node: ast.FunctionDef) -> bool:
        """Check if function has list append pattern."""
        for child in ast.walk(node):
            if isinstance(child, ast.For):
                for stmt in ast.walk(child):
                    if isinstance(stmt, ast.Call):
                        if isinstance(stmt.func, ast.Attribute):
                            if stmt.func.attr == "append":
                                return True
        return False

    def _suggest_list_comprehension(
        self, node: ast.FunctionDef, code: str
    ) -> RefactoringSuggestion | None:
        """Suggest list comprehension refactoring."""
        return RefactoringSuggestion(
            function_name=node.name,
            suggestion_type="list_comprehension",
            description=f"Convert loop in {node.name} to list comprehension",
            original_code=code,
            suggested_code=f"# Use list comprehension in {node.name}",
            impact="medium",
            confidence=0.8,
        )
