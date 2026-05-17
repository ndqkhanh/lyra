"""Tests for RuleMetadata."""

import pytest
from lyra_cli.core.rule_metadata import RuleMetadata, RuleCategory, RuleSeverity


def test_rule_metadata_creation():
    """Test creating a RuleMetadata instance."""
    rule = RuleMetadata(
        name="test-rule",
        description="Test rule description",
        category=RuleCategory.CODING_STANDARDS,
        severity=RuleSeverity.HIGH
    )
    assert rule.name == "test-rule"
    assert rule.description == "Test rule description"
    assert rule.category == RuleCategory.CODING_STANDARDS
    assert rule.severity == RuleSeverity.HIGH
    assert rule.enabled is True
    assert rule.file_path is None


def test_rule_metadata_disabled():
    """Test creating a disabled rule."""
    rule = RuleMetadata(
        name="disabled-rule",
        description="Disabled rule",
        category=RuleCategory.SECURITY,
        severity=RuleSeverity.CRITICAL,
        enabled=False
    )
    assert rule.enabled is False


def test_rule_metadata_with_file_path():
    """Test RuleMetadata with file path."""
    rule = RuleMetadata(
        name="test-rule",
        description="Test description",
        category=RuleCategory.TESTING,
        severity=RuleSeverity.MEDIUM,
        file_path="/path/to/rule.md"
    )
    assert rule.file_path == "/path/to/rule.md"
