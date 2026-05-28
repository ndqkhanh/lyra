"""
Code Reviewer Skill - AST-based code review with severity classification.

Analyzes Python source code for:
- Security issues
- Performance problems
- Code smells
- Style violations

Outputs a structured review report with CRITICAL, HIGH, MEDIUM, LOW severity findings.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    """Severity level for code review findings."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingCategory(StrEnum):
    """Category of code review finding."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    CODE_SMELL = "code_smell"
    STYLE = "style"
    ERROR_PRONE = "error_prone"
    BEST_PRACTICE = "best_practice"


@dataclass(frozen=True)
class ReviewFinding:
    """A single code review finding."""

    line: int
    column: int
    severity: Severity
    category: FindingCategory
    message: str
    suggestion: str
    code: str


@dataclass(frozen=True)
class ReviewReport:
    """Complete code review report."""

    file_path: str
    line_count: int
    findings: tuple[ReviewFinding, ...]
    summary: dict[str, int]

    @property
    def critical_count(self) -> int:
        return self.summary.get("critical", 0)

    @property
    def high_count(self) -> int:
        return self.summary.get("high", 0)

    @property
    def medium_count(self) -> int:
        return self.summary.get("medium", 0)

    @property
    def low_count(self) -> int:
        return self.summary.get("low", 0)


class CodeReviewerSkill:
    """AST-based code review skill with severity classification."""

    def __init__(self) -> None:
        self._findings: list[ReviewFinding] = []

    def run(self, input_data: dict) -> dict:
        """Run code review on the provided source code.

        Args:
            input_data: Dictionary with keys:
                - source: Source code string to review
                - file_path: Optional file path for context (default "unknown")

        Returns:
            Dictionary with review report data.
        """
        source = input_data.get("source", "")
        if not source:
            return {"error": "No source code provided", "findings": [], "summary": {}}

        file_path = input_data.get("file_path", "unknown")
        self._findings.clear()
        self._review_source(source)

        summary = self._compute_summary()
        return ReviewReport(
            file_path=file_path,
            line_count=len(source.splitlines()),
            findings=tuple(self._findings),
            summary=summary,
        ).__dict__ | {"findings": [f.__dict__ for f in self._findings]}

    def _review_source(self, source: str) -> None:
        """Run all review checks on source code."""
        self._check_ast(source)
        self._check_style(source)
        self._check_security_patterns(source)

    def _check_ast(self, source: str) -> None:
        """Parse AST and check for structural issues."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            self._findings.append(
                ReviewFinding(
                    line=getattr(e, "lineno", 0) or 0,
                    column=getattr(e, "offset", 0) or 0,
                    severity=Severity.CRITICAL,
                    category=FindingCategory.ERROR_PRONE,
                    message=f"Syntax error: {e.msg}",
                    suggestion="Fix the syntax error before proceeding with review.",
                    code="SYNTAX_ERROR",
                )
            )
            return

        for node in ast.walk(tree):
            self._check_function_too_long(node)
            self._check_bare_except(node)
            self._check_mutable_defaults(node)
            self._check_debug_import(node)
            self._check_slow_loop(node)

    def _check_function_too_long(self, node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body_lines = node.end_lineno - node.lineno if node.end_lineno else 0
            if body_lines > 50:
                self._findings.append(
                    ReviewFinding(
                        line=node.lineno,
                        column=node.col_offset,
                        severity=Severity.MEDIUM,
                        category=FindingCategory.CODE_SMELL,
                        message=f"Function '{node.name}' is {body_lines} lines long.",
                        suggestion="Consider breaking it into smaller functions (<50 lines).",
                        code="TOO_LONG_FUNCTION",
                    )
                )

    def _check_bare_except(self, node: ast.AST) -> None:
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            self._findings.append(
                ReviewFinding(
                    line=node.lineno,
                    column=node.col_offset,
                    severity=Severity.HIGH,
                    category=FindingCategory.ERROR_PRONE,
                    message="Bare except clause catches all exceptions.",
                    suggestion="Catch specific exceptions instead of using bare 'except:'.",
                    code="BARE_EXCEPT",
                )
            )

    def _check_mutable_defaults(self, node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    self._findings.append(
                        ReviewFinding(
                            line=default.lineno,
                            column=default.col_offset,
                            severity=Severity.HIGH,
                            category=FindingCategory.ERROR_PRONE,
                            message=f"Mutable default argument in '{node.name}'.",
                            suggestion="Use 'None' as default and assign inside the function body.",
                            code="MUTABLE_DEFAULT",
                        )
                    )

    def _check_debug_import(self, node: ast.AST) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in ("pdb", "ipdb", "trace"):
                    self._findings.append(
                        ReviewFinding(
                            line=node.lineno,
                            column=node.col_offset,
                            severity=Severity.MEDIUM,
                            category=FindingCategory.CODE_SMELL,
                            message=f"Debug import '{alias.name}' found in production code.",
                            suggestion="Remove debug imports before committing.",
                            code="DEBUG_IMPORT",
                        )
                    )

    def _check_slow_loop(self, node: ast.AST) -> None:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "append":
                if isinstance(func.value, ast.Name) and func.value.id == "list":
                    return
            # Check for range(len(...)) pattern
            if (
                isinstance(func, ast.Name)
                and func.id == "range"
                and node.args
                and isinstance(node.args[0], ast.Call)
                and isinstance(node.args[0].func, ast.Name)
                and node.args[0].func.id == "len"
            ):
                parent_call = None
                for n in ast.walk(node):
                    if isinstance(n, ast.Call) and n is not node:
                        if isinstance(n.func, ast.Name) and n.func.id == "range":
                            parent_call = n
                if parent_call is None:
                    self._findings.append(
                        ReviewFinding(
                            line=node.lineno,
                            column=node.col_offset,
                            severity=Severity.LOW,
                            category=FindingCategory.PERFORMANCE,
                            message="Use of range(len(...)) pattern detected.",
                            suggestion="Use 'enumerate()' for index-based iteration or iterate directly.",
                            code="RANGE_LEN",
                        )
                    )

    def _check_style(self, source: str) -> None:
        """Check code style issues via regex patterns."""
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()
            if line != stripped:
                self._findings.append(
                    ReviewFinding(
                        line=i,
                        column=len(stripped),
                        severity=Severity.LOW,
                        category=FindingCategory.STYLE,
                        message="Trailing whitespace detected.",
                        suggestion="Remove trailing whitespace.",
                        code="TRAILING_WS",
                    )
                )
            if len(line) > 100:
                self._findings.append(
                    ReviewFinding(
                        line=i,
                        column=100,
                        severity=Severity.LOW,
                        category=FindingCategory.STYLE,
                        message=f"Line too long ({len(line)} > 100 chars).",
                        suggestion="Break the line to stay under 100 characters.",
                        code="LINE_TOO_LONG",
                    )
                )

    def _check_security_patterns(self, source: str) -> None:
        """Check for common security anti-patterns via regex."""
        patterns: list[tuple[str, str, Severity, str]] = [
            (r"eval\s*\(", "Use of eval() allows arbitrary code execution.", Severity.CRITICAL, "EVAL_USAGE"),
            (r"exec\s*\(", "Use of exec() allows arbitrary code execution.", Severity.CRITICAL, "EXEC_USAGE"),
            (r"pickle\.loads?", "Pickle can execute arbitrary code during deserialization.", Severity.CRITICAL, "PICKLE_USAGE"),
            (r"os\.system\s*\(", "subprocess.run() is safer than os.system().", Severity.HIGH, "OS_SYSTEM"),
            (r"subprocess\.call\(.*shell=True", "shell=True enables shell injection attacks.", Severity.CRITICAL, "SHELL_TRUE"),
        ]
        for pattern, message, severity, code in patterns:
            for match in re.finditer(pattern, source):
                line_num = source[: match.start()].count("\n") + 1
                self._findings.append(
                    ReviewFinding(
                        line=line_num,
                        column=match.start() - source[: match.start()].rfind("\n"),
                        severity=severity,
                        category=FindingCategory.SECURITY,
                        message=message,
                        suggestion=f"Replace with a safer alternative. ({code})",
                        code=code,
                    )
                )

    def _compute_summary(self) -> dict[str, int]:
        """Compute finding severity summary."""
        counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in self._findings:
            key = finding.severity.value.lower()
            counts[key] = counts.get(key, 0) + 1
        return counts
