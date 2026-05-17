"""Tests for skill metadata."""
import pytest
from lyra_cli.core.skill_metadata import SkillMetadata


def test_skill_metadata_creation():
    """Test creating skill metadata."""
    skill = SkillMetadata(
        name="test-skill",
        description="Test skill description",
        origin="ECC",
        tags=["test", "example"],
        triggers=["test", "example"]
    )

    assert skill.name == "test-skill"
    assert skill.description == "Test skill description"
    assert skill.origin == "ECC"
    assert skill.tags == ["test", "example"]
    assert skill.triggers == ["test", "example"]
    assert skill.codemap is None
    assert skill.file_path is None


def test_skill_metadata_with_optional_fields():
    """Test skill metadata with optional fields."""
    skill = SkillMetadata(
        name="test-skill",
        description="Test description",
        origin="lyra",
        tags=["test"],
        triggers=None,
        codemap="# Codemap content",
        file_path="/path/to/skill.md"
    )

    assert skill.triggers == []  # Should be initialized to empty list
    assert skill.codemap == "# Codemap content"
    assert skill.file_path == "/path/to/skill.md"
