"""
Comprehensive tests for the skills system.
"""

import tempfile
from pathlib import Path

import pytest

from src.skills import (
    ECCSkillImporter,
    Skill,
    SkillCategory,
    SkillParser,
    SkillRegistry,
)


class TestSkill:
    """Tests for Skill class."""

    def test_skill_creation(self):
        """Test creating a skill."""
        skill = Skill(
            name="python-testing",
            description="Python testing patterns",
            content="Use pytest for testing",
            category=SkillCategory.TDD_TESTING,
            trigger_patterns=["test", "pytest"],
            tags=["python", "testing"],
            language="python",
        )

        assert skill.name == "python-testing"
        assert skill.description == "Python testing patterns"
        assert skill.category == SkillCategory.TDD_TESTING
        assert len(skill.trigger_patterns) == 2
        assert len(skill.tags) == 2

    def test_matches_trigger(self):
        """Test trigger pattern matching."""
        skill = Skill(
            name="test-skill",
            description="Test",
            content="Content",
            trigger_patterns=["pytest", "unit test"],
        )

        assert skill.matches_trigger("I need to write pytest tests")
        assert skill.matches_trigger("How do I unit test this?")
        assert not skill.matches_trigger("No match here")

    def test_matches_tags(self):
        """Test tag matching."""
        skill = Skill(
            name="test-skill",
            description="Test",
            content="Content",
            tags=["python", "testing", "pytest"],
        )

        assert skill.matches_tags({"python"})
        assert skill.matches_tags({"testing", "coverage"})
        assert not skill.matches_tags({"javascript", "jest"})

    def test_to_dict(self):
        """Test converting skill to dictionary."""
        skill = Skill(
            name="test-skill",
            description="Test",
            content="Content",
            category=SkillCategory.TDD_TESTING,
        )

        data = skill.to_dict()
        assert data["name"] == "test-skill"
        assert data["category"] == "tdd-testing"
        assert "created_at" in data

    def test_from_dict(self):
        """Test creating skill from dictionary."""
        data = {
            "name": "test-skill",
            "description": "Test",
            "content": "Content",
            "category": "tdd-testing",
            "tags": ["python"],
        }

        skill = Skill.from_dict(data)
        assert skill.name == "test-skill"
        assert skill.category == SkillCategory.TDD_TESTING
        assert skill.tags == ["python"]


class TestSkillRegistry:
    """Tests for SkillRegistry class."""

    def test_registry_creation(self):
        """Test creating a registry."""
        registry = SkillRegistry()
        assert len(registry.skills) == 0

    def test_register_skill(self):
        """Test registering a skill."""
        registry = SkillRegistry()
        skill = Skill(
            name="test-skill",
            description="Test",
            content="Content",
        )

        registry.register(skill)
        assert len(registry.skills) == 1
        assert "test-skill" in registry.skills

    def test_unregister_skill(self):
        """Test unregistering a skill."""
        registry = SkillRegistry()
        skill = Skill(
            name="test-skill",
            description="Test",
            content="Content",
        )

        registry.register(skill)
        assert registry.unregister("test-skill")
        assert len(registry.skills) == 0
        assert not registry.unregister("nonexistent")

    def test_get_skill(self):
        """Test getting a skill."""
        registry = SkillRegistry()
        skill = Skill(
            name="test-skill",
            description="Test",
            content="Content",
        )

        registry.register(skill)
        retrieved = registry.get("test-skill")
        assert retrieved is not None
        assert retrieved.name == "test-skill"
        assert registry.get("nonexistent") is None

    def test_find_by_trigger(self):
        """Test finding skills by trigger."""
        registry = SkillRegistry()

        skill1 = Skill(
            name="pytest-skill",
            description="Pytest testing",
            content="Content",
            trigger_patterns=["pytest", "test"],
        )
        skill2 = Skill(
            name="unittest-skill",
            description="Unittest testing",
            content="Content",
            trigger_patterns=["unittest", "test"],
        )

        registry.register(skill1)
        registry.register(skill2)

        results = registry.find_by_trigger("I need pytest help")
        assert len(results) > 0
        assert results[0].skill.name == "pytest-skill"

    def test_find_by_category(self):
        """Test finding skills by category."""
        registry = SkillRegistry()

        skill1 = Skill(
            name="skill1",
            description="Test",
            content="Content",
            category=SkillCategory.TDD_TESTING,
        )
        skill2 = Skill(
            name="skill2",
            description="Test",
            content="Content",
            category=SkillCategory.BACKEND_PATTERNS,
        )

        registry.register(skill1)
        registry.register(skill2)

        results = registry.find_by_category(SkillCategory.TDD_TESTING)
        assert len(results) == 1
        assert results[0].name == "skill1"

    def test_find_by_tags(self):
        """Test finding skills by tags."""
        registry = SkillRegistry()

        skill1 = Skill(
            name="skill1",
            description="Test",
            content="Content",
            tags=["python", "testing"],
        )
        skill2 = Skill(
            name="skill2",
            description="Test",
            content="Content",
            tags=["javascript", "testing"],
        )

        registry.register(skill1)
        registry.register(skill2)

        # Match any tag
        results = registry.find_by_tags({"python"}, match_all=False)
        assert len(results) == 1
        assert results[0].name == "skill1"

        # Match all tags
        results = registry.find_by_tags({"python", "testing"}, match_all=True)
        assert len(results) == 1

    def test_find_by_language(self):
        """Test finding skills by language."""
        registry = SkillRegistry()

        skill1 = Skill(
            name="skill1",
            description="Test",
            content="Content",
            language="python",
        )
        skill2 = Skill(
            name="skill2",
            description="Test",
            content="Content",
            language="javascript",
        )

        registry.register(skill1)
        registry.register(skill2)

        results = registry.find_by_language("python")
        assert len(results) == 1
        assert results[0].name == "skill1"

    def test_search(self):
        """Test comprehensive search."""
        registry = SkillRegistry()

        skill = Skill(
            name="python-testing",
            description="Python testing patterns",
            content="Use pytest for testing",
            category=SkillCategory.TDD_TESTING,
            tags=["python", "testing"],
            language="python",
        )

        registry.register(skill)

        # Search by name
        results = registry.search("python")
        assert len(results) > 0
        assert results[0].skill.name == "python-testing"

        # Search with filters
        results = registry.search(
            "testing",
            category=SkillCategory.TDD_TESTING,
            language="python",
        )
        assert len(results) > 0

    def test_get_statistics(self):
        """Test getting registry statistics."""
        registry = SkillRegistry()

        skill1 = Skill(
            name="skill1",
            description="Test",
            content="Content",
            category=SkillCategory.TDD_TESTING,
            language="python",
            source="lyra",
        )
        skill2 = Skill(
            name="skill2",
            description="Test",
            content="Content",
            category=SkillCategory.BACKEND_PATTERNS,
            language="python",
            source="ecc",
        )

        registry.register(skill1)
        registry.register(skill2)

        stats = registry.get_statistics()
        assert stats["total_skills"] == 2
        assert stats["by_category"]["tdd-testing"] == 1
        assert stats["by_language"]["python"] == 2
        assert stats["sources"]["lyra"] == 1
        assert stats["sources"]["ecc"] == 1

    def test_save_and_load(self):
        """Test saving and loading registry."""
        registry = SkillRegistry()

        skill = Skill(
            name="test-skill",
            description="Test",
            content="Content",
        )
        registry.register(skill)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skills.json"
            registry.save(path)

            new_registry = SkillRegistry()
            count = new_registry.load(path)

            assert count == 1
            assert "test-skill" in new_registry.skills

    def test_clear(self):
        """Test clearing registry."""
        registry = SkillRegistry()

        skill = Skill(
            name="test-skill",
            description="Test",
            content="Content",
        )
        registry.register(skill)

        registry.clear()
        assert len(registry.skills) == 0


class TestSkillParser:
    """Tests for SkillParser class."""

    def test_parse_string(self):
        """Test parsing skill from string."""
        content = """---
name: python-testing
description: Python testing patterns
category: tdd-testing
trigger_patterns: [pytest, test]
tags: [python, testing]
language: python
---

# Python Testing

Use pytest for testing.
"""

        parser = SkillParser()
        skill = parser.parse_string(content)

        assert skill is not None
        assert skill.name == "python-testing"
        assert skill.description == "Python testing patterns"
        assert skill.category == SkillCategory.TDD_TESTING
        assert len(skill.trigger_patterns) == 2
        assert skill.language == "python"
        assert "pytest" in skill.content

    def test_parse_file(self):
        """Test parsing skill from file."""
        content = """---
name: test-skill
description: Test skill
---

Content here.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill.md"
            path.write_text(content)

            parser = SkillParser()
            skill = parser.parse_file(path)

            assert skill is not None
            assert skill.name == "test-skill"

    def test_parse_directory(self):
        """Test parsing directory of skills."""
        skill1_content = """---
name: skill1
description: Skill 1
---

Content 1
"""

        skill2_content = """---
name: skill2
description: Skill 2
---

Content 2
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "skill1.md").write_text(skill1_content)
            (tmpdir / "skill2.md").write_text(skill2_content)

            parser = SkillParser()
            skills = parser.parse_directory(tmpdir)

            assert len(skills) == 2
            assert "skill1" in skills
            assert "skill2" in skills


class TestECCSkillImporter:
    """Tests for ECCSkillImporter class."""

    def test_import_file(self):
        """Test importing a single file."""
        content = """---
name: test-skill
description: Test skill
---

Content
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill.md"
            path.write_text(content)

            registry = SkillRegistry()
            importer = ECCSkillImporter(registry)

            assert importer.import_file(path)
            assert "test-skill" in registry.skills

    def test_import_directory(self):
        """Test importing directory of skills."""
        skill1 = """---
name: skill1
description: Skill 1
---

Content 1
"""

        skill2 = """---
name: skill2
description: Skill 2
---

Content 2
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "skill1.md").write_text(skill1)
            (tmpdir / "skill2.md").write_text(skill2)

            registry = SkillRegistry()
            importer = ECCSkillImporter(registry)

            result = importer.import_directory(tmpdir)

            assert result.total_files == 2
            assert result.parsed_successfully == 2
            assert result.registered_successfully == 2
            assert result.success_rate == 1.0
            assert len(result.failed) == 0

    def test_import_with_failures(self):
        """Test importing with some failures."""
        valid_skill = """---
name: valid-skill
description: Valid skill
---

Content
"""

        invalid_skill = """---
invalid yaml: [
---

Content
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "valid.md").write_text(valid_skill)
            (tmpdir / "invalid.md").write_text(invalid_skill)

            registry = SkillRegistry()
            importer = ECCSkillImporter(registry)

            result = importer.import_directory(tmpdir)

            assert result.total_files == 2
            assert result.registered_successfully == 1
            assert len(result.failed) == 1
            assert result.success_rate == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
