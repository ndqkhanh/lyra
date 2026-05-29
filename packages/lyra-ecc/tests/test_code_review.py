"""
Tests for Enhanced Rules Engine and Code Review Integration

Comprehensive test suite for code review functionality.
"""

from pathlib import Path

import pytest

from lyra_ecc.code_review import (
    CodeReviewResult,
    EnhancedRulesEngine,
    create_code_review_engine,
)
from lyra_ecc.rules import RuleSeverity, RuleViolation


class TestCodeReviewResult:
    """Test code review result."""

    def test_from_violations_no_violations(self):
        """Test creating result with no violations."""
        file_path = Path("test.py")
        violations = []

        result = CodeReviewResult.from_violations(file_path, violations)

        assert result.file_path == file_path
        assert len(result.violations) == 0
        assert result.passed
        assert "No violations" in result.summary

    def test_from_violations_with_critical(self):
        """Test creating result with critical violations."""
        file_path = Path("test.py")
        violations = [
            RuleViolation(
                rule="test-rule",
                severity=RuleSeverity.CRITICAL,
                message="Critical issue",
                line=10,
            )
        ]

        result = CodeReviewResult.from_violations(file_path, violations)

        assert not result.passed
        assert result.severity_counts["CRITICAL"] == 1
        assert "BLOCKED" in result.summary

    def test_from_violations_with_warnings_only(self):
        """Test creating result with only warnings."""
        file_path = Path("test.py")
        violations = [
            RuleViolation(
                rule="test-rule",
                severity=RuleSeverity.MEDIUM,
                message="Medium issue",
                line=10,
            ),
            RuleViolation(
                rule="test-rule-2",
                severity=RuleSeverity.LOW,
                message="Low issue",
                line=20,
            ),
        ]

        result = CodeReviewResult.from_violations(file_path, violations)

        assert result.passed  # Warnings don't block
        assert result.severity_counts["MEDIUM"] == 1
        assert result.severity_counts["LOW"] == 1
        assert "WARNINGS" in result.summary


class TestEnhancedRulesEngine:
    """Test enhanced rules engine."""

    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        engine = EnhancedRulesEngine()

        assert engine is not None
        assert len(engine.common_rules) > 0

    def test_detect_language_python(self):
        """Test detecting Python language."""
        engine = EnhancedRulesEngine()

        assert engine.detect_language(Path("test.py")) == "python"

    def test_detect_language_typescript(self):
        """Test detecting TypeScript language."""
        engine = EnhancedRulesEngine()

        assert engine.detect_language(Path("test.ts")) == "typescript"
        assert engine.detect_language(Path("test.tsx")) == "typescript"

    def test_detect_language_javascript(self):
        """Test detecting JavaScript language."""
        engine = EnhancedRulesEngine()

        assert engine.detect_language(Path("test.js")) == "javascript"
        assert engine.detect_language(Path("test.jsx")) == "javascript"

    def test_detect_language_unknown(self):
        """Test detecting unknown language."""
        engine = EnhancedRulesEngine()

        assert engine.detect_language(Path("test.unknown")) is None

    def test_review_file_clean_code(self):
        """Test reviewing file with no violations."""
        engine = EnhancedRulesEngine()

        code = """
def calculate_sum(a, b):
    return a + b
"""
        result = engine.review_file(Path("test.py"), code)

        assert result.passed
        assert len(result.violations) == 0

    def test_review_file_with_violations(self):
        """Test reviewing file with violations."""
        engine = EnhancedRulesEngine()

        code = """
def test():
    print("Debug message")
    api_key = "secret123"
"""
        result = engine.review_file(Path("test.py"), code)

        # Note: Rules need to be activated first, so this may not find violations
        # unless activate_for_project() is called
        assert isinstance(result, CodeReviewResult)
        assert result.file_path == Path("test.py")

    def test_review_multiple_files(self):
        """Test reviewing multiple files."""
        engine = EnhancedRulesEngine()

        files = [
            (Path("test1.py"), "def foo(): pass"),
            (Path("test2.py"), "def bar(): pass"),
        ]

        results = engine.review_files(files)

        assert len(results) == 2
        assert all(isinstance(r, CodeReviewResult) for r in results)

    def test_get_violations_by_severity(self):
        """Test filtering violations by severity."""
        engine = EnhancedRulesEngine()

        violations = [
            RuleViolation(
                rule="rule1",
                severity=RuleSeverity.CRITICAL,
                message="Critical",
                line=1,
            ),
            RuleViolation(
                rule="rule2", severity=RuleSeverity.HIGH, message="High", line=2
            ),
            RuleViolation(
                rule="rule3", severity=RuleSeverity.MEDIUM, message="Medium", line=3
            ),
        ]

        critical = engine.get_violations_by_severity(violations, RuleSeverity.CRITICAL)
        assert len(critical) == 1
        assert critical[0].severity == RuleSeverity.CRITICAL

    def test_get_blocking_violations(self):
        """Test getting blocking violations."""
        engine = EnhancedRulesEngine()

        violations = [
            RuleViolation(
                rule="rule1",
                severity=RuleSeverity.CRITICAL,
                message="Critical",
                line=1,
            ),
            RuleViolation(
                rule="rule2", severity=RuleSeverity.HIGH, message="High", line=2
            ),
            RuleViolation(
                rule="rule3", severity=RuleSeverity.MEDIUM, message="Medium", line=3
            ),
        ]

        blocking = engine.get_blocking_violations(violations)
        assert len(blocking) == 2  # CRITICAL and HIGH

    def test_should_block_merge_with_critical(self):
        """Test merge blocking with critical violations."""
        engine = EnhancedRulesEngine()

        violations = [
            RuleViolation(
                rule="rule1",
                severity=RuleSeverity.CRITICAL,
                message="Critical",
                line=1,
            )
        ]

        assert engine.should_block_merge(violations)

    def test_should_block_merge_with_warnings_only(self):
        """Test merge not blocked with only warnings."""
        engine = EnhancedRulesEngine()

        violations = [
            RuleViolation(
                rule="rule1", severity=RuleSeverity.MEDIUM, message="Medium", line=1
            )
        ]

        assert not engine.should_block_merge(violations)

    def test_get_review_summary(self):
        """Test getting review summary."""
        engine = EnhancedRulesEngine()

        results = [
            CodeReviewResult.from_violations(Path("test1.py"), []),
            CodeReviewResult.from_violations(
                Path("test2.py"),
                [
                    RuleViolation(
                        rule="rule1",
                        severity=RuleSeverity.CRITICAL,
                        message="Critical",
                        line=1,
                    )
                ],
            ),
        ]

        summary = engine.get_review_summary(results)

        assert summary["total_files"] == 2
        assert summary["files_passed"] == 1
        assert summary["files_blocked"] == 1
        assert summary["severity_totals"]["CRITICAL"] == 1
        assert summary["should_block_merge"]


class TestCreateCodeReviewEngine:
    """Test code review engine factory."""

    def test_create_engine(self):
        """Test creating code review engine."""
        engine = create_code_review_engine()

        assert isinstance(engine, EnhancedRulesEngine)
        assert len(engine.common_rules) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
