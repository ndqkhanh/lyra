"""Tests for skill curator."""


import pytest
from lyra_cli.skills.skill_curator import (
    CuratorSignal,
    DiscoverySource,
    SelectionContext,
    SkillCurator,
)


@pytest.fixture
def temp_skills_dir(tmp_path):
    """Create temporary skills directory with test skills."""
    # Use tmp_path as both project and user home to isolate tests
    skills_dir = tmp_path / ".lyra" / "skills"
    skills_dir.mkdir(parents=True)

    # Create test skill 1: Python testing
    skill1 = skills_dir / "test-skill.md"
    skill1.write_text("""---
name: test-skill
description: Write comprehensive tests for Python code
triggers: [test, pytest, unittest]
tags: [testing, python, quality]
tools: [Read, Write, Bash]
---

# Test Skill

Write tests following TDD principles.
""")

    # Create test skill 2: Code review
    skill2 = skills_dir / "review-skill.md"
    skill2.write_text("""---
name: review-skill
description: Review code for quality and correctness
triggers: [review, audit, check]
tags: [quality, review, security]
tools: [Read, Grep]
---

# Review Skill

Systematic code review.
""")

    # Create test skill 3: Debugging
    skill3 = skills_dir / "debug-skill.md"
    skill3.write_text("""---
name: debug-skill
description: Debug and fix errors
triggers: [debug, error, fix]
tags: [debugging, error-handling]
tools: [Read, Bash, Grep]
---

# Debug Skill

Find and fix bugs.
""")

    return tmp_path


class TestSkillCurator:
    """Test suite for SkillCurator."""

    def test_discovery_finds_skills(self, temp_skills_dir):
        """Test that curator discovers skills from directory."""
        # Use temp_skills_dir for both project and user home to isolate
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)
        count = curator.discover_skills()

        assert count == 3
        assert curator.stats.skills_discovered == 3

    def test_selection_by_task_description(self, temp_skills_dir):
        """Test skill selection based on task description."""
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)
        curator.discover_skills()

        context = SelectionContext(
            current_file="test_example.py",
            recent_tools=(),
            task_description="write unit tests for the authentication module",
            active_skills=(),
            error_history=(),
        )

        result = curator.select_skills(context, max_skills=3)

        assert len(result.selected_skills) > 0
        # Should select test-skill due to "test" in description
        skill_names = [s.skill_name for s in result.selected_skills]
        assert "test-skill" in skill_names

    def test_selection_by_file_extension(self, temp_skills_dir):
        """Test skill selection based on file extension."""
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)
        curator.discover_skills()

        context = SelectionContext(
            current_file="app.py",
            recent_tools=(),
            task_description="improve code quality",
            active_skills=(),
            error_history=(),
        )

        result = curator.select_skills(context, max_skills=3)

        assert len(result.selected_skills) > 0
        assert result.retrieval_latency_ms > 0

    def test_selection_with_error_history(self, temp_skills_dir):
        """Test skill selection when errors are present."""
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)
        curator.discover_skills()

        context = SelectionContext(
            current_file="app.py",
            recent_tools=(),
            task_description="fix the issue",
            active_skills=(),
            error_history=("TypeError: cannot concatenate str and int",),
        )

        result = curator.select_skills(context, max_skills=3)

        # Should prioritize debug-skill due to error history
        skill_names = [s.skill_name for s in result.selected_skills]
        assert "debug-skill" in skill_names

    def test_selection_with_user_intent(self, temp_skills_dir):
        """Test explicit user intent overrides other signals."""
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)
        curator.discover_skills()

        context = SelectionContext(
            current_file="app.py",
            recent_tools=(),
            task_description="work on the code",
            active_skills=(),
            error_history=(),
            user_intent="use review-skill",
        )

        result = curator.select_skills(context, max_skills=3)

        # Should select review-skill due to explicit intent
        skill_names = [s.skill_name for s in result.selected_skills]
        assert "review-skill" in skill_names
        # Should have relevance score > 0 (user intent weight is 0.15)
        review_match = next(s for s in result.selected_skills if s.skill_name == "review-skill")
        assert review_match.relevance_score > 0.1

    def test_record_outcome_updates_stats(self, temp_skills_dir):
        """Test recording selection outcomes."""
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)

        curator.record_outcome("test-skill", success=True, relevance_score=0.9)
        curator.record_outcome("test-skill", success=True, relevance_score=0.8)
        curator.record_outcome("test-skill", success=False, relevance_score=0.3)

        stats = curator.get_stats()
        assert stats["successful_selections"] == 2
        assert stats["failed_selections"] == 1
        # Success rate calculation: successful / (successful + failed)
        assert stats["success_rate"] == pytest.approx(2/3, rel=0.01)

    def test_categorize_skills(self, temp_skills_dir):
        """Test skill categorization by tags."""
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)
        curator.discover_skills()

        categories = curator.categorize_skills()

        assert "testing" in categories
        assert "quality" in categories
        assert "debugging" in categories

    def test_recommend_skills(self, temp_skills_dir):
        """Test skill recommendations based on active skills."""
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)
        curator.discover_skills()

        recommendations = curator.recommend_skills(
            current_skills=["test-skill"],
            max_recommendations=2,
        )

        # Should recommend review-skill (shares "quality" tag)
        assert len(recommendations) > 0
        recommended_names = [name for name, _ in recommendations]
        assert "review-skill" in recommended_names

    def test_empty_directory_returns_zero(self, tmp_path):
        """Test discovery in empty directory."""
        curator = SkillCurator(project_root=tmp_path, user_home=tmp_path)
        count = curator.discover_skills()

        assert count == 0

    def test_malformed_skill_is_skipped(self, tmp_path):
        """Test that malformed skills are skipped."""
        skills_dir = tmp_path / ".lyra" / "skills"
        skills_dir.mkdir(parents=True)

        # Create malformed skill (no frontmatter)
        bad_skill = skills_dir / "bad-skill.md"
        bad_skill.write_text("# Just a heading\n\nNo frontmatter here.")

        curator = SkillCurator(project_root=tmp_path, user_home=tmp_path)
        count = curator.discover_skills()

        assert count == 0  # Malformed skill should be skipped

    def test_routing_signals_detected(self, temp_skills_dir):
        """Test that routing signals are correctly identified."""
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)
        curator.discover_skills()

        context = SelectionContext(
            current_file="test.py",
            recent_tools=("Read", "Write"),
            task_description="write tests",
            active_skills=("existing-skill",),
            error_history=("error message",),
            user_intent="explicit intent",
        )

        result = curator.select_skills(context)

        # All signals should be detected
        assert CuratorSignal.FILE_EXTENSION in result.routing_signals_used
        assert CuratorSignal.ACTIVE_TOOLS in result.routing_signals_used
        assert CuratorSignal.TASK_CATEGORY in result.routing_signals_used
        assert CuratorSignal.RECENT_ERRORS in result.routing_signals_used
        assert CuratorSignal.USER_EXPLICIT in result.routing_signals_used
        assert CuratorSignal.DEPENDENCY_CHAIN in result.routing_signals_used

    def test_max_skills_limit_respected(self, temp_skills_dir):
        """Test that max_skills limit is respected."""
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)
        curator.discover_skills()

        context = SelectionContext(
            current_file="app.py",
            recent_tools=(),
            task_description="general task",
            active_skills=(),
            error_history=(),
        )

        result = curator.select_skills(context, max_skills=2)

        assert len(result.selected_skills) <= 2

    def test_discovery_source_identification(self, temp_skills_dir):
        """Test that skill sources are correctly identified."""
        curator = SkillCurator(project_root=temp_skills_dir, user_home=temp_skills_dir)
        curator.discover_skills()

        context = SelectionContext(
            current_file="app.py",
            recent_tools=(),
            task_description="test",
            active_skills=(),
            error_history=(),
        )

        result = curator.select_skills(context)

        # All skills should be from PROJECT_LOCAL (since we use temp_skills_dir for both)
        for match in result.selected_skills:
            assert match.source == DiscoverySource.PROJECT_LOCAL
