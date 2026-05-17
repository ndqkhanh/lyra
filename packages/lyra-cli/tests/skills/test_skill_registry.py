"""Tests for skill registry."""
import pytest
from pathlib import Path
from lyra_cli.core.skill_registry import SkillRegistry
from lyra_cli.core.skill_metadata import SkillMetadata


@pytest.fixture
def temp_skill_dir(tmp_path):
    """Create temporary skill directory with test skills."""
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()

    # Create test skill
    test_skill_dir = skill_dir / "test-skill"
    test_skill_dir.mkdir()

    skill_file = test_skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: test-skill
description: Test skill for testing
origin: test
tags: [test, example]
triggers: [test, example]
---

# Test Skill

This is a test skill.
""")

    return skill_dir


def test_skill_registry_initialization():
    """Test skill registry initialization."""
    registry = SkillRegistry()
    assert registry.skill_dirs == []
    assert registry._skills == {}


def test_skill_registry_with_dirs():
    """Test skill registry with directories."""
    dirs = [Path("/path/to/skills")]
    registry = SkillRegistry(skill_dirs=dirs)
    assert registry.skill_dirs == dirs


def test_load_skills(temp_skill_dir):
    """Test loading skills from directory."""
    registry = SkillRegistry(skill_dirs=[temp_skill_dir])
    skills = registry.load_skills()

    assert len(skills) == 1
    assert "test-skill" in skills

    skill = skills["test-skill"]
    assert skill.name == "test-skill"
    assert skill.description == "Test skill for testing"
    assert skill.origin == "test"
    assert skill.tags == ["test", "example"]
    assert skill.triggers == ["test", "example"]


def test_get_skill(temp_skill_dir):
    """Test getting skill by name."""
    registry = SkillRegistry(skill_dirs=[temp_skill_dir])
    registry.load_skills()

    skill = registry.get_skill("test-skill")
    assert skill is not None
    assert skill.name == "test-skill"

    missing = registry.get_skill("nonexistent")
    assert missing is None


def test_search_skills(temp_skill_dir):
    """Test searching skills."""
    registry = SkillRegistry(skill_dirs=[temp_skill_dir])
    registry.load_skills()

    # Search by name
    results = registry.search_skills("test")
    assert len(results) == 1
    assert results[0].name == "test-skill"

    # Search by description
    results = registry.search_skills("testing")
    assert len(results) == 1

    # Search by tag
    results = registry.search_skills("example")
    assert len(results) == 1

    # No results
    results = registry.search_skills("nonexistent")
    assert len(results) == 0


def test_get_by_trigger(temp_skill_dir):
    """Test getting skills by trigger keyword."""
    registry = SkillRegistry(skill_dirs=[temp_skill_dir])
    registry.load_skills()

    results = registry.get_by_trigger("test")
    assert len(results) == 1
    assert results[0].name == "test-skill"

    results = registry.get_by_trigger("example")
    assert len(results) == 1

    results = registry.get_by_trigger("nonexistent")
    assert len(results) == 0


def test_list_skills(temp_skill_dir):
    """Test listing all skills."""
    registry = SkillRegistry(skill_dirs=[temp_skill_dir])
    registry.load_skills()

    skills = registry.list_skills()
    assert len(skills) == 1
    assert skills[0].name == "test-skill"
