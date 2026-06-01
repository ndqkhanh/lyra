"""Backend Engineer Skill — API design, database optimization, and service architecture.

Analyzes backend code for:
- RESTful API design patterns
- Database query optimization
- Caching strategies
- Service scalability patterns
- Error handling and logging
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class BackendSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BackendCategory(StrEnum):
    API_DESIGN = "api_design"
    DATABASE = "database"
    PERFORMANCE = "performance"
    SECURITY = "security"
    SCALABILITY = "scalability"


@dataclass(frozen=True)
class BackendIssue:
    line: int
    category: BackendCategory
    severity: BackendSeverity
    message: str
    suggestion: str
    code_snippet: str


@dataclass(frozen=True)
class BackendReport:
    file_path: str
    issues: tuple[BackendIssue, ...]
    score: int
    summary: dict[str, int]


class BackendEngineerSkill:
    """Analyzes backend code for API design, database, and scalability issues."""

    _PATTERNS = [
        # Database anti-patterns
        (
            r"SELECT\s+\*\s+FROM",
            BackendCategory.DATABASE,
            BackendSeverity.HIGH,
            "SELECT * queries fetch unnecessary columns",
            "Specify only required columns in SELECT statements",
        ),
        (
            r"\.all\(\)\s*\[",
            BackendCategory.DATABASE,
            BackendSeverity.CRITICAL,
            "Loading all records then filtering in Python — N+1 query pattern",
            "Use database-level filtering with .filter() or WHERE clauses",
        ),
        (
            r"for\s+\w+\s+in\s+\w+\.all\(\):",
            BackendCategory.PERFORMANCE,
            BackendSeverity.HIGH,
            "Iterating over .all() without pagination",
            "Use pagination or batch processing for large datasets",
        ),
        # API design issues
        (
            r"@app\.route\(['\"].*['\"],\s*methods=\[['\"]GET['\"],\s*['\"]POST['\"]\]",
            BackendCategory.API_DESIGN,
            BackendSeverity.MEDIUM,
            "Single endpoint handling multiple HTTP methods",
            "Separate GET and POST into distinct endpoints for clarity",
        ),
        (
            r"return\s+\{[^}]*\}\s*,\s*200",
            BackendCategory.API_DESIGN,
            BackendSeverity.LOW,
            "Explicit 200 status code is redundant",
            "200 is the default; only specify non-2xx status codes",
        ),
        # Security issues
        (
            r"password\s*=\s*request\.(form|json|args)\[",
            BackendCategory.SECURITY,
            BackendSeverity.CRITICAL,
            "Password transmitted without validation or hashing",
            "Hash passwords with bcrypt/argon2 before storage",
        ),
        (
            r"\.execute\([f\"][^\"]*\{[^}]*\}",
            BackendCategory.SECURITY,
            BackendSeverity.CRITICAL,
            "SQL injection vulnerability via f-string",
            "Use parameterized queries or ORM methods",
        ),
        # Caching and performance
        (
            r"@cache\.cached\(timeout=0\)",
            BackendCategory.PERFORMANCE,
            BackendSeverity.MEDIUM,
            "Cache timeout set to 0 disables caching",
            "Set appropriate cache TTL based on data volatility",
        ),
        (
            r"time\.sleep\(",
            BackendCategory.SCALABILITY,
            BackendSeverity.HIGH,
            "Blocking sleep in request handler",
            "Use async/await or background tasks for delays",
        ),
    ]

    def __init__(self) -> None:
        self._issues: list[BackendIssue] = []

    def run(self, input_data: dict) -> dict:
        """Run backend code analysis.

        Args:
            input_data: Dictionary with keys:
                - source: Source code string to analyze
                - file_path: Optional file path for context (default "unknown")
                - framework: Optional framework name (flask, fastapi, django)

        Returns:
            Dictionary with analysis report data.
        """
        source = input_data.get("source", "")
        if not source:
            return {"error": "No source code provided", "issues": [], "summary": {}}

        file_path = input_data.get("file_path", "unknown")
        framework = input_data.get("framework", "unknown")
        self._issues.clear()

        # Run pattern checks
        for pattern, category, severity, message, suggestion in self._PATTERNS:
            for match in re.finditer(pattern, source, re.IGNORECASE):
                line_num = source[: match.start()].count("\n") + 1
                snippet = source.splitlines()[line_num - 1].strip()[:80]
                self._issues.append(
                    BackendIssue(
                        line=line_num,
                        category=category,
                        severity=severity,
                        message=message,
                        suggestion=suggestion,
                        code_snippet=snippet,
                    )
                )

        # Check for missing error handling
        has_try_except = "try:" in source and "except" in source
        has_error_handler = "@app.errorhandler" in source or "@exception_handler" in source
        if not has_try_except and not has_error_handler:
            self._issues.append(
                BackendIssue(
                    line=0,
                    category=BackendCategory.API_DESIGN,
                    severity=BackendSeverity.HIGH,
                    message="No error handling detected",
                    suggestion="Add try-except blocks and global error handlers",
                    code_snippet="",
                )
            )

        # Check for logging
        has_logging = "logging." in source or "logger." in source
        if not has_logging:
            self._issues.append(
                BackendIssue(
                    line=0,
                    category=BackendCategory.API_DESIGN,
                    severity=BackendSeverity.MEDIUM,
                    message="No logging detected",
                    suggestion="Add structured logging for debugging and monitoring",
                    code_snippet="",
                )
            )

        summary = self._compute_summary()
        score = self._compute_score()

        return BackendReport(
            file_path=file_path,
            issues=tuple(self._issues),
            score=score,
            summary=summary,
        ).__dict__ | {
            "issues": [i.__dict__ for i in self._issues],
            "framework": framework,
        }

    def _compute_summary(self) -> dict[str, int]:
        """Compute issue severity summary."""
        counts: dict[str, int] = {}
        for issue in self._issues:
            key = issue.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _compute_score(self) -> int:
        """Compute overall code quality score (0-100)."""
        return max(
            0,
            100
            - len([i for i in self._issues if i.severity == BackendSeverity.CRITICAL]) * 25
            - len([i for i in self._issues if i.severity == BackendSeverity.HIGH]) * 15
            - len([i for i in self._issues if i.severity == BackendSeverity.MEDIUM]) * 8
            - len([i for i in self._issues if i.severity == BackendSeverity.LOW]) * 3,
        )
