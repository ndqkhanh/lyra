"""Tests for RuleRegistry."""

import pytest
from pathlib import Path
from lyra_cli.core.rule_registry import RuleRegistry
from lyra_cli.core.rule_metadata import RuleCategory, RuleSeverity


@pytest.fixture
def rules_dir(tmp_path):
    """Create a temporary rules directory with test rules."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Create immutability-required.md
    immutability_md = rules_dir / "immutability-required.md"
    immutability_md.write_text("""---
name: immutability-required
description: Always create new objects
category: CodingStandards
severity: high
enabled: true
---

# Immutability Required
""")

    # Create minimum-test-coverage.md
    coverage_md = rules_dir / "minimum-test-coverage.md"
    coverage_md.write_text("""---
name: minimum-test-coverage
description: Minimum 80% test coverage
category: Testing
severity: critical
enabled: true
---

# Minimum Test Coverage
""")

    return rules_dir


def test_load_rules(rules_dir):
    """Test loading rules from directory."""
    registry = RuleRegistry([rules_dir])
    registry.load_rules()

    assert len(registry._rules) == 2
    assert "immutability-required" in registry._rules
    assert "minimum-test-coverage" in registry._rules


def test_get_rule(rules_dir):
    """Test getting a rule by name."""
    registry = RuleRegistry([rules_dir])
    registry.load_rules()

    rule = registry.get_rule("immutability-required")
    assert rule is not None
    assert rule.name == "immutability-required"
    assert rule.category == RuleCategory.CODING_STANDARDS


def test_get_rules_by_category(rules_dir):
    """Test getting rules by category."""
    registry = RuleRegistry([rules_dir])
    registry.load_rules()

    coding_rules = registry.get_rules_by_category(RuleCategory.CODING_STANDARDS)
    assert len(coding_rules) == 1
    assert coding_rules[0].name == "immutability-required"

    testing_rules = registry.get_rules_by_category(RuleCategory.TESTING)
    assert len(testing_rules) == 1
    assert testing_rules[0].name == "minimum-test-coverage"


def test_search_rules(rules_dir):
    """Test searching rules."""
    registry = RuleRegistry([rules_dir])
    registry.load_rules()

    results = registry.search_rules("immutability")
    assert len(results) == 1
    assert results[0].name == "immutability-required"


def test_list_rules(rules_dir):
    """Test listing all rules."""
    registry = RuleRegistry([rules_dir])
    registry.load_rules()

    rules = registry.list_rules()
    assert len(rules) == 2
