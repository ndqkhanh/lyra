"""Deep tests for src/lyra/rules/rule_registry.py — 85%+ coverage target.

Tests RuleRegistry with complete coverage of register, unregister, query,
enable/disable, clear, and statistics.
"""

from __future__ import annotations

import pytest

from lyra.rules.rule import Rule, RuleCategory, RuleSeverity
from lyra.rules.rule_registry import RuleRegistry


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def empty_registry() -> RuleRegistry:
    return RuleRegistry()


@pytest.fixture
def sample_rule() -> Rule:
    return Rule(
        rule_id="test-rule",
        category=RuleCategory.CODING_STYLE,
        title="Test Rule",
        description="A test rule",
        severity=RuleSeverity.WARNING,
        language="python",
        file_patterns=["**/*.py"],
        priority=10,
    )


@pytest.fixture
def populated_registry(sample_rule: Rule) -> RuleRegistry:
    reg = RuleRegistry()
    reg.register(sample_rule)
    reg.register(Rule(
        rule_id="js-rule",
        category=RuleCategory.CODING_STYLE,
        title="JS Rule",
        description="JavaScript rule",
        severity=RuleSeverity.INFO,
        language="javascript",
        file_patterns=["**/*.js"],
        priority=5,
    ))
    reg.register(Rule(
        rule_id="security-rule",
        category=RuleCategory.SECURITY,
        title="Security Rule",
        description="No secrets",
        severity=RuleSeverity.ERROR,
        language="python",
        file_patterns=["**/*.py"],
        priority=20,
    ))
    reg.register(Rule(
        rule_id="no-lang-rule",
        category=RuleCategory.PATTERNS,
        title="No Language",
        description="Applies to all languages",
        priority=1,
    ))
    return reg


# =========================================================================
# Constructor
# =========================================================================


class TestConstructor:
    def test_empty_initialization(self, empty_registry: RuleRegistry):
        assert len(empty_registry.rules) == 0
        assert empty_registry.get_statistics()["total_rules"] == 0
        for cat in RuleCategory:
            assert empty_registry.list_rules(category=cat) == []


# =========================================================================
# Register
# =========================================================================


class TestRegister:
    def test_register_rule(self, empty_registry: RuleRegistry, sample_rule: Rule):
        empty_registry.register(sample_rule)
        assert len(empty_registry.rules) == 1
        assert empty_registry.get("test-rule") is sample_rule

    def test_register_duplicate_fails(self, empty_registry: RuleRegistry, sample_rule: Rule):
        empty_registry.register(sample_rule)
        with pytest.raises(ValueError, match="already registered"):
            empty_registry.register(sample_rule)

    def test_register_rule_no_language(self, empty_registry: RuleRegistry):
        rule = Rule(
            rule_id="no-lang",
            category=RuleCategory.SECURITY,
            title="No Language",
            description="Test",
        )
        empty_registry.register(rule)
        assert empty_registry.get("no-lang") is rule

    def test_register_multiple_categories(self, empty_registry: RuleRegistry):
        for cat in list(RuleCategory)[:3]:
            empty_registry.register(Rule(
                rule_id=f"rule-{cat.value}",
                category=cat,
                title=f"Test {cat.value}",
                description="Test",
            ))
        assert empty_registry.get_statistics()["total_rules"] == 3

    def test_register_sorts_by_priority(self, empty_registry: RuleRegistry):
        low = Rule(
            rule_id="low", category=RuleCategory.TESTING, title="Low",
            description="Low priority", priority=1,
        )
        high = Rule(
            rule_id="high", category=RuleCategory.TESTING, title="High",
            description="High priority", priority=100,
        )
        empty_registry.register(low)
        empty_registry.register(high)
        rules = empty_registry.list_rules(category=RuleCategory.TESTING)
        assert rules[0].rule_id == "high"
        assert rules[1].rule_id == "low"

    def test_register_updates_language_index(self, empty_registry: RuleRegistry):
        rule = Rule(
            rule_id="py-rule", category=RuleCategory.CODING_STYLE,
            title="Py", description="Python rule",
            language="python",
        )
        empty_registry.register(rule)
        assert rule in empty_registry._rules_by_language.get("python", [])

    def test_register_no_language_skips_lang_index(self, empty_registry: RuleRegistry):
        rule = Rule(
            rule_id="no-lang", category=RuleCategory.CODING_STYLE,
            title="No Lang", description="No language",
        )
        empty_registry.register(rule)
        # Should not create an entry for None
        assert None not in empty_registry._rules_by_language


# =========================================================================
# Unregister
# =========================================================================


class TestUnregister:
    def test_unregister_existing(self, populated_registry: RuleRegistry):
        assert populated_registry.unregister("test-rule") is True
        assert populated_registry.get("test-rule") is None

    def test_unregister_nonexistent(self, populated_registry: RuleRegistry):
        assert populated_registry.unregister("nonexistent") is False

    def test_unregister_removes_from_category(self, populated_registry: RuleRegistry):
        populated_registry.unregister("test-rule")
        rules = populated_registry.list_rules(category=RuleCategory.CODING_STYLE)
        assert all(r.rule_id != "test-rule" for r in rules)

    def test_unregister_removes_from_language(self, populated_registry: RuleRegistry):
        populated_registry.unregister("test-rule")
        rules = populated_registry.list_rules(language="python")
        assert all(r.rule_id != "test-rule" for r in rules)

    def test_unregister_rule_without_language(self, empty_registry: RuleRegistry):
        rule = Rule(
            rule_id="no-lang", category=RuleCategory.PATTERNS,
            title="No Lang", description="Test",
        )
        empty_registry.register(rule)
        assert empty_registry.unregister("no-lang") is True


# =========================================================================
# Get
# =========================================================================


class TestGet:
    def test_get_existing(self, populated_registry: RuleRegistry):
        rule = populated_registry.get("test-rule")
        assert rule is not None
        assert rule.rule_id == "test-rule"

    def test_get_nonexistent(self, populated_registry: RuleRegistry):
        assert populated_registry.get("nonexistent") is None


# =========================================================================
# find_rules_for_file
# =========================================================================


class TestFindRulesForFile:
    def test_no_filters(self, populated_registry: RuleRegistry):
        rules = populated_registry.find_rules_for_file("src/any.py")
        assert len(rules) > 0

    def test_filter_by_language(self, populated_registry: RuleRegistry):
        rules = populated_registry.find_rules_for_file("src/test.py", language="python")
        assert all(r.matches_language("python") for r in rules)

    def test_filter_by_category(self, populated_registry: RuleRegistry):
        rules = populated_registry.find_rules_for_file(
            "src/test.py", category=RuleCategory.CODING_STYLE,
        )
        assert all(r.category == RuleCategory.CODING_STYLE for r in rules)

    def test_filter_by_language_and_category(self, populated_registry: RuleRegistry):
        rules = populated_registry.find_rules_for_file(
            "src/test.py", language="python", category=RuleCategory.SECURITY,
        )
        assert len(rules) == 1
        assert rules[0].rule_id == "security-rule"

    def test_no_matching_file(self, populated_registry: RuleRegistry):
        # "no-lang-rule" has no file_patterns and no language — it matches all files
        rules = populated_registry.find_rules_for_file("src/test.rs", language="rust")
        # Only the universal rule matches
        assert len(rules) == 1
        assert rules[0].rule_id == "no-lang-rule"

    def test_result_sorted_by_priority(self, populated_registry: RuleRegistry):
        rules = populated_registry.find_rules_for_file("src/test.py")
        priorities = [r.priority for r in rules]
        assert priorities == sorted(priorities, reverse=True)


# =========================================================================
# list_rules
# =========================================================================


class TestListRules:
    def test_all_rules(self, populated_registry: RuleRegistry):
        rules = populated_registry.list_rules()
        assert len(rules) == len(populated_registry.rules)

    def test_by_category(self, populated_registry: RuleRegistry):
        rules = populated_registry.list_rules(category=RuleCategory.SECURITY)
        assert len(rules) == 1
        assert rules[0].rule_id == "security-rule"

    def test_by_nonexistent_category(self, empty_registry: RuleRegistry):
        rules = empty_registry.list_rules(category=RuleCategory.AGENTS)
        assert rules == []

    def test_by_language(self, populated_registry: RuleRegistry):
        rules = populated_registry.list_rules(language="python")
        assert len(rules) == 2

    def test_by_nonexistent_language(self, populated_registry: RuleRegistry):
        rules = populated_registry.list_rules(language="rust")
        assert rules == []

    def test_enabled_only(self, populated_registry: RuleRegistry):
        populated_registry.disable("test-rule")
        rules = populated_registry.list_rules(enabled_only=True)
        assert all(r.enabled for r in rules)
        assert "test-rule" not in {r.rule_id for r in rules}

    def test_enabled_only_with_category(self, populated_registry: RuleRegistry):
        populated_registry.disable("test-rule")
        rules = populated_registry.list_rules(
            category=RuleCategory.CODING_STYLE, enabled_only=True,
        )
        assert len(rules) == 1
        assert rules[0].rule_id == "js-rule"

    def test_enabled_only_with_language(self, populated_registry: RuleRegistry):
        populated_registry.disable("test-rule")
        rules = populated_registry.list_rules(
            language="python", enabled_only=True,
        )
        assert len(rules) == 1
        assert rules[0].rule_id == "security-rule"


# =========================================================================
# Enable / Disable
# =========================================================================


class TestEnableDisable:
    def test_enable(self, populated_registry: RuleRegistry):
        populated_registry.disable("test-rule")
        assert not populated_registry.get("test-rule").enabled
        assert populated_registry.enable("test-rule") is True
        assert populated_registry.get("test-rule").enabled is True

    def test_enable_nonexistent(self, populated_registry: RuleRegistry):
        assert populated_registry.enable("nonexistent") is False

    def test_disable(self, populated_registry: RuleRegistry):
        assert populated_registry.get("test-rule").enabled is True
        assert populated_registry.disable("test-rule") is True
        assert populated_registry.get("test-rule").enabled is False

    def test_disable_nonexistent(self, populated_registry: RuleRegistry):
        assert populated_registry.disable("nonexistent") is False


# =========================================================================
# Clear
# =========================================================================


class TestClear:
    def test_clear_removes_all(self, populated_registry: RuleRegistry):
        populated_registry.clear()
        assert len(populated_registry.rules) == 0
        assert populated_registry.get_statistics()["total_rules"] == 0
        for cat in RuleCategory:
            assert populated_registry.list_rules(category=cat) == []

    def test_clear_empty_registry(self, empty_registry: RuleRegistry):
        empty_registry.clear()
        assert len(empty_registry.rules) == 0

    def test_clear_clears_categories(self, populated_registry: RuleRegistry):
        populated_registry.clear()
        for cat in RuleCategory:
            assert populated_registry._rules_by_category[cat] == []

    def test_clear_clears_languages(self, populated_registry: RuleRegistry):
        populated_registry.clear()
        assert populated_registry._rules_by_language == {}


# =========================================================================
# get_statistics
# =========================================================================


class TestGetStatistics:
    def test_statistics_structure(self, populated_registry: RuleRegistry):
        stats = populated_registry.get_statistics()
        assert "total_rules" in stats
        assert "by_category" in stats
        assert "by_language" in stats
        assert "by_severity" in stats
        assert "enabled" in stats
        assert "disabled" in stats

    def test_statistics_counts(self, populated_registry: RuleRegistry):
        stats = populated_registry.get_statistics()
        assert stats["total_rules"] == 4
        assert stats["by_category"]["coding-style"] == 2
        assert stats["by_category"]["security"] == 1
        assert stats["by_category"]["patterns"] == 1
        assert stats["by_language"]["python"] == 2
        assert stats["by_language"]["javascript"] == 1
        assert stats["enabled"] == 4
        assert stats["disabled"] == 0

    def test_statistics_with_disabled_rule(self, populated_registry: RuleRegistry):
        populated_registry.disable("test-rule")
        stats = populated_registry.get_statistics()
        assert stats["enabled"] == 3
        assert stats["disabled"] == 1

    def test_statistics_by_severity(self, populated_registry: RuleRegistry):
        stats = populated_registry.get_statistics()
        assert stats["by_severity"]["warning"] >= 1
        assert stats["by_severity"]["info"] >= 1
        assert stats["by_severity"]["error"] >= 1

    def test_statistics_empty(self, empty_registry: RuleRegistry):
        stats = empty_registry.get_statistics()
        assert stats["total_rules"] == 0
        assert all(v == 0 for v in stats["by_category"].values())
        assert stats["by_language"] == {}
        assert stats["by_severity"]["error"] == 0
        assert stats["enabled"] == 0
        assert stats["disabled"] == 0
