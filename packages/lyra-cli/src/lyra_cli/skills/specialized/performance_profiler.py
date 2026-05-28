"""
Performance Profiler Skill - Profile code sections and suggest optimizations.

Analyzes code for:
- Computational complexity hot spots
- Bottlenecks in loops and recursion
- Unnecessary allocations
- Optimizable patterns

Estimates time/space complexity and suggests improvements.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum


class ComplexityClass(StrEnum):
    """Time complexity classes."""

    CONSTANT = "O(1)"
    LOGARITHMIC = "O(log n)"
    LINEAR = "O(n)"
    LINEARRITHMIC = "O(n log n)"
    QUADRATIC = "O(n^2)"
    CUBIC = "O(n^3)"
    EXPONENTIAL = "O(2^n)"
    UNKNOWN = "O(?)"


@dataclass(frozen=True)
class PerformanceIssue:
    """A single performance issue finding."""

    line: int
    target: str
    description: str
    complexity: ComplexityClass
    suggestion: str
    estimated_impact: str


@dataclass(frozen=True)
class ProfileResult:
    """Performance profile for a code unit."""

    name: str
    type: str
    line: int
    estimated_complexity: ComplexityClass
    issues: tuple[PerformanceIssue, ...]
    optimization_score: int


@dataclass(frozen=True)
class ProfileReport:
    """Complete performance profiling report."""

    module_name: str
    total_lines: int
    results: tuple[ProfileResult, ...]
    summary: dict[str, int]


class PerformanceProfilerSkill:
    """Profile code sections for performance bottlenecks and optimizations."""

    def run(self, input_data: dict) -> dict:
        """Profile the provided source code for performance issues.

        Args:
            input_data: Dictionary with keys:
                - source: Source code string
                - module_name: Module name (default "module")

        Returns:
            Dictionary with profile report.
        """
        source = input_data.get("source", "")
        if not source:
            return {"error": "No source code provided", "results": []}

        module_name = input_data.get("module_name", "module")

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "results": []}

        results: list[ProfileResult] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                pr = self._profile_function(node, source)
                if pr:
                    results.append(pr)
            elif isinstance(node, ast.For):
                pr = self._profile_loop(node)
                if pr:
                    results.append(pr)

        summary = self._compute_summary(results)
        return ProfileReport(
            module_name=module_name,
            total_lines=len(source.splitlines()),
            results=tuple(results),
            summary=summary,
        ).__dict__ | {"results": [r.__dict__ for r in results]}

    def _profile_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, source: str
    ) -> ProfileResult | None:
        """Profile a function for performance characteristics."""
        issues: list[PerformanceIssue] = []
        complexity = self._estimate_complexity(node)

        # Check for nested loops
        nested_loops = self._count_nested_loops(node)
        if nested_loops >= 2:
            issues.append(
                PerformanceIssue(
                    line=node.lineno,
                    target=node.name,
                    description=f"Nested loops detected (depth {nested_loops}).",
                    complexity=ComplexityClass.QUADRATIC
                    if nested_loops == 2
                    else ComplexityClass.CUBIC,
                    suggestion="Consider flattening loops or using more efficient data structures.",
                    estimated_impact="high",
                )
            )

        # Check for list/dict/set creation in loops
        for child in ast.walk(node):
            if isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp)):
                issues.append(
                    PerformanceIssue(
                        line=child.lineno,
                        target=node.name,
                        description="Comprehension inside function (usually fine, check context).",
                        complexity=ComplexityClass.LINEAR,
                        suggestion="Comprehensions are efficient but watch for nested ones.",
                        estimated_impact="low",
                    )
                )
            if isinstance(child, ast.Call):
                self._check_expensive_calls(child, node, issues)

        # Estimate overall complexity
        body_lines = node.end_lineno - node.lineno if node.end_lineno else 0
        optimization_score = self._compute_optimization_score(issues, body_lines)

        return ProfileResult(
            name=node.name,
            type="async function" if isinstance(node, ast.AsyncFunctionDef) else "function",
            line=node.lineno,
            estimated_complexity=complexity,
            issues=tuple(issues),
            optimization_score=optimization_score,
        )

    def _profile_loop(self, node: ast.For) -> ProfileResult | None:
        """Profile a for loop."""
        issues: list[PerformanceIssue] = []

        # Check for range(len(...)) pattern
        if (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
            and node.iter.args
            and isinstance(node.iter.args[0], ast.Call)
            and isinstance(node.iter.args[0].func, ast.Name)
            and node.iter.args[0].func.id == "len"
        ):
            issues.append(
                PerformanceIssue(
                    line=node.lineno,
                    target="loop",
                    description="range(len(...)) pattern. Inefficient for iteration.",
                    complexity=ComplexityClass.LINEAR,
                    suggestion="Use 'enumerate()' or iterate directly over the collection.",
                    estimated_impact="medium",
                )
            )

        return ProfileResult(
            name=f"loop_at_line_{node.lineno}",
            type="loop",
            line=node.lineno,
            estimated_complexity=ComplexityClass.LINEAR,
            issues=tuple(issues),
            optimization_score=10 - len(issues) * 3,
        )

    def _estimate_complexity(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ComplexityClass:
        """Estimate the time complexity of a function."""
        has_loop = False
        has_nested = False
        has_recursion = False

        for child in ast.walk(node):
            if isinstance(child, ast.For) or isinstance(child, ast.While):
                if has_loop:
                    has_nested = True
                has_loop = True

            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == node.name:
                    has_recursion = True

        if has_recursion:
            return ComplexityClass.EXPONENTIAL
        if has_nested:
            return ComplexityClass.QUADRATIC
        if has_loop:
            return ComplexityClass.LINEAR
        return ComplexityClass.CONSTANT

    def _count_nested_loops(self, node: ast.AST, current_depth: int = 0) -> int:
        """Count maximum nested loop depth."""
        if isinstance(node, (ast.For, ast.While)):
            current_depth += 1
            max_child = current_depth
            for child in ast.iter_child_nodes(node):
                child_depth = self._count_nested_loops(child, current_depth)
                if child_depth > max_child:
                    max_child = child_depth
            return max_child
        # Recurse into non-loop nodes to find loops
        max_depth = current_depth
        for child in ast.iter_child_nodes(node):
            child_depth = self._count_nested_loops(child, current_depth)
            if child_depth > max_depth:
                max_depth = child_depth
        return max_depth

    def _check_expensive_calls(
        self,
        call: ast.Call,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        issues: list[PerformanceIssue],
    ) -> None:
        """Check for expensive function calls."""
        if isinstance(call.func, ast.Attribute):
            name = call.func.attr
        elif isinstance(call.func, ast.Name):
            name = call.func.id
        else:
            return

        expensive: dict[str, tuple[str, ComplexityClass, str]] = {
            "deepcopy": ("Deep copy operation is expensive.", ComplexityClass.LINEAR, "medium"),
            "sort": ("Sort operation in a loop may be O(n log n) each iteration.", ComplexityClass.LINEARRITHMIC, "high"),
            "sorted": ("Sort operation may be expensive in hot paths.", ComplexityClass.LINEARRITHMIC, "medium"),
        }

        if name in expensive:
            desc, comp, impact = expensive[name]
            issues.append(
                PerformanceIssue(
                    line=call.lineno,
                    target=func_node.name,
                    description=desc,
                    complexity=comp,
                    suggestion=f"Consider caching or avoiding repeated '{name}' calls.",
                    estimated_impact=impact,
                )
            )

    def _compute_optimization_score(
        self, issues: list[PerformanceIssue], body_lines: int
    ) -> int:
        """Compute an optimization priority score (0-100)."""
        impact_scores = {"high": 30, "medium": 15, "low": 5}
        base = 100
        for issue in issues:
            base -= impact_scores.get(issue.estimated_impact, 10)
        return max(0, base)

    def _compute_summary(self, results: list[ProfileResult]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in results:
            for issue in r.issues:
                key = issue.estimated_impact
                counts[key] = counts.get(key, 0) + 1
        return counts
