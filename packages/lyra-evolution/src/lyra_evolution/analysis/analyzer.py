"""Code analyzer for static analysis and bottleneck detection."""

from __future__ import annotations

import ast
import time
from pathlib import Path

from .models import AnalysisResult, Bottleneck, ComplexityMetrics


class CodeAnalyzer:
    """Analyzes Python code for complexity and bottlenecks."""

    def parse_code(self, code: str) -> ast.Module:
        """Parse Python code into AST.

        Args:
            code: Python source code

        Returns:
            AST module

        Raises:
            SyntaxError: If code has invalid syntax
        """
        return ast.parse(code)

    def analyze_complexity(self, code: str) -> ComplexityMetrics:
        """Analyze code complexity.

        Args:
            code: Python source code

        Returns:
            Complexity metrics
        """
        if not code.strip():
            return ComplexityMetrics(
                cyclomatic_complexity=0,
                cognitive_complexity=0,
                functions=[],
                classes=[],
                lines_of_code=0,
                comment_ratio=0.0,
            )

        try:
            tree = self.parse_code(code)
        except SyntaxError:
            return ComplexityMetrics(
                cyclomatic_complexity=0,
                cognitive_complexity=0,
                functions=[],
                classes=[],
                lines_of_code=0,
                comment_ratio=0.0,
            )

        functions = []
        classes = []
        cyclomatic = 0
        cognitive = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                cyclomatic += self._calculate_cyclomatic(node)
                cognitive += self._calculate_cognitive(node)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

        lines = code.split("\n")
        loc = len([line for line in lines if line.strip() and not line.strip().startswith("#")])
        comment_lines = len([line for line in lines if line.strip().startswith("#")])
        comment_ratio = comment_lines / len(lines) if lines else 0.0

        return ComplexityMetrics(
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            functions=functions,
            classes=classes,
            lines_of_code=loc,
            comment_ratio=comment_ratio,
        )

    def detect_bottlenecks(self, code: str) -> list[Bottleneck]:
        """Detect performance bottlenecks.

        Args:
            code: Python source code

        Returns:
            List of detected bottlenecks
        """
        try:
            tree = self.parse_code(code)
        except SyntaxError:
            return []

        bottlenecks = []

        # Detect recursive functions
        recursive = self.detect_recursive_functions(tree)
        for func_name in recursive:
            bottlenecks.append(
                Bottleneck(
                    function_name=func_name,
                    type="recursive",
                    severity="high",
                    line_number=self._get_function_line(tree, func_name),
                    description=f"Recursive function {func_name} may cause stack overflow",
                    suggestion="Consider iterative approach or memoization",
                )
            )

        # Detect inefficient loops
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self._has_inefficient_loop(node):
                    bottlenecks.append(
                        Bottleneck(
                            function_name=node.name,
                            type="inefficient_loop",
                            severity="medium",
                            line_number=node.lineno,
                            description=f"Function {node.name} has inefficient loop pattern",
                            suggestion="Consider list comprehension or generator expression",
                        )
                    )

        return bottlenecks

    def detect_recursive_functions(self, tree: ast.Module) -> set[str]:
        """Detect recursive function calls.

        Args:
            tree: AST module

        Returns:
            Set of recursive function names
        """
        recursive = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name) and child.func.id == func_name:
                            recursive.add(func_name)

        return recursive

    def analyze_file(self, file_path: Path) -> AnalysisResult:
        """Analyze a single file.

        Args:
            file_path: Path to Python file

        Returns:
            Analysis result
        """
        code = file_path.read_text()
        metrics = self.analyze_complexity(code)
        bottlenecks = self.detect_bottlenecks(code)

        return AnalysisResult(
            file_path=file_path,
            metrics=metrics,
            bottlenecks=bottlenecks,
            timestamp=time.time(),
        )

    def analyze_directory(self, directory: Path) -> list[AnalysisResult]:
        """Analyze all Python files in a directory.

        Args:
            directory: Directory path

        Returns:
            List of analysis results
        """
        results = []
        for py_file in directory.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                try:
                    result = self.analyze_file(py_file)
                    results.append(result)
                except Exception:
                    # Skip files that can't be analyzed
                    continue

        return results

    def _calculate_cyclomatic(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _calculate_cognitive(self, node: ast.FunctionDef) -> int:
        """Calculate cognitive complexity for a function."""
        cognitive = 0
        nesting_level = 0

        def visit(n: ast.AST, level: int) -> None:
            nonlocal cognitive
            if isinstance(n, (ast.If, ast.While, ast.For)):
                cognitive += 1 + level
                for child in ast.iter_child_nodes(n):
                    visit(child, level + 1)
            else:
                for child in ast.iter_child_nodes(n):
                    visit(child, level)

        for child in ast.iter_child_nodes(node):
            visit(child, nesting_level)

        return cognitive

    def _has_inefficient_loop(self, node: ast.FunctionDef) -> bool:
        """Check if function has inefficient loop patterns."""
        for child in ast.walk(node):
            if isinstance(child, ast.For):
                # Check for append pattern in loop
                for stmt in ast.walk(child):
                    if isinstance(stmt, ast.Call):
                        if isinstance(stmt.func, ast.Attribute):
                            if stmt.func.attr == "append":
                                return True
        return False

    def _get_function_line(self, tree: ast.Module, func_name: str) -> int:
        """Get line number of a function."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                return node.lineno
        return 0
