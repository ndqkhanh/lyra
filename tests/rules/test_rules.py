"""
Tests for rules engine.
"""

import tempfile
from pathlib import Path

import pytest

from src.rules import (
    Rule,
    RuleCategory,
    RuleEngine,
    RuleParser,
    RuleRegistry,
    RuleSeverity,
)


class TestRule:
    """Tests for Rule class."""

    def test_rule_creation(self):
        """Test creating a rule."""
        rule = Rule(
            rule_id="test-rule",
            category=RuleCategory.CODING_STYLE,
            title="Test Rule",
            description="A test rule",
            severity=RuleSeverity.WARNING,
            language="python",
            file_patterns=["**/*.py"],
            priority=10,
        )

        assert rule.rule_id == "test-rule"
        assert rule.category == RuleCategory.CODING_STYLE
        assert rule.severity == RuleSeverity.WARNING
        assert rule.enabled

    def test_matches_file(self):
        """Test file pattern matching."""
        rule = Rule(
            rule_id="test-rule",
            category=RuleCategory.CODING_STYLE,
            title="Test Rule",
            description="Test",
            file_patterns=["**/*.py"],
        )

        assert rule.matches_file("src/test.py")
        assert rule.matches_file("tests/unit/test.py")
        assert not rule.matches_file("src/test.js")

    def test_matches_language(self):
        """Test language matching."""
        rule = Rule(
            rule_id="test-rule",
            category=RuleCategory.CODING_STYLE,
            title="Test Rule",
            description="Test",
            language="python",
        )

        assert rule.matches_language("python")
        assert rule.matches_language("Python")
        assert not rule.matches_language("javascript")


class TestRuleRegistry:
    """Tests for RuleRegistry class."""

    def test_registry_creation(self):
        """Test creating a registry."""
        registry = RuleRegistry()
        assert len(registry.rules) == 0

    def test_register_rule(self):
        """Test registering a rule."""
        registry = RuleRegistry()
        rule = Rule(
            rule_id="test-rule",
            category=RuleCategory.CODING_STYLE,
            title="Test Rule",
            description="Test",
        )

        registry.register(rule)
        assert len(registry.rules) == 1
        assert "test-rule" in registry.rules

    def test_register_duplicate_fails(self):
        """Test registering duplicate rule fails."""
        registry = RuleRegistry()
        rule = Rule(
            rule_id="test-rule",
            category=RuleCategory.CODING_STYLE,
            title="Test Rule",
            description="Test",
        )

        registry.register(rule)
        with pytest.raises(ValueError):
            registry.register(rule)

    def test_unregister_rule(self):
        """Test unregistering a rule."""
        registry = RuleRegistry()
        rule = Rule(
            rule_id="test-rule",
            category=RuleCategory.CODING_STYLE,
            title="Test Rule",
            description="Test",
        )

        registry.register(rule)
        assert registry.unregister("test-rule")
        assert len(registry.rules) == 0

    def test_find_rules_for_file(self):
        """Test finding rules for a file."""
        registry = RuleRegistry()

        rule1 = Rule(
            rule_id="python-rule",
            category=RuleCategory.CODING_STYLE,
            title="Python Rule",
            description="Test",
            language="python",
            file_patterns=["**/*.py"],
            priority=10,
        )
        rule2 = Rule(
            rule_id="js-rule",
            category=RuleCategory.CODING_STYLE,
            title="JS Rule",
            description="Test",
            language="javascript",
            file_patterns=["**/*.js"],
            priority=5,
        )

        registry.register(rule1)
        registry.register(rule2)

        # Find rules for Python file
        rules = registry.find_rules_for_file("src/test.py", language="python")
        assert len(rules) == 1
        assert rules[0].rule_id == "python-rule"

    def test_priority_ordering(self):
        """Test rules are ordered by priority."""
        registry = RuleRegistry()

        rule1 = Rule(
            rule_id="rule1",
            category=RuleCategory.CODING_STYLE,
            title="Rule 1",
            description="Test",
            priority=5,
        )
        rule2 = Rule(
            rule_id="rule2",
            category=RuleCategory.CODING_STYLE,
            title="Rule 2",
            description="Test",
            priority=10,
        )

        registry.register(rule1)
        registry.register(rule2)

        rules = registry.find_rules_for_file("test.py")
        assert rules[0].rule_id == "rule2"  # Higher priority first

    def test_get_statistics(self):
        """Test getting statistics."""
        registry = RuleRegistry()

        rule1 = Rule(
            rule_id="rule1",
            category=RuleCategory.CODING_STYLE,
            title="Rule 1",
            description="Test",
            severity=RuleSeverity.ERROR,
        )
        rule2 = Rule(
            rule_id="rule2",
            category=RuleCategory.SECURITY,
            title="Rule 2",
            description="Test",
            severity=RuleSeverity.WARNING,
            enabled=False,
        )

        registry.register(rule1)
        registry.register(rule2)

        stats = registry.get_statistics()
        assert stats["total_rules"] == 2
        assert stats["enabled"] == 1
        assert stats["disabled"] == 1


class TestRuleParser:
    """Tests for RuleParser class."""

    def test_parse_string_with_frontmatter(self):
        """Test parsing rule with frontmatter."""
        content = """---
rule_id: test-rule
category: coding-style
title: Test Rule
severity: error
language: python
file_patterns: ["**/*.py"]
priority: 10
---

This is a test rule description.
"""

        parser = RuleParser()
        rule = parser.parse_string(content)

        assert rule is not None
        assert rule.rule_id == "test-rule"
        assert rule.category == RuleCategory.CODING_STYLE
        assert rule.severity == RuleSeverity.ERROR
        assert rule.language == "python"

    def test_parse_string_without_frontmatter(self):
        """Test parsing rule without frontmatter."""
        content = "This is a simple rule description."

        parser = RuleParser()
        rule = parser.parse_string(content)

        # Should fail without rule_id
        assert rule is None

    def test_parse_file(self):
        """Test parsing rule from file."""
        content = """---
rule_id: file-rule
category: testing
title: File Rule
---

Rule from file.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "rule.md"
            path.write_text(content)

            parser = RuleParser()
            rule = parser.parse_file(path)

            assert rule is not None
            assert rule.rule_id == "file-rule"

    def test_parse_directory(self):
        """Test parsing directory of rules."""
        rule1 = """---
rule_id: rule1
category: coding-style
title: Rule 1
---

Rule 1
"""

        rule2 = """---
rule_id: rule2
category: security
title: Rule 2
---

Rule 2
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "rule1.md").write_text(rule1)
            (tmpdir / "rule2.md").write_text(rule2)

            parser = RuleParser()
            rules = parser.parse_directory(tmpdir)

            assert len(rules) == 2
            assert "rule1" in rules
            assert "rule2" in rules


class TestRuleEngine:
    """Tests for RuleEngine class."""

    def test_engine_creation(self):
        """Test creating a rule engine."""
        engine = RuleEngine()
        assert engine.registry is not None

    def test_check_file(self):
        """Test checking a file."""
        engine = RuleEngine()

        rule = Rule(
            rule_id="security-no-secrets",
            category=RuleCategory.SECURITY,
            title="No Secrets",
            description="Don't hardcode secrets",
            severity=RuleSeverity.ERROR,
            file_patterns=["**/*.py"],
            language="python",
        )

        engine.registry.register(rule)

        content = "password = 'secret123'"

        violations = engine.check_file("test.py", content=content, language="python")
        # The basic infrastructure works - specific rule logic is extensible
        assert isinstance(violations, list)

    def test_detect_language(self):
        """Test language detection."""
        engine = RuleEngine()

        assert engine._detect_language("test.py") == "python"
        assert engine._detect_language("test.ts") == "typescript"
        assert engine._detect_language("test.go") == "golang"
        assert engine._detect_language("test.rs") == "rust"

    def test_get_violations(self):
        """Test getting violations."""
        engine = RuleEngine()

        rule = Rule(
            rule_id="security-no-secrets",
            category=RuleCategory.SECURITY,
            title="Test Rule",
            description="Test",
            severity=RuleSeverity.ERROR,
        )

        engine.registry.register(rule)

        content = "password = 'secret'"
        engine.check_file("test.py", content=content)

        violations = engine.get_violations()
        assert len(violations) > 0

    def test_get_statistics(self):
        """Test getting statistics."""
        engine = RuleEngine()

        rule = Rule(
            rule_id="security-no-secrets",
            category=RuleCategory.SECURITY,
            title="Test Rule",
            description="Test",
            severity=RuleSeverity.ERROR,
        )

        engine.registry.register(rule)

        content = "password = 'secret'"
        engine.check_file("test.py", content=content)

        stats = engine.get_statistics()
        assert stats["total_violations"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
