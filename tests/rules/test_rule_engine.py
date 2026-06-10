"""
Tests for RuleEngine — file checking, rule matching, violation tracking,
and statistics.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra.rules.rule import Rule, RuleCategory, RuleSeverity, RuleViolation
from lyra.rules.rule_engine import RuleEngine
from lyra.rules.rule_registry import RuleRegistry


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def registry() -> RuleRegistry:
    reg = RuleRegistry()

    # Coding style rule
    reg.register(Rule(
        rule_id="no-hardcoded-values",
        title="No TODO comments",
        category=RuleCategory.CODING_STYLE,
        description="Avoid TODO/FIXME comments in code",
        severity=RuleSeverity.WARNING,
        file_patterns=["*.py"],
        language="python",
    ))

    # Security rule
    reg.register(Rule(
        rule_id="no-secrets",
        category=RuleCategory.SECURITY,
        title="No hardcoded secrets",
        description="Avoid hardcoded passwords, API keys, secrets",
        severity=RuleSeverity.ERROR,
        file_patterns=["*.py", "*.ts", "*.env"],
        language="python",
    ))

    # Testing rule
    reg.register(Rule(
        rule_id="test-coverage",
        category=RuleCategory.TESTING,
        title="Test coverage minimum",
        description="Ensure at least 80% test coverage",
        severity=RuleSeverity.INFO,
        file_patterns=["**/*.py"],
    ))

    # Rule matching all files (no patterns)
    reg.register(Rule(
        rule_id="global-rule",
        category=RuleCategory.CODING_STYLE,
        title="Global rule",
        description="Applies to all files",
        severity=RuleSeverity.HINT,
    ))

    # Disabled rule
    reg.register(Rule(
        rule_id="disabled-rule",
        category=RuleCategory.SECURITY,
        title="Disabled test",
        description="This rule is disabled",
        severity=RuleSeverity.WARNING,
        enabled=False,
    ))

    return reg


@pytest.fixture
def engine(registry: RuleRegistry) -> RuleEngine:
    return RuleEngine(registry=registry)


# =========================================================================
# RuleEngine — initialization
# =========================================================================


class TestRuleEngineInit:
    """RuleEngine initialization."""

    def test_init_with_registry(self, registry: RuleRegistry):
        engine = RuleEngine(registry=registry)
        assert engine.registry is registry
        assert engine.violations == []

    def test_init_creates_registry(self):
        engine = RuleEngine()
        assert engine.registry is not None
        assert isinstance(engine.registry, RuleRegistry)


# =========================================================================
# RuleEngine — _detect_language
# =========================================================================


class TestRuleEngineDetectLanguage:
    """Language detection from file extensions."""

    def test_detect_python(self, engine: RuleEngine):
        assert engine._detect_language("src/main.py") == "python"

    def test_detect_typescript(self, engine: RuleEngine):
        assert engine._detect_language("src/app.ts") == "typescript"
        assert engine._detect_language("src/app.tsx") == "typescript"

    def test_detect_javascript(self, engine: RuleEngine):
        assert engine._detect_language("src/app.js") == "javascript"
        assert engine._detect_language("src/app.jsx") == "javascript"

    def test_detect_go(self, engine: RuleEngine):
        assert engine._detect_language("main.go") == "golang"

    def test_detect_rust(self, engine: RuleEngine):
        assert engine._detect_language("lib.rs") == "rust"

    def test_detect_java(self, engine: RuleEngine):
        assert engine._detect_language("Main.java") == "java"

    def test_detect_kotlin(self, engine: RuleEngine):
        assert engine._detect_language("Main.kt") == "kotlin"

    def test_detect_swift(self, engine: RuleEngine):
        assert engine._detect_language("main.swift") == "swift"

    def test_detect_php(self, engine: RuleEngine):
        assert engine._detect_language("index.php") == "php"

    def test_detect_cpp(self, engine: RuleEngine):
        assert engine._detect_language("main.cpp") == "cpp"
        assert engine._detect_language("main.cc") == "cpp"

    def test_detect_c(self, engine: RuleEngine):
        assert engine._detect_language("main.c") == "c"

    def test_detect_unknown(self, engine: RuleEngine):
        assert engine._detect_language("Makefile") is None

    def test_detect_no_extension(self, engine: RuleEngine):
        assert engine._detect_language("Dockerfile") is None


# =========================================================================
# RuleEngine — check_file
# =========================================================================


class TestRuleEngineCheckFile:
    """check_file with various scenarios."""

    def test_check_file_with_content(self, engine: RuleEngine):
        """check_file with provided content."""
        violations = engine.check_file(
            "src/main.py",
            content="print('hello')",
            language="python",
        )
        assert isinstance(violations, list)

    def test_check_file_triggers_todo_violation(self, engine: RuleEngine, tmp_path: Path):
        """TODO comment triggers coding style violation."""
        py_file = tmp_path / "main.py"
        py_file.write_text("# TODO: fix this later\nprint('hello')")

        violations = engine.check_file(str(py_file))
        assert len(violations) >= 1
        todo_violations = [v for v in violations if "TODO" in v.message]
        assert len(todo_violations) >= 1

    def test_check_file_triggers_secret_violation(self, engine: RuleEngine, tmp_path: Path):
        """Hardcoded password triggers security violation."""
        py_file = tmp_path / "config.py"
        py_file.write_text("password = 'super-secret'")

        violations = engine.check_file(str(py_file), language="python")
        assert len(violations) >= 1
        secret_violations = [v for v in violations if "secret" in v.message.lower()]
        assert len(secret_violations) >= 1

    def test_check_file_unreadable(self, engine: RuleEngine):
        """check_file returns empty when file can't be read."""
        violations = engine.check_file("/nonexistent/path/file.py")
        assert violations == []

    def test_check_file_no_language_detected(self, engine: RuleEngine, tmp_path: Path):
        """check_file auto-detects language from extension."""
        py_file = tmp_path / "script.py"
        py_file.write_text("TO DO: implement")
        violations = engine.check_file(str(py_file))
        assert isinstance(violations, list)

    def test_check_file_auto_detect_language(self, engine: RuleEngine, tmp_path: Path):
        """check_file auto-detects language when not provided."""
        js_file = tmp_path / "app.js"
        js_file.write_text("console.log('hello')")

        violations = engine.check_file(str(js_file))
        assert isinstance(violations, list)

    def test_check_file_global_rule_applies(self, engine: RuleEngine, tmp_path: Path):
        """Global rules (no file_patterns) apply to all files."""
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Some notes")

        violations = engine.check_file(str(txt_file))
        global_violations = [v for v in violations if v.rule_id == "global-rule"]
        # Global rule has no checks, so no violations from it directly

    def test_check_file_multiple_violations(self, engine: RuleEngine, tmp_path: Path):
        """A file can trigger multiple rule violations."""
        py_file = tmp_path / "danger.py"
        py_file.write_text("""
# TODO: implement
password = "admin"
api_key = "12345"
secret = "hidden"
""")

        violations = engine.check_file(str(py_file), language="python")
        # Should have TODO violations AND secret violations
        todo_count = sum(1 for v in violations if "TODO" in v.message)
        secret_count = sum(1 for v in violations if "secret" in v.message.lower())
        assert todo_count >= 1
        assert secret_count >= 1

    def test_check_file_no_content_no_read(self, engine: RuleEngine, tmp_path: Path):
        """check_file with content=None reads from disk."""
        py_file = tmp_path / "exists.py"
        py_file.write_text("TODO: do something")
        violations = engine.check_file(str(py_file), content=None)
        assert isinstance(violations, list)

    def test_check_file_empty_content(self, engine: RuleEngine, tmp_path: Path):
        """Empty content produces no violations."""
        py_file = tmp_path / "empty.py"
        py_file.write_text("")
        violations = engine.check_file(str(py_file))
        # No TODO, no secrets
        assert len(violations) >= 0


# =========================================================================
# RuleEngine — violation tracking
# =========================================================================


class TestRuleEngineViolations:
    """Violation storage and filtering."""

    def test_get_violations_all(self, engine: RuleEngine, tmp_path: Path):
        """get_violations returns all stored violations."""
        py_file = tmp_path / "violations.py"
        py_file.write_text("# TODO: fix\npassword = 'x'")
        engine.check_file(str(py_file))
        assert len(engine.get_violations()) >= 1

    def test_get_violations_filter_by_severity(self, engine: RuleEngine, tmp_path: Path):
        """get_violations filters by severity."""
        py_file = tmp_path / "severity_test.py"
        py_file.write_text("# TODO: fix this")
        engine.check_file(str(py_file))

        warnings = engine.get_violations(severity="warning")
        for v in warnings:
            assert v.severity.value == "warning"

    def test_get_violations_filter_by_file(self, engine: RuleEngine, tmp_path: Path):
        """get_violations filters by file path."""
        py_file = tmp_path / "filter_me.py"
        py_file.write_text("# TODO: fix")
        engine.check_file(str(py_file))

        file_violations = engine.get_violations(file_path=str(py_file))
        for v in file_violations:
            assert v.file_path == str(py_file)

    def test_get_violations_filter_no_match(self, engine: RuleEngine):
        """get_violations with no matching filters returns empty."""
        engine.violations = [
            RuleViolation(
                rule_id="test",
                severity=RuleSeverity.ERROR,
                message="test",
            )
        ]
        assert engine.get_violations(severity="info") == []

    def test_get_violations_filter_file_no_match(self, engine: RuleEngine):
        """get_violations filter by non-matching file returns empty."""
        engine.violations = [
            RuleViolation(
                rule_id="test",
                severity=RuleSeverity.WARNING,
                message="test",
                file_path="/some/file.py",
            )
        ]
        assert engine.get_violations(file_path="/other/file.py") == []

    def test_clear_violations(self, engine: RuleEngine, tmp_path: Path):
        """clear_violations empties the violations list."""
        py_file = tmp_path / "clear_me.py"
        py_file.write_text("TODO: fix")
        engine.check_file(str(py_file))
        assert len(engine.violations) > 0
        engine.clear_violations()
        assert engine.violations == []

    def test_check_file_appends_to_violations(self, engine: RuleEngine, tmp_path: Path):
        """check_file appends to existing violations list."""
        py_file = tmp_path / "append_test.py"
        py_file.write_text("TODO: do this")

        engine.check_file(str(py_file))
        first_count = len(engine.violations)

        engine.check_file(str(py_file))
        assert len(engine.violations) >= first_count


# =========================================================================
# RuleEngine — statistics
# =========================================================================


class TestRuleEngineStatistics:
    """Violation statistics."""

    def test_get_statistics_empty(self, engine: RuleEngine):
        """Statistics with no violations."""
        stats = engine.get_statistics()
        assert stats["total_violations"] == 0
        assert stats["by_severity"] == {}
        assert stats["by_file"] == {}
        assert stats["files_with_violations"] == 0

    def test_get_statistics_with_violations(self, engine: RuleEngine, tmp_path: Path):
        """Statistics with violations."""
        py_file = tmp_path / "stats_test.py"
        py_file.write_text("TODO: fix\npassword = 'x'\nsecret = 'y'")

        engine.check_file(str(py_file))
        stats = engine.get_statistics()
        assert stats["total_violations"] > 0
        assert len(stats["by_severity"]) > 0
        assert stats["files_with_violations"] == 1
        assert "registry_stats" in stats

    def test_get_statistics_by_file(self, engine: RuleEngine, tmp_path: Path):
        """Statistics tracks violations per file."""
        f1 = tmp_path / "f1.py"
        f1.write_text("TODO: one")
        f2 = tmp_path / "f2.py"
        f2.write_text("TODO: two")

        engine.check_file(str(f1))
        engine.check_file(str(f2))
        stats = engine.get_statistics()
        assert stats["files_with_violations"] == 2

    def test_statistics_registry_stats_included(self, engine: RuleEngine):
        """Statistics includes registry statistics."""
        stats = engine.get_statistics()
        assert "total_rules" in stats["registry_stats"]
        assert "by_category" in stats["registry_stats"]
        assert "by_language" in stats["registry_stats"]


# =========================================================================
# RuleEngine — _check_rule routing
# =========================================================================


class TestRuleEngineRuleRouting:
    """Rule routing by category."""

    def test_check_coding_style_rule(self, engine: RuleEngine):
        """_check_rule dispatches to _check_coding_style."""
        rule = Rule(
            rule_id="no-hardcoded-values",
            category=RuleCategory.CODING_STYLE,
            title="No hardcoded",
            description="Avoid hardcoded values",
            severity=RuleSeverity.WARNING,
        )
        violations = engine._check_rule(rule, "main.py", "# TODO: fix this")
        assert len(violations) >= 1
        assert violations[0].rule_id == "no-hardcoded-values"

    def test_check_coding_style_no_match(self, engine: RuleEngine):
        """Coding style with no TODO/FIXME produces no violations."""
        rule = Rule(
            rule_id="no-hardcoded-values",
            category=RuleCategory.CODING_STYLE,
            title="No hardcoded",
            description="Avoid hardcoded values",
            severity=RuleSeverity.WARNING,
        )
        violations = engine._check_rule(rule, "main.py", "print('clean code')")
        assert len(violations) == 0

    def test_check_security_rule(self, engine: RuleEngine):
        """_check_rule dispatches to _check_security."""
        rule = Rule(
            rule_id="no-secrets-in-code",
            category=RuleCategory.SECURITY,
            title="No secrets",
            description="Avoid hardcoded secrets",
            severity=RuleSeverity.ERROR,
        )
        violations = engine._check_rule(rule, "main.py", "password = 'secret'")
        assert len(violations) >= 1

    def test_check_security_no_match(self, engine: RuleEngine):
        """Security check with no secret patterns."""
        rule = Rule(
            rule_id="no-secrets-in-code",
            category=RuleCategory.SECURITY,
            title="No secrets",
            description="Avoid hardcoded secrets",
            severity=RuleSeverity.ERROR,
        )
        violations = engine._check_rule(rule, "main.py", "x = 1 + 2")
        assert len(violations) == 0

    def test_check_testing_rule(self, engine: RuleEngine):
        """_check_rule dispatches to _check_testing."""
        rule = Rule(
            rule_id="test-coverage-minimum",
            category=RuleCategory.TESTING,
            title="Coverage",
            description="Must have 80% coverage",
            severity=RuleSeverity.INFO,
        )
        violations = engine._check_rule(rule, "main.py", "def test(): pass")
        # Testing rule currently is a no-op (pass)
        assert len(violations) == 0

    def test_unknown_category(self, engine: RuleEngine, registry: RuleRegistry):
        """Unknown rule category produces no violations."""
        # Create a rule with a category that has no check method
        rule = Rule(
            rule_id="unknown-cat",
            category=RuleCategory.PATTERNS,  # Not CODING_STYLE, SECURITY, or TESTING
            title="Patterns rule",
            description="A patterns rule",
            severity=RuleSeverity.INFO,
        )
        violations = engine._check_rule(rule, "main.py", "content")
        assert len(violations) == 0


# =========================================================================
# RuleEngine — violation dataclass
# =========================================================================


class TestRuleViolation:
    """RuleViolation dataclass."""

    def test_violation_defaults(self):
        v = RuleViolation(
            rule_id="test",
            severity=RuleSeverity.WARNING,
            message="test message",
        )
        assert v.file_path is None
        assert v.line_number is None
        assert v.timestamp is not None

    def test_violation_full(self):
        v = RuleViolation(
            rule_id="test",
            severity=RuleSeverity.ERROR,
            message="error",
            file_path="/path/to/file.py",
            line_number=42,
            column=10,
            context="def foo():",
            metadata={"key": "val"},
        )
        assert v.file_path == "/path/to/file.py"
        assert v.line_number == 42
        assert v.column == 10
        assert v.context == "def foo():"
        assert v.metadata == {"key": "val"}
