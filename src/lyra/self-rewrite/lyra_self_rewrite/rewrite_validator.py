"""Validate rewrites before deployment — syntax, imports, style, and test checks."""

from __future__ import annotations

from dataclasses import dataclass

from .rewrite_generator import GeneratedRewrite


@dataclass(frozen=True)
class ValidationConfig:
    """Configuration governing rewrite validation behaviour."""

    syntax_check: bool = True
    import_check: bool = True
    style_check: bool = True
    test_check: bool = True


@dataclass(frozen=True)
class ValidationIssue:
    """A single issue found during rewrite validation."""

    severity: str
    message: str
    location: tuple[int, int] = (0, 0)
    rule: str = ""


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a single rewrite."""

    rewrite_id: str
    passed: bool
    issues: tuple[ValidationIssue, ...]
    score: float
    recommendations: tuple[str, ...]


class RewriteValidator:
    """Validates generated rewrites for correctness and quality."""

    async def validate(
        self,
        rewrite: GeneratedRewrite,
        config: ValidationConfig,
    ) -> ValidationResult:
        """Run all enabled validation checks on a rewrite."""
        issues: list[ValidationIssue] = []
        total_deduction = 0.0
        recommendations: list[str] = []

        if not rewrite.generated_code:
            issues.append(ValidationIssue(
                severity="error",
                message="Generated code is empty",
                rule="non_empty",
            ))
            total_deduction += 1.0
            recommendations.append("Ensure generated code is non-empty")

        if config.syntax_check:
            syntax_issues, syntax_deduction = _check_syntax(rewrite)
            issues.extend(syntax_issues)
            total_deduction += syntax_deduction
            if syntax_issues:
                recommendations.append("Fix syntax errors in generated code")

        if config.import_check:
            import_issues, import_deduction = _check_imports(rewrite)
            issues.extend(import_issues)
            total_deduction += import_deduction
            if import_issues:
                recommendations.append("Add missing import statements")

        if config.style_check:
            style_issues, style_deduction = _check_style(rewrite)
            issues.extend(style_issues)
            total_deduction += style_deduction
            if style_issues:
                recommendations.append("Fix style issues in generated code")

        if config.test_check:
            test_issues, test_deduction = _check_test_presence(rewrite)
            issues.extend(test_issues)
            total_deduction += test_deduction
            if test_issues:
                recommendations.append("Generated rewrite should include tests")

        base_score = rewrite.confidence
        score = max(0.0, base_score - total_deduction)
        passed = score >= 0.3 and len([i for i in issues if i.severity == "error"]) == 0

        return ValidationResult(
            rewrite_id=rewrite.rewrite_id,
            passed=passed,
            issues=tuple(issues),
            score=score,
            recommendations=tuple(recommendations),
        )

    async def batch_validate(
        self,
        rewrites: tuple[GeneratedRewrite, ...],
    ) -> tuple[ValidationResult, ...]:
        """Validate multiple rewrites in batch with default config."""
        config = ValidationConfig()
        results: list[ValidationResult] = []
        for rewrite in rewrites:
            result = await self.validate(rewrite, config)
            results.append(result)
        return tuple(results)

    @staticmethod
    def get_severity_counts(result: ValidationResult) -> dict[str, int]:
        """Count issues by severity level."""
        counts: dict[str, int] = {}
        for issue in result.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts


def _check_syntax(rewrite: GeneratedRewrite) -> tuple[list[ValidationIssue], float]:
    """Check the rewrite for basic structural syntax."""
    issues: list[ValidationIssue] = []
    deduction = 0.0
    code = rewrite.generated_code

    # Check for comment completeness
    lines = code.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and stripped.count("#") > 3:
            issues.append(ValidationIssue(
                severity="warning",
                message=f"Line {i + 1} has excessive comment markers",
                location=(i + 1, 0),
                rule="comment_quality",
            ))
            deduction += 0.05

    # Check for basic structural completeness
    if code.count("# PoolPattern: ") > 0 and not code.strip().endswith("\n"):
        issues.append(ValidationIssue(
            severity="warning",
            message="Generated code may be truncated",
            rule="structural_completeness",
        ))
        deduction += 0.1

    return issues, deduction


def _check_imports(rewrite: GeneratedRewrite) -> tuple[list[ValidationIssue], float]:
    """Check for missing imports based on code patterns."""
    issues: list[ValidationIssue] = []
    deduction = 0.0
    code = rewrite.generated_code.lower()

    import_keywords = {
        "logger": "import logging",
        "asyncio": "import asyncio",
        "typing": "from typing import",
        "dataclass": "from dataclasses",
        "abc": "from abc import",
    }

    for keyword, needed_import in import_keywords.items():
        if keyword in code and needed_import not in code:
            issues.append(ValidationIssue(
                severity="warning",
                message=f"Code uses '{keyword}' but may be missing '{needed_import}'",
                rule="missing_import",
            ))
            deduction += 0.1
            break  # One warning per rewrite for imports

    return issues, deduction


def _check_style(rewrite: GeneratedRewrite) -> tuple[list[ValidationIssue], float]:
    """Check for basic style issues in the generated code."""
    issues: list[ValidationIssue] = []
    deduction = 0.0
    code = rewrite.generated_code

    lines = code.split("\n")
    for i, line in enumerate(lines):
        if len(line) > 100:
            issues.append(ValidationIssue(
                severity="warning",
                message=f"Line {i + 1} exceeds 100 characters",
                location=(i + 1, 0),
                rule="line_length",
            ))
            deduction += 0.05
            break  # One warning for line length

    return issues, deduction


def _check_test_presence(
    rewrite: GeneratedRewrite,
) -> tuple[list[ValidationIssue], float]:
    """Check if the rewrite indicates testing considerations."""
    issues: list[ValidationIssue] = []
    deduction = 0.0
    code = rewrite.generated_code.lower()

    test_indicators = ["test", "assert", "pytest", "unittest"]
    has_test_content = any(indicator in code for indicator in test_indicators)

    if not has_test_content:
        issues.append(ValidationIssue(
            severity="info",
            message="Generated rewrite does not reference testing constructs",
            rule="test_presence",
        ))
        deduction = 0.1

    return issues, deduction
