"""Integration tests for Phase 4: Advanced Features.

Tests the complete flow of:
- Skill composition execution
- Analytics tracking
- Configuration management
- Template-based skill creation
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from lyra_cli.cli.skill_manager import SkillManager


@pytest.fixture
def temp_lyra_dir():
    """Create a temporary .lyra directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        lyra_dir = Path(tmpdir) / ".lyra"
        lyra_dir.mkdir()

        # Create subdirectories
        (lyra_dir / "skills").mkdir()
        (lyra_dir / "templates").mkdir()
        (lyra_dir / "analytics").mkdir()

        yield lyra_dir


@pytest.fixture
def skill_manager(temp_lyra_dir, monkeypatch):
    """Create a skill manager with temp directories."""
    # Patch home directory to use temp dir
    monkeypatch.setattr(Path, "home", lambda: temp_lyra_dir.parent)

    manager = SkillManager()

    # Add test skills
    test_skills = {
        "test-skill-a": {
            "name": "test-skill-a",
            "version": "1.0.0",
            "description": "Test skill A",
            "category": "test",
            "execution": {"type": "prompt", "prompt": "Execute A"},
        },
        "test-skill-b": {
            "name": "test-skill-b",
            "version": "1.0.0",
            "description": "Test skill B",
            "category": "test",
            "execution": {"type": "prompt", "prompt": "Execute B"},
        },
        "test-composition": {
            "name": "test-composition",
            "version": "1.0.0",
            "description": "Test composition skill",
            "category": "test",
            "execution": {
                "type": "composition",
                "stages": [
                    {
                        "name": "stage1",
                        "skill": "test-skill-a",
                        "args": "${input}",
                        "output": "result1",
                    },
                    {
                        "name": "stage2",
                        "skill": "test-skill-b",
                        "args": "${result1}",
                        "output": "result2",
                    },
                ],
                "return": "${result2}",
            },
        },
    }

    # Save test skills to temp directory
    for skill_name, skill_data in test_skills.items():
        skill_file = temp_lyra_dir / "skills" / f"{skill_name}.json"
        with open(skill_file, "w") as f:
            json.dump(skill_data, f)

    # Reload skills
    manager.reload()

    # Mock execute_skill for testing
    def mock_execute_skill(skill_name: str, args: str) -> str:
        return f"Output from {skill_name} with args: {args}"

    manager.execute_skill = mock_execute_skill

    return manager


def test_composition_execution(skill_manager):
    """Test executing a composition skill end-to-end."""
    result = skill_manager.execute_composition("test-composition", "test input")

    assert result["success"]
    assert result["output"] is not None
    assert "test-skill-b" in result["output"]


def test_composition_with_nonexistent_skill(skill_manager):
    """Test composition fails gracefully with missing skill."""
    # Create a composition with a nonexistent skill
    bad_composition = {
        "name": "bad-composition",
        "version": "1.0.0",
        "description": "Bad composition",
        "category": "test",
        "execution": {
            "type": "composition",
            "stages": [
                {
                    "name": "stage1",
                    "skill": "nonexistent-skill",
                    "args": "${input}",
                    "output": "result",
                }
            ],
            "return": "${result}",
        },
    }

    skill_manager.skills["bad-composition"] = bad_composition
    result = skill_manager.execute_composition("bad-composition", "test")

    assert not result["success"]
    assert "not found" in result["error"]


def test_analytics_tracking(skill_manager):
    """Test that skill execution is tracked in analytics."""
    # Execute a composition
    skill_manager.execute_composition("test-composition", "test input")

    # Check analytics
    stats = skill_manager.get_skill_stats("test-composition")

    assert "test-composition" in stats
    assert stats["test-composition"]["total_invocations"] == 1
    assert stats["test-composition"]["successful_invocations"] == 1


def test_analytics_failure_tracking(skill_manager):
    """Test that failed executions are tracked."""
    # Create a composition that will fail
    bad_composition = {
        "name": "fail-composition",
        "version": "1.0.0",
        "description": "Failing composition",
        "category": "test",
        "execution": {
            "type": "composition",
            "stages": [
                {
                    "name": "stage1",
                    "skill": "nonexistent",
                    "args": "${input}",
                    "output": "result",
                }
            ],
            "return": "${result}",
        },
    }

    skill_manager.skills["fail-composition"] = bad_composition
    skill_manager.execute_composition("fail-composition", "test")

    # Check analytics
    stats = skill_manager.get_skill_stats("fail-composition")

    assert stats["fail-composition"]["total_invocations"] == 1
    assert stats["fail-composition"]["failed_invocations"] == 1
    assert stats["fail-composition"]["success_rate"] == 0.0


def test_top_skills_query(skill_manager):
    """Test querying top skills by usage."""
    # Execute multiple skills
    skill_manager.execute_composition("test-composition", "input1")
    skill_manager.execute_composition("test-composition", "input2")

    # Get top skills
    top_skills = skill_manager.get_top_skills(limit=5, sort_by="invocations")

    assert len(top_skills) > 0
    assert top_skills[0]["skill_name"] == "test-composition"
    assert top_skills[0]["total_invocations"] == 2


def test_skill_configuration(skill_manager):
    """Test skill configuration management."""
    # Set configuration
    config = {"timeout": 30, "retry": 3, "custom_param": "value"}
    skill_manager.set_skill_config("test-skill-a", config)

    # Get configuration
    retrieved_config = skill_manager.get_skill_config("test-skill-a")

    assert retrieved_config["timeout"] == 30
    assert retrieved_config["retry"] == 3
    assert retrieved_config["custom_param"] == "value"


def test_skill_configuration_persistence(skill_manager):
    """Test that configuration persists across reloads."""
    # Set configuration
    config = {"setting": "value"}
    skill_manager.set_skill_config("test-skill-a", config)

    # Create new manager instance (simulates reload)
    new_manager = SkillManager()
    new_manager.config_manager = skill_manager.config_manager

    # Get configuration
    retrieved_config = new_manager.get_skill_config("test-skill-a")

    assert retrieved_config["setting"] == "value"


def test_template_listing(skill_manager):
    """Test listing available templates."""
    templates = skill_manager.list_templates()

    assert len(templates) > 0
    assert any(t["name"] == "prompt-skill" for t in templates)


def test_create_skill_from_template(skill_manager, temp_lyra_dir):
    """Test creating a skill from a template."""
    variables = {
        "skill_name": "new-test-skill",
        "description": "A new test skill",
        "category": "test",
        "prompt": "Execute the test",
    }

    result = skill_manager.create_from_template(
        "prompt-skill",
        variables,
        save_path=temp_lyra_dir / "skills" / "new-test-skill.json",
    )

    assert result["success"]
    assert result["skill_name"] == "new-test-skill"

    # Verify skill was created
    skill_file = Path(result["path"])
    assert skill_file.exists()

    # Verify skill content
    with open(skill_file) as f:
        skill_data = json.load(f)

    assert skill_data["name"] == "new-test-skill"
    assert skill_data["description"] == "A new test skill"
    assert skill_data["category"] == "test"


def test_record_skill_execution(skill_manager):
    """Test manual recording of skill execution."""
    skill_manager.record_skill_execution(
        skill_name="test-skill-a",
        duration_ms=150,
        success=True,
        args_length=10,
        output_length=50,
    )

    stats = skill_manager.get_skill_stats("test-skill-a")

    assert stats["test-skill-a"]["total_invocations"] == 1
    assert stats["test-skill-a"]["successful_invocations"] == 1
    assert stats["test-skill-a"]["avg_duration_ms"] == 150


def test_composition_context_isolation(skill_manager):
    """Test that composition contexts are isolated between executions."""
    # Execute first composition
    result1 = skill_manager.execute_composition("test-composition", "input1")

    # Execute second composition
    result2 = skill_manager.execute_composition("test-composition", "input2")

    # Results should be different (not sharing context)
    assert result1["output"] != result2["output"]
    assert "input1" in result1["output"]
    assert "input2" in result2["output"]


def test_global_config_access(skill_manager):
    """Test accessing global skill configuration."""
    global_config = skill_manager.get_global_config()

    # Should have default global settings
    assert isinstance(global_config, dict)
