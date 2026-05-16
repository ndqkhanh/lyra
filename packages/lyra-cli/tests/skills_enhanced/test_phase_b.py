"""Tests for Phase B Skills System Enhancement."""

import pytest

from lyra_cli.skills_enhanced.skill_lifecycle import (
    SkillLifecycleManager,
    SkillApplicability,
    SkillPolicy,
    SkillTermination,
    SkillInterface,
    SkillStatus,
)


@pytest.fixture
def skill_manager():
    """Create skill lifecycle manager."""
    return SkillLifecycleManager()


def test_skill_add(skill_manager):
    """Test adding a new skill."""
    skill_id = skill_manager.add(
        name="Test Skill",
        description="A test skill",
        applicability=SkillApplicability(trigger_keywords=["test"]),
        policy=SkillPolicy(execution_steps=["step1", "step2"]),
        termination=SkillTermination(success_conditions=["done"]),
        interface=SkillInterface(),
    )

    assert skill_id is not None
    assert skill_manager.stats["total_skills"] == 1
    assert skill_manager.stats["operations"]["add"] == 1


def test_skill_refine(skill_manager):
    """Test refining a skill."""
    skill_id = skill_manager.add(
        "Test Skill", "Description",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )

    success = skill_manager.refine(skill_id, {"description": "Updated"})

    assert success is True
    assert skill_manager.stats["operations"]["refine"] == 1


def test_skill_merge(skill_manager):
    """Test merging skills."""
    skill1 = skill_manager.add(
        "Skill 1", "First",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )
    skill2 = skill_manager.add(
        "Skill 2", "Second",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )

    merged_id = skill_manager.merge([skill1, skill2], "Merged Skill")

    assert merged_id is not None
    assert skill_manager.stats["operations"]["merge"] == 1


def test_skill_split(skill_manager):
    """Test splitting a skill."""
    skill_id = skill_manager.add(
        "Test Skill", "Description",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )

    split_ids = skill_manager.split(skill_id, {})

    assert len(split_ids) == 2
    assert skill_manager.stats["operations"]["split"] == 1


def test_skill_prune(skill_manager):
    """Test pruning a skill."""
    skill_id = skill_manager.add(
        "Test Skill", "Description",
        SkillApplicability(),
        SkillPolicy(execution_steps=["step1", "unused step"]),
        SkillTermination(), SkillInterface()
    )

    success = skill_manager.prune(skill_id)

    assert success is True
    assert skill_manager.stats["operations"]["prune"] == 1


def test_skill_distill(skill_manager):
    """Test distilling a skill."""
    skill_id = skill_manager.add(
        "Test Skill", "Description",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )

    distilled_id = skill_manager.distill(skill_id)

    assert distilled_id is not None
    assert skill_manager.stats["operations"]["distill"] == 1


def test_skill_abstract(skill_manager):
    """Test abstracting a skill."""
    skill_id = skill_manager.add(
        "Test Skill", "Description",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )

    abstract_id = skill_manager.abstract(skill_id)

    assert abstract_id is not None
    assert skill_manager.stats["operations"]["abstract"] == 1


def test_skill_compose(skill_manager):
    """Test composing skills."""
    skill1 = skill_manager.add(
        "Skill 1", "First",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )
    skill2 = skill_manager.add(
        "Skill 2", "Second",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )

    composed_id = skill_manager.compose([skill1, skill2], "Composed")

    assert composed_id is not None


def test_skill_rewrite(skill_manager):
    """Test rewriting a skill."""
    skill_id = skill_manager.add(
        "Test Skill", "Description",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )

    new_policy = SkillPolicy(execution_steps=["new_step"])
    success = skill_manager.rewrite(skill_id, new_policy)

    assert success is True
    assert skill_manager.stats["operations"]["rewrite"] == 1


def test_skill_rerank(skill_manager):
    """Test reranking skills."""
    skill1 = skill_manager.add(
        "Skill 1", "First",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )
    skill2 = skill_manager.add(
        "Skill 2", "Second",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )

    success = skill_manager.rerank({skill1: 1, skill2: 2})

    assert success is True
    assert skill_manager.stats["operations"]["rerank"] == 1


def test_skill_verify(skill_manager):
    """Test verifying a skill."""
    skill_id = skill_manager.add(
        "Test Skill", "Description",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )

    success = skill_manager.verify_skill(skill_id)

    assert success is True
    assert skill_manager.stats["verified_skills"] == 1


def test_skill_activate(skill_manager):
    """Test activating a verified skill."""
    skill_id = skill_manager.add(
        "Test Skill", "Description",
        SkillApplicability(), SkillPolicy(),
        SkillTermination(), SkillInterface()
    )

    skill_manager.verify_skill(skill_id)
    success = skill_manager.activate_skill(skill_id)

    assert success is True
    assert skill_manager.stats["active_skills"] == 1


def test_skill_lifecycle_complete(skill_manager):
    """Test complete skill lifecycle."""
    # Add
    skill_id = skill_manager.add(
        "Test Skill", "Description",
        SkillApplicability(trigger_keywords=["test"]),
        SkillPolicy(execution_steps=["step1"]),
        SkillTermination(), SkillInterface()
    )

    # Refine
    skill_manager.refine(skill_id, {"description": "Updated"})

    # Verify
    skill_manager.verify_skill(skill_id)

    # Activate
    skill_manager.activate_skill(skill_id)

    skill = skill_manager.skills[skill_id]
    assert skill.status == SkillStatus.ACTIVE
