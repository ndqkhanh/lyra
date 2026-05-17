"""Tests for RuleValidator."""

import pytest
from pathlib import Path
from lyra_cli.core.rule_validator import RuleValidator, ValidationResult, RuleViolation
from lyra_cli.core.rule_registry import RuleRegistry
from lyra_cli.core.rule_metadata import RuleCategory


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

    return rules_dir


@pytest.fixture
def validator(rules_dir):
    """Create a RuleValidator with loaded rules."""
    registry = RuleRegistry([rules_dir])
    registry.load_rules()
    return RuleValidator(registry)


def test_validate(validator):
    """Test validating against all rules."""
    result = validator.validate()

    assert isinstance(result, ValidationResult)
    assert result.rules_checked == 1


def test_validate_category(validator):
    """Test validating against rules in a specific category."""
    result = validator.validate_category(RuleCategory.CODING_STANDARDS)

    assert isinstance(result, ValidationResult)
    assert result.rules_checked == 1


def test_validation_result_passed(validator):
    """Test validation result when no violations."""
    result = validator.validate()

    assert result.passed is True
    assert len(result.violations) == 0
