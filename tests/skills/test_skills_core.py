"""Tests for skills system."""
import pytest
from pathlib import Path
import tempfile
import shutil

from lyra_cli.core.skill_metadata import SkillMetadata
from lyra_cli.core.skill_registry import SkillRegistry
from lyra_cli.core.skill_loader import SkillLoader


@pytest.fixture
def temp_skill_dir():
    """Create temporary skill directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_skill(temp_skill_dir):
    """Create sample skill file."""
    skill_dir = temp_skill_dir / "test-skill"
    skill_dir.mkdir()

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: test-skill
description: A test skill
origin: test
tags:
  - testing
  - example
triggers:
  - test
  - example
---

# Test Skill

This is a test skill for testing purposes.

## Usage

Use this skill for testing.
""")

    return skill_file


def test_skill_metadata_creation():
    """Test SkillMetadata creation."""
    metadata = SkillMetadata(
        name="test",
        description="Test skill",
        origin="test",
        tags=["test"],
    )

    assert metadata.name == "test"
    assert metadata.description == "Test skill"
    assert metadata.origin == "test"
    assert metadata.tags == ["test"]
    assert metadata.triggers == []


def test_skill_metadata_with_triggers():
    """Test SkillMetadata with triggers."""
    metadata = SkillMetadata(
        name="test",
        description="Test skill",
        origin="test",
        tags=["test"],
        triggers=["keyword1", "keyword2"],
    )

    assert metadata.triggers == ["keyword1", "keyword2"]


def test_skill_registry_initialization():
    """Test SkillRegistry initialization."""
    registry = SkillRegistry()

    assert registry.skill_dirs == []
    assert registry._skills == {}


def test_skill_registry_with_dirs(temp_skill_dir):
    """Test SkillRegistry with directories."""
    registry = SkillRegistry(skill_dirs=[temp_skill_dir])

    assert len(registry.skill_dirs) == 1
    assert registry.skill_dirs[0] == temp_skill_dir


def test_load_skills_empty_dir(temp_skill_dir):
    """Test loading skills from empty directory."""
    registry = SkillRegistry(skill_dirs=[temp_skill_dir])
    skills = registry.load_skills()

    assert len(skills) == 0


def test_load_skills_with_sample(temp_skill_dir, sample_skill):
    """Test loading skills with sample skill."""
    registry = SkillRegistry(skill_dirs=[temp_skill_dir])
    skills = registry.load_skills()

    assert len(skills) == 1
    assert "test-skill" in skills

    skill = skills["test-skill"]
    assert skill.name == "test-skill"
    assert skill.description == "A test skill"
    assert skill.origin == "test"
    assert "testing" in skill.tags
    assert "example" in skill.tags
    assert "test" in skill.triggers
    assert "example" in skill.triggers


def test_load_skills_nonexistent_dir():
    """Test loading skills from nonexistent directory."""
    nonexistent = Path("/nonexistent/path")
    registry = SkillRegistry(skill_dirs=[nonexistent])
    skills = registry.load_skills()

    assert len(skills) == 0


def test_load_skills_multiple_dirs(temp_skill_dir, sample_skill):
    """Test loading skills from multiple directories."""
    # Create second skill directory
    temp_dir2 = Path(tempfile.mkdtemp())
    skill_dir2 = temp_dir2 / "skill2"
    skill_dir2.mkdir()

    skill_file2 = skill_dir2 / "SKILL.md"
    skill_file2.write_text("""---
name: skill2
description: Second skill
origin: test
tags:
  - test2
---

# Skill 2
""")

    try:
        registry = SkillRegistry(skill_dirs=[temp_skill_dir, temp_dir2])
        skills = registry.load_skills()

        assert len(skills) == 2
        assert "test-skill" in skills
        assert "skill2" in skills
    finally:
        shutil.rmtree(temp_dir2)


def test_skill_loader_load_content(sample_skill):
    """Test SkillLoader loading content."""
    loader = SkillLoader()

    metadata = SkillMetadata(
        name="test",
        description="Test",
        origin="test",
        tags=["test"],
        file_path=str(sample_skill),
    )

    content = loader.load_skill_content(metadata)

    assert "Test Skill" in content
    assert "Usage" in content


def test_skill_loader_load_nonexistent():
    """Test SkillLoader with nonexistent file."""
    loader = SkillLoader()

    metadata = SkillMetadata(
        name="test",
        description="Test",
        origin="test",
        tags=["test"],
        file_path="/nonexistent/file.md",
    )

    content = loader.load_skill_content(metadata)

    assert content == ""


def test_skill_loader_no_file_path():
    """Test SkillLoader with no file path."""
    loader = SkillLoader()

    metadata = SkillMetadata(
        name="test",
        description="Test",
        origin="test",
        tags=["test"],
    )

    content = loader.load_skill_content(metadata)

    assert content == ""


def test_parse_skill_file_invalid_format(temp_skill_dir):
    """Test parsing skill file with invalid format."""
    skill_dir = temp_skill_dir / "invalid-skill"
    skill_dir.mkdir()

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Invalid Skill\n\nNo frontmatter")

    registry = SkillRegistry(skill_dirs=[temp_skill_dir])
    skills = registry.load_skills()

    assert len(skills) == 0


def test_parse_skill_file_incomplete_frontmatter(temp_skill_dir):
    """Test parsing skill file with incomplete frontmatter."""
    skill_dir = temp_skill_dir / "incomplete-skill"
    skill_dir.mkdir()

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: incomplete\n")

    registry = SkillRegistry(skill_dirs=[temp_skill_dir])
    skills = registry.load_skills()

    # Should handle gracefully
    assert len(skills) == 0


def test_skill_registry_reload(temp_skill_dir, sample_skill):
    """Test reloading skills."""
    registry = SkillRegistry(skill_dirs=[temp_skill_dir])

    # First load
    skills1 = registry.load_skills()
    assert len(skills1) == 1

    # Add another skill
    skill_dir2 = temp_skill_dir / "skill2"
    skill_dir2.mkdir()
    skill_file2 = skill_dir2 / "SKILL.md"
    skill_file2.write_text("""---
name: skill2
description: Second skill
origin: test
tags:
  - test
---

# Skill 2
""")

    # Reload
    skills2 = registry.load_skills()
    assert len(skills2) == 2
    assert "test-skill" in skills2
    assert "skill2" in skills2


def test_skill_metadata_codemap():
    """Test SkillMetadata with codemap."""
    metadata = SkillMetadata(
        name="test",
        description="Test",
        origin="test",
        tags=["test"],
        codemap="test codemap",
    )

    assert metadata.codemap == "test codemap"


def test_generate_codemap():
    """Test codemap generation."""
    loader = SkillLoader()

    # Currently returns None (not implemented)
    codemap = loader.generate_codemap("test", Path("/tmp"))

    assert codemap is None
