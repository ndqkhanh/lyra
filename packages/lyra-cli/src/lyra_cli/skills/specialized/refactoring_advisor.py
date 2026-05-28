"""
Refactoring Advisor Skill - Analyze code for refactoring opportunities.

Detects:
- Long functions needing extraction
- Large classes needing decomposition
- Complex conditionals needing simplification
- Duplicated code blocks
- Deep nesting

Suggests specific refactorings with before/after code examples.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum


class RefactoringType(StrEnum):
    """Types of refactoring opportunities."""

    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    SIMPLIFY_CONDITIONAL = "simplify_conditional"
    REMOVE_DUPLICATION = "remove_duplication"
    REDUCE_NESTING = "reduce_nesting"
    SPLIT_FUNCTION = "split_function"
    REPLACE_TEMP_WITH_QUERY = "replace_temp_with_query"


@dataclass(frozen=True)
class RefactoringSuggestion:
    """A single refactoring suggestion."""

    type: RefactoringType
    line: int
    target: str
    description: str
    reason: str
    before_code: str
    after_code: str
    complexity_score: int


@dataclass(frozen=True)
class RefactoringReport:
    """Complete refactoring report."""

    file_path: str
    total_lines: int
    suggestions: tuple[RefactoringSuggestion, ...]
    summary: dict[str, int]


class RefactoringAdvisorSkill:
    """Analyze code for refactoring opportunities and suggest improvements."""

    def run(self, input_data: dict) -> dict:
        """Analyze source code for refactoring opportunities.

        Args:
            input_data: Dictionary with keys:
                - source: Source code string to analyze
                - file_path: Optional file path for context (default "unknown")

        Returns:
            Dictionary with refactoring report.
        """
        source = input_data.get("source", "")
        if not source:
            return {"error": "No source code provided", "suggestions": []}

        file_path = input_data.get("file_path", "unknown")
        suggestions: list[RefactoringSuggestion] = []

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "suggestions": []}

        for node in ast.walk(tree):
            self._check_extract_method(node, source, suggestions)
            self._check_simplify_conditional(node, source, suggestions)
            self._check_reduce_nesting(node, source, suggestions)

        self._check_duplication(source, suggestions)
        self._check_extract_class(tree, source, suggestions)

        summary = self._compute_summary(suggestions)
        return RefactoringReport(
            file_path=file_path,
            total_lines=len(source.splitlines()),
            suggestions=tuple(suggestions),
            summary=summary,
        ).__dict__ | {"suggestions": [s.__dict__ for s in suggestions]}

    def _check_extract_method(
        self, node: ast.AST, source: str, suggestions: list[RefactoringSuggestion]
    ) -> None:
        """Flag long functions as extract method candidates."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body_lines = node.end_lineno - node.lineno if node.end_lineno else 0
            if body_lines > 30:
                source_lines = source.splitlines()
                func_source = "\n".join(
                    source_lines[node.lineno - 1 : node.end_lineno]
                )
                suggestions.append(
                    RefactoringSuggestion(
                        type=RefactoringType.EXTRACT_METHOD,
                        line=node.lineno,
                        target=node.name,
                        description=f"Function '{node.name}' is {body_lines} lines long.",
                        reason="Long functions are hard to read, test, and maintain.",
                        before_code=f"def {node.name}(...):\n    ...  # {body_lines} lines",
                        after_code=f"def {node.name}(...):\n    return _inner_operation(...)\n\n"
                        f"def _inner_operation(...):\n    ...  # extracted logic",
                        complexity_score=min(body_lines // 10, 10),
                    )
                )

    def _check_simplify_conditional(
        self, node: ast.AST, source: str, suggestions: list[RefactoringSuggestion]
    ) -> None:
        """Flag complex conditionals."""
        if isinstance(node, ast.If):
            complexity = self._measure_condition_complexity(node.test)
            if complexity > 3:
                source_lines = source.splitlines()
                cond_source = source_lines[node.lineno - 1].strip()
                suggestions.append(
                    RefactoringSuggestion(
                        type=RefactoringType.SIMPLIFY_CONDITIONAL,
                        line=node.lineno,
                        target="conditional",
                        description=f"Complex conditional with {complexity} sub-conditions.",
                        reason="Complex conditionals are error-prone and hard to understand.",
                        before_code=cond_source,
                        after_code=self._generate_simplified_conditional(
                            cond_source, node.lineno, source_lines
                        ),
                        complexity_score=complexity,
                    )
                )

    def _measure_condition_complexity(self, test: ast.expr) -> int:
        """Measure cyclomatic complexity of a conditional expression."""
        if isinstance(test, ast.BoolOp):
            return 1 + sum(
                self._measure_condition_complexity(v) for v in test.values
            )
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            return 1 + self._measure_condition_complexity(test.operand)
        if isinstance(test, ast.Compare):
            return len(test.ops)
        if isinstance(test, ast.Call):
            return 1
        return 0

    def _generate_simplified_conditional(
        self, cond_source: str, line: int, source_lines: list[str]
    ) -> str:
        """Generate simplified conditional suggestion."""
        return (
            "# Extract condition to named variable:\n"
            f"is_valid = {cond_source}\n"
            "if is_valid:\n    ..."
        )

    def _check_reduce_nesting(
        self, node: ast.AST, source: str, suggestions: list[RefactoringSuggestion]
    ) -> None:
        """Flag deeply nested blocks."""
        if not hasattr(node, 'lineno'):
            return
        depth = self._measure_nesting_depth(node, 0)
        if depth > 4:
            suggestions.append(
                RefactoringSuggestion(
                    type=RefactoringType.REDUCE_NESTING,
                    line=node.lineno,
                    target="nesting block",
                    description=f"Deep nesting detected (depth {depth}).",
                    reason="Deep nesting reduces readability and increases complexity.",
                    before_code="if condition:\n    if other:\n        ...  # depth > 4",
                    after_code=(
                        "def _extracted_block(...):\n"
                        "    if not condition:\n"
                        "        return\n"
                        "    if not other:\n"
                        "        return\n"
                        "    ...  # flat logic"
                    ),
                    complexity_score=depth,
                )
            )

    def _measure_nesting_depth(self, node: ast.AST, current_depth: int) -> int:
        """Recursively measure max nesting depth."""
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
            current_depth += 1
        max_depth = current_depth
        for child in ast.iter_child_nodes(node):
            child_depth = self._measure_nesting_depth(child, current_depth)
            if child_depth > max_depth:
                max_depth = child_depth
        return max_depth

    def _check_duplication(self, source: str, suggestions: list[RefactoringSuggestion]) -> None:
        """Detect duplicated code blocks."""
        lines = source.splitlines()
        seen_blocks: dict[str, list[int]] = {}

        i = 0
        while i < len(lines) - 2:
            block = "\n".join(lines[i : i + 3])
            if block.strip():
                if block in seen_blocks:
                    seen_blocks[block].append(i + 1)
                else:
                    seen_blocks[block] = [i + 1]
            i += 1

        for block, occurrences in seen_blocks.items():
            if len(occurrences) >= 2:
                first_line = min(occurrences)
                suggestions.append(
                    RefactoringSuggestion(
                        type=RefactoringType.REMOVE_DUPLICATION,
                        line=first_line,
                        target="duplicate code block",
                        description=f"Duplicate code block found at lines {', '.join(str(o) for o in occurrences)}.",
                        reason="Duplicated code increases maintenance cost and bug surface.",
                        before_code=block,
                        after_code="# Extract to shared function:\n"
                        "def shared_operation(...):\n"
                        f"    {block.split(chr(10))[0] if chr(10) in block else block}",
                        complexity_score=2,
                    )
                )

    def _check_extract_class(
        self, tree: ast.Module, source: str, suggestions: list[RefactoringSuggestion]
    ) -> None:
        """Flag large classes as extract class candidates."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                method_count = sum(
                    1 for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                if method_count > 10:
                    suggestions.append(
                        RefactoringSuggestion(
                            type=RefactoringType.EXTRACT_CLASS,
                            line=node.lineno,
                            target=node.name,
                            description=f"Class '{node.name}' has {method_count} methods.",
                            reason="Large classes violate Single Responsibility Principle.",
                            before_code=f"class {node.name}:\n    ...  # {method_count} methods",
                            after_code=f"class {node.name}Core:\n    ...  # core methods\n\n"
                            f"class {node.name}Extended:\n    ...  # extended methods",
                            complexity_score=min(method_count // 3, 10),
                        )
                    )

    def _compute_summary(self, suggestions: list[RefactoringSuggestion]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in suggestions:
            key = s.type.value
            counts[key] = counts.get(key, 0) + 1
        return counts
