"""
Tests for Skills System

Tests the 7-tuple skill formalism with verifier-gated admission.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from lyra_evolution.skills_system import Skill, SkillRegistry


@pytest.fixture
def temp_registry():
    """Create temporary skill registry for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    skills_dir = temp_dir / "skills"

    registry = SkillRegistry(skills_dir=skills_dir)

    yield registry

    # Cleanup
    shutil.rmtree(temp_dir)


def test_registry_initialization(temp_registry):
    """Test registry initializes correctly."""
    assert temp_registry.skills_dir.exists()
    assert len(temp_registry.skills) == 0


def test_add_code_skill(temp_registry):
    """Test adding code skill."""
    skill = Skill(
        name="test_skill",
        applicability="When testing",
        policy="def test(): pass",
        termination="Test complete",
        interface={"inputs": [], "outputs": []},
        skill_type="code"
    )

    admitted = temp_registry.add_skill(skill, verify=True)
    assert admitted
    assert skill.verified


def test_add_workflow_skill(temp_registry):
    """Test adding workflow skill."""
    skill = Skill(
        name="test_workflow",
        applicability="When running workflow",
        policy="1. Step one\n2. Step two",
        termination="Workflow complete",
        interface={"inputs": [], "outputs": []},
        skill_type="workflow"
    )

    admitted = temp_registry.add_skill(skill, verify=True)
    assert admitted


def test_get_skill(temp_registry):
    """Test retrieving skill."""
    skill = Skill(
        name="retrieve_test",
        applicability="Test",
        policy="pass",
        termination="Done",
        interface={}
    )

    temp_registry.add_skill(skill)

    retrieved = temp_registry.get_skill("retrieve_test")
    assert retrieved is not None
    assert retrieved.name == "retrieve_test"


def test_search_skills_by_type(temp_registry):
    """Test searching skills by type."""
    # Add different types
    temp_registry.add_skill(Skill(
        name="code1",
        applicability="Test",
        policy="pass",
        termination="Done",
        interface={},
        skill_type="code"
    ))

    temp_registry.add_skill(Skill(
        name="workflow1",
        applicability="Test",
        policy="pass",
        termination="Done",
        interface={},
        skill_type="workflow"
    ))

    # Search by type
    code_skills = temp_registry.search_skills(skill_type="code")
    assert len(code_skills) == 1
    assert code_skills[0].skill_type == "code"


def test_search_skills_by_query(temp_registry):
    """Test searching skills by text query."""
    temp_registry.add_skill(Skill(
        name="parallel_exploration",
        applicability="When exploring variants",
        policy="pass",
        termination="Done",
        interface={}
    ))

    temp_registry.add_skill(Skill(
        name="sequential_test",
        applicability="When testing",
        policy="pass",
        termination="Done",
        interface={}
    ))

    # Search by name
    results = temp_registry.search_skills(query="parallel")
    assert len(results) == 1
    assert "parallel" in results[0].name


def test_update_skill(temp_registry):
    """Test updating skill."""
    skill = Skill(
        name="update_test",
        applicability="Original",
        policy="pass",
        termination="Done",
        interface={}
    )

    temp_registry.add_skill(skill)

    # Update
    updated = temp_registry.update_skill(
        "update_test",
        {"applicability": "Updated"}
    )

    assert updated

    # Verify update
    retrieved = temp_registry.get_skill("update_test")
    assert retrieved.applicability == "Updated"
    assert retrieved.lineage.version == 2


def test_delete_skill(temp_registry):
    """Test deleting skill."""
    skill = Skill(
        name="delete_test",
        applicability="Test",
        policy="pass",
        termination="Done",
        interface={}
    )

    temp_registry.add_skill(skill)

    # Delete
    deleted = temp_registry.delete_skill("delete_test")
    assert deleted

    # Verify deletion
    retrieved = temp_registry.get_skill("delete_test")
    assert retrieved is None


def test_skill_persistence(temp_registry):
    """Test skills persist to disk."""
    skill = Skill(
        name="persist_test",
        applicability="Test",
        policy="pass",
        termination="Done",
        interface={}
    )

    temp_registry.add_skill(skill)

    # Create new registry (reload from disk)
    new_registry = SkillRegistry(skills_dir=temp_registry.skills_dir)

    # Verify skill loaded
    retrieved = new_registry.get_skill("persist_test")
    assert retrieved is not None
    assert retrieved.name == "persist_test"


def test_skill_lineage(temp_registry):
    """Test skill lineage tracking."""
    skill = Skill(
        name="lineage_test",
        applicability="Test",
        policy="pass",
        termination="Done",
        interface={}
    )

    temp_registry.add_skill(skill)

    # Update multiple times
    temp_registry.update_skill("lineage_test", {"policy": "new_policy"})
    temp_registry.update_skill("lineage_test", {"applicability": "new_app"})

    # Check lineage
    retrieved = temp_registry.get_skill("lineage_test")
    assert retrieved.lineage.version == 3
    assert len(retrieved.lineage.modifications) == 2


def test_verified_only_search(temp_registry):
    """Test searching only verified skills."""
    # Add verified skill
    verified = Skill(
        name="verified",
        applicability="Test",
        policy="pass",
        termination="Done",
        interface={}
    )
    temp_registry.add_skill(verified, verify=True)

    # Add unverified skill
    unverified = Skill(
        name="unverified",
        applicability="Test",
        policy="pass",
        termination="Done",
        interface={}
    )
    temp_registry.add_skill(unverified, verify=False)

    # Search verified only
    results = temp_registry.search_skills(verified_only=True)
    assert len(results) == 1
    assert results[0].verified


def test_get_statistics(temp_registry):
    """Test registry statistics."""
    # Add various skills
    temp_registry.add_skill(Skill(
        name="code1",
        applicability="Test",
        policy="pass",
        termination="Done",
        interface={},
        skill_type="code",
        risk_level="low"
    ), verify=True)

    temp_registry.add_skill(Skill(
        name="workflow1",
        applicability="Test",
        policy="pass",
        termination="Done",
        interface={},
        skill_type="workflow",
        risk_level="high"
    ), verify=False)

    stats = temp_registry.get_statistics()

    assert stats["total"] == 2
    assert stats["verified"] == 1
    assert stats["unverified"] == 1
    assert stats["by_type"]["code"] == 1
    assert stats["by_type"]["workflow"] == 1
    assert stats["by_risk"]["low"] == 1
    assert stats["by_risk"]["high"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
