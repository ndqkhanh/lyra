"""Tests for priority skills."""

import pytest

from lyra_cli.skills_integration import PrioritySkills, SkillMatcher


def test_get_all_skills():
    """All 10 priority skills are available."""
    skills = PrioritySkills.get_all()

    assert len(skills) == 10
    assert all(s.name for s in skills)
    assert all(s.description for s in skills)


def test_skill_matcher_finds_matches():
    """Skill matcher finds relevant skills."""
    matcher = SkillMatcher()

    matches = matcher.match("I need to review this code")

    assert len(matches) > 0
    assert any(s.name == "code-reviewer" for s in matches)


def test_skill_matcher_multiple_matches():
    """Skill matcher can find multiple matches."""
    matcher = SkillMatcher()

    matches = matcher.match("review code for security issues")

    # Should match both code-reviewer and security-reviewer
    assert len(matches) >= 2


def test_get_skill_by_name():
    """Can retrieve skill by name."""
    matcher = SkillMatcher()

    skill = matcher.get_skill("code-reviewer")

    assert skill is not None
    assert skill.name == "code-reviewer"


@pytest.mark.anyio
async def test_code_reviewer_handler():
    """Code reviewer handler executes."""
    result = await PrioritySkills.code_reviewer({})

    assert "code review" in result.lower()


@pytest.mark.anyio
async def test_tdd_guide_handler():
    """TDD guide handler executes."""
    result = await PrioritySkills.tdd_guide({})

    assert "tdd" in result.lower()
