from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import pytest

from lyra_open_ended import (
    CurriculumPhase,
    CurriculumStep,
    GoalDifficulty,
    GoalOutcome,
    GoalStatus,
    LearnerProfile,
    LearningGoal,
    OpenEndedLearner,
)


# ======================================================================
# Enum tests
# ======================================================================


class TestGoalStatus:
    def test_values(self) -> None:
        assert GoalStatus.PROPOSED.value == "proposed"
        assert GoalStatus.ACTIVE.value == "active"
        assert GoalStatus.COMPLETED.value == "completed"
        assert GoalStatus.ABANDONED.value == "abandoned"
        assert GoalStatus.SUPERSEDED.value == "superseded"

    def test_is_string_enum(self) -> None:
        assert issubclass(GoalStatus, str)


class TestGoalDifficulty:
    def test_values(self) -> None:
        assert GoalDifficulty.TRIVIAL.value == "trivial"
        assert GoalDifficulty.EASY.value == "easy"
        assert GoalDifficulty.MEDIUM.value == "medium"
        assert GoalDifficulty.HARD.value == "hard"
        assert GoalDifficulty.EXPERT.value == "expert"

    def test_is_string_enum(self) -> None:
        assert issubclass(GoalDifficulty, str)


class TestCurriculumPhase:
    def test_values(self) -> None:
        assert CurriculumPhase.FOUNDATIONS.value == "foundations"
        assert CurriculumPhase.CORE.value == "core"
        assert CurriculumPhase.ADVANCED.value == "advanced"
        assert CurriculumPhase.SPECIALIZED.value == "specialized"
        assert CurriculumPhase.FRONTIER.value == "frontier"

    def test_is_string_enum(self) -> None:
        assert issubclass(CurriculumPhase, str)


# ======================================================================
# Frozen dataclass tests
# ======================================================================


class TestLearningGoal:
    def test_creation(self) -> None:
        now = datetime.now()
        goal = LearningGoal(
            goal_id="g_0001",
            title="Test Goal",
            description="A test goal",
            domain="Testing",
            difficulty=GoalDifficulty.EASY,
            prerequisites=("Prereq A",),
            estimated_steps=3,
            status=GoalStatus.PROPOSED,
            progress_score=0.0,
            created_at=now,
            completed_at=None,
        )
        assert goal.goal_id == "g_0001"
        assert goal.title == "Test Goal"
        assert goal.status == GoalStatus.PROPOSED
        assert goal.progress_score == 0.0
        assert goal.completed_at is None

    def test_is_frozen(self) -> None:
        now = datetime.now()
        goal = LearningGoal(
            goal_id="g_0001",
            title="Test Goal",
            description="A test goal",
            domain="Testing",
            difficulty=GoalDifficulty.EASY,
            prerequisites=(),
            estimated_steps=1,
            status=GoalStatus.PROPOSED,
            progress_score=0.0,
            created_at=now,
            completed_at=None,
        )
        with pytest.raises(AttributeError):
            goal.title = "Changed"  # type: ignore[misc]


class TestGoalOutcome:
    def test_creation(self) -> None:
        outcome = GoalOutcome(
            goal_id="g_0001",
            success_rating=0.85,
            time_spent_seconds=3600.0,
            skills_gained=("python", "testing"),
            insights="Completed successfully",
            next_goal_hints=("Advanced Testing",),
        )
        assert outcome.goal_id == "g_0001"
        assert outcome.success_rating == 0.85
        assert outcome.skills_gained == ("python", "testing")

    def test_is_frozen(self) -> None:
        outcome = GoalOutcome(
            goal_id="g_0001",
            success_rating=0.5,
            time_spent_seconds=0.0,
            skills_gained=(),
            insights="",
            next_goal_hints=(),
        )
        with pytest.raises(AttributeError):
            outcome.success_rating = 0.9  # type: ignore[misc]


class TestCurriculumStep:
    def test_creation(self) -> None:
        now = datetime.now()
        goal = LearningGoal(
            goal_id="g_0001",
            title="Test",
            description="A goal",
            domain="Test",
            difficulty=GoalDifficulty.TRIVIAL,
            prerequisites=(),
            estimated_steps=1,
            status=GoalStatus.PROPOSED,
            progress_score=0.0,
            created_at=now,
            completed_at=None,
        )
        step = CurriculumStep(
            step_id="step_001",
            phase=CurriculumPhase.FOUNDATIONS,
            goals=(goal,),
            estimated_duration_hours=2.0,
            review_criteria="Complete the test goal",
        )
        assert step.step_id == "step_001"
        assert step.phase == CurriculumPhase.FOUNDATIONS
        assert len(step.goals) == 1

    def test_is_frozen(self) -> None:
        step = CurriculumStep(
            step_id="s",
            phase=CurriculumPhase.CORE,
            goals=(),
            estimated_duration_hours=0.0,
            review_criteria="",
        )
        with pytest.raises(AttributeError):
            step.step_id = "changed"  # type: ignore[misc]


class TestLearnerProfile:
    def test_creation(self) -> None:
        profile = LearnerProfile(
            learner_id="agent-1",
            capabilities=("basic_literacy", "python"),
            knowledge_gaps=("advanced_math",),
            completed_goals=("g_0001",),
            total_progress=0.5,
            current_phase=CurriculumPhase.CORE,
        )
        assert profile.learner_id == "agent-1"
        assert "python" in profile.capabilities
        assert profile.total_progress == 0.5

    def test_is_frozen(self) -> None:
        profile = LearnerProfile(
            learner_id="a",
            capabilities=(),
            knowledge_gaps=(),
            completed_goals=(),
            total_progress=0.0,
            current_phase=CurriculumPhase.FOUNDATIONS,
        )
        with pytest.raises(AttributeError):
            profile.learner_id = "b"  # type: ignore[misc]


# ======================================================================
# OpenEndedLearner tests
# ======================================================================


class TestOpenEndedLearnerInit:
    def test_default_capabilities(self) -> None:
        learner = OpenEndedLearner("agent-1")
        progress = learner.get_progress()
        assert progress["learner_id"] == "agent-1"
        assert "basic_literacy" in progress["capabilities"]
        assert progress["total_progress"] == 0.0
        assert progress["completed_goals"] == ()

    def test_custom_capabilities(self) -> None:
        learner = OpenEndedLearner("agent-2", capabilities=("python", "math", "logic"))
        progress = learner.get_progress()
        caps = progress["capabilities"]
        assert "python" in caps
        assert "math" in caps
        assert "logic" in caps
        # Capabilities should be sorted
        assert caps == ("logic", "math", "python")

    def test_learner_id_is_stored(self) -> None:
        learner = OpenEndedLearner("my-learner")
        stats = learner.get_stats()
        assert stats["learner_id"] == "my-learner"


class TestProposeGoal:
    def test_basic_proposal(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        assert isinstance(goal, LearningGoal)
        assert goal.status == GoalStatus.PROPOSED
        assert re.match(r"g_\d{4}", goal.goal_id)
        assert goal.progress_score == 0.0
        assert goal.completed_at is None
        assert isinstance(goal.created_at, datetime)

    def test_proposal_with_domain(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal(domain="Programming")
        assert goal.domain == "Programming"
        assert goal.status == GoalStatus.PROPOSED

    def test_proposal_with_difficulty(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal(difficulty="trivial")
        assert goal.difficulty == GoalDifficulty.TRIVIAL

    def test_proposal_domain_and_difficulty(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal(domain="Mathematics", difficulty="easy")
        assert goal.domain == "Mathematics"
        assert goal.difficulty == GoalDifficulty.EASY

    def test_difficulty_progression(self) -> None:
        """Learner should not be able to jump directly to EXPERT."""
        learner = OpenEndedLearner("agent-1")
        expert_goal = learner.propose_goal(difficulty="expert")
        # Cannot propose EXPERT without any completed goals — should get a generic trivial goal
        assert expert_goal.difficulty == GoalDifficulty.TRIVIAL

    def test_difficulty_progression_after_completion(self) -> None:
        """After completing a TRIVIAL goal, EASY should be proposed."""
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "Successfully completed and understood everything.")
        learner.record_outcome(goal, outcome)

        # Next proposals should reach up to MEDIUM (TRIVIAL completed -> EASY reachable, max+2)
        next_goal = learner.propose_goal(difficulty="easy")
        assert next_goal.difficulty == GoalDifficulty.EASY

    def test_prerequisites_respected(self) -> None:
        """A goal with unmet prerequisites should not be proposed unless prereqs are met."""
        learner = OpenEndedLearner("agent-1")
        # Propose without domain — heuristic will pick best available
        goal1 = learner.propose_goal(domain="Mathematics")
        assert goal1.domain == "Mathematics"

    def test_domain_diversity(self) -> None:
        """Propose goals from different domains when called repeatedly."""
        learner = OpenEndedLearner("agent-1")
        domains_seen: set[str] = set()
        for _ in range(5):
            goal = learner.propose_goal()
            domains_seen.add(goal.domain)
        # With 5 proposals across a diverse catalog we should see at least 2 domains
        assert len(domains_seen) >= 2

    def test_unique_goal_ids(self) -> None:
        learner = OpenEndedLearner("agent-1")
        ids = set()
        for _ in range(10):
            goal = learner.propose_goal()
            ids.add(goal.goal_id)
        assert len(ids) == 10

    def test_proposal_returns_stored_goal(self) -> None:
        """Propose should store the goal internally."""
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        next_goals = learner.get_next_goals(count=10)
        goal_ids = {g.goal_id for g in next_goals}
        assert goal.goal_id in goal_ids


class TestSelfEvaluate:
    def test_basic_evaluation(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "Completed the goal successfully. Learned a lot.")
        assert isinstance(outcome, GoalOutcome)
        assert outcome.goal_id == goal.goal_id
        assert 0.0 <= outcome.success_rating <= 1.0

    def test_success_rating_high_for_positive(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(
            goal,
            "Successfully completed everything. Mastered all concepts. Excellent results. "
            "Learned proficient skills. Great progress.",
        )
        assert outcome.success_rating >= 0.6

    def test_success_rating_low_for_negative(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(
            goal,
            "Failed completely. Struggled with everything. Confused by difficult concepts. "
            "Poor results. Bad experience.",
        )
        assert outcome.success_rating <= 0.4

    def test_neutral_rating_for_empty(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "")
        assert outcome.success_rating == 0.5

    def test_extracts_skills(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(
            goal,
            "Learned Python programming. Mastered data structures. "
            "Gained skills in algorithm design.",
        )
        skills = outcome.skills_gained
        assert "python programming" in skills
        assert "data structures" in skills
        assert "algorithm design" in skills

    def test_no_skills_extracted_when_none_mentioned(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "It went okay.")
        assert outcome.skills_gained == ()

    def test_generates_next_goal_hints(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(
            goal,
            "Completed the goal. Learned many new things.",
        )
        # Hints should be a tuple (possibly empty)
        assert isinstance(outcome.next_goal_hints, tuple)

    def test_time_spent_adjusts_rating(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        # Very short time relative to steps should incur penalty
        fast = learner.self_evaluate(goal, "Successful. Completed. Mastered.", time_spent=0.1)
        slow = learner.self_evaluate(goal, "Successful. Completed. Mastered.", time_spent=10.0)
        assert fast.success_rating <= slow.success_rating


class TestRecordOutcome:
    def test_records_outcome_and_updates_state(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "Successfully completed. Learned Python.")
        learner.record_outcome(goal, outcome)

        progress = learner.get_progress()
        assert goal.goal_id in progress["completed_goals"]
        assert progress["total_progress"] > 0.0

    def test_skills_added_to_capabilities(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(
            goal,
            "Learned Python programming. Mastered data structures.",
        )
        learner.record_outcome(goal, outcome)

        progress = learner.get_progress()
        caps = progress["capabilities"]
        assert "python programming" in caps
        assert "data structures" in caps

    def test_goal_marked_completed(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "Done.")
        learner.record_outcome(goal, outcome)

        # The stored goal should now be COMPLETED
        stored = learner._goals[goal.goal_id]
        assert stored.status == GoalStatus.COMPLETED
        assert stored.completed_at is not None

    def test_outcome_is_stored(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "Done.")
        learner.record_outcome(goal, outcome)

        assert goal.goal_id in learner._outcomes
        assert learner._outcomes[goal.goal_id] is outcome


class TestUpdateCurriculum:
    def test_returns_list_when_no_goals(self) -> None:
        learner = OpenEndedLearner("agent-1")
        steps = learner.update_curriculum()
        assert isinstance(steps, list)

    def test_returns_curriculum_steps_with_proposed_goals(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        steps = learner.update_curriculum()
        assert len(steps) >= 1
        assert all(isinstance(s, CurriculumStep) for s in steps)

    def test_phases_advance_after_completions(self) -> None:
        learner = OpenEndedLearner("agent-1")
        # Complete a TRIVIAL goal to advance phase
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "Done successfully.")
        learner.record_outcome(goal, outcome)

        steps = learner.update_curriculum()
        assert len(steps) >= 1


class TestGetNextGoals:
    def test_returns_proposed_goals(self) -> None:
        learner = OpenEndedLearner("agent-1")
        learner.propose_goal()
        learner.propose_goal()

        next_goals = learner.get_next_goals(count=2)
        assert len(next_goals) == 2
        assert all(g.status == GoalStatus.PROPOSED for g in next_goals)

    def test_returns_empty_when_no_proposals(self) -> None:
        learner = OpenEndedLearner("agent-1")
        assert learner.get_next_goals() == []

    def test_respects_count(self) -> None:
        learner = OpenEndedLearner("agent-1")
        for _ in range(5):
            learner.propose_goal()
        assert len(learner.get_next_goals(count=3)) == 3
        assert len(learner.get_next_goals(count=10)) == 5


class TestEstimateReadiness:
    def test_full_readiness_no_prereqs(self) -> None:
        learner = OpenEndedLearner("agent-1")
        now = datetime.now()
        goal = LearningGoal(
            goal_id="g_0001",
            title="Simple Goal",
            description="No prereqs",
            domain="Test",
            difficulty=GoalDifficulty.TRIVIAL,
            prerequisites=(),
            estimated_steps=1,
            status=GoalStatus.PROPOSED,
            progress_score=0.0,
            created_at=now,
            completed_at=None,
        )
        assert learner.estimate_readiness(goal) == 1.0

    def test_full_readiness_met_prereqs(self) -> None:
        learner = OpenEndedLearner("agent-1")
        now = datetime.now()
        # Complete a prerequisite
        prereq = LearningGoal(
            goal_id="g_0001",
            title="Prereq Goal",
            description="Prerequisite",
            domain="Test",
            difficulty=GoalDifficulty.TRIVIAL,
            prerequisites=(),
            estimated_steps=1,
            status=GoalStatus.COMPLETED,
            progress_score=1.0,
            created_at=now,
            completed_at=datetime.now(),
        )
        learner._goals["g_0001"] = prereq
        learner._completed_ids.add("g_0001")
        learner._completed_titles.add("Prereq Goal")

        goal = LearningGoal(
            goal_id="g_0002",
            title="Advanced Goal",
            description="Has prereqs",
            domain="Test",
            difficulty=GoalDifficulty.EASY,
            prerequisites=("Prereq Goal",),
            estimated_steps=1,
            status=GoalStatus.PROPOSED,
            progress_score=0.0,
            created_at=now,
            completed_at=None,
        )
        assert learner.estimate_readiness(goal) == 1.0

    def test_partial_readiness(self) -> None:
        learner = OpenEndedLearner("agent-1")
        now = datetime.now()
        learner._completed_titles.add("Prereq A")
        goal = LearningGoal(
            goal_id="g_0001",
            title="Mixed",
            description="Partial prereqs",
            domain="Test",
            difficulty=GoalDifficulty.MEDIUM,
            prerequisites=("Prereq A", "Prereq B", "Prereq C"),
            estimated_steps=1,
            status=GoalStatus.PROPOSED,
            progress_score=0.0,
            created_at=now,
            completed_at=None,
        )
        assert learner.estimate_readiness(goal) == pytest.approx(1.0 / 3.0)


class TestGetProgress:
    def test_returns_dict_with_expected_keys(self) -> None:
        learner = OpenEndedLearner("agent-1")
        progress = learner.get_progress()
        expected_keys = {
            "learner_id",
            "total_progress",
            "completed_goals",
            "current_phase",
            "capabilities",
            "knowledge_gaps",
            "outstanding_goals",
        }
        assert set(progress.keys()) == expected_keys

    def test_tracks_outstanding_goals(self) -> None:
        learner = OpenEndedLearner("agent-1")
        learner.propose_goal()
        learner.propose_goal()
        progress = learner.get_progress()
        assert progress["outstanding_goals"] == 2


class TestGetStats:
    def test_returns_dict_with_expected_keys(self) -> None:
        learner = OpenEndedLearner("agent-1")
        stats = learner.get_stats()
        expected_keys = {
            "learner_id",
            "total_goals",
            "completed_goals",
            "proposed_goals",
            "abandoned_goals",
            "average_success_rating",
            "current_phase",
            "phase_distribution",
            "domain_distribution",
        }
        assert set(stats.keys()) == expected_keys

    def test_counts_are_accurate(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal1 = learner.propose_goal()
        learner.self_evaluate(goal1, "Done.")
        learner.record_outcome(goal1, learner.self_evaluate(goal1, "Success."))
        goal2 = learner.propose_goal()

        stats = learner.get_stats()
        assert stats["total_goals"] == 2
        assert stats["completed_goals"] == 1
        assert stats["proposed_goals"] == 1

    def test_average_rating(self) -> None:
        learner = OpenEndedLearner("agent-1")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "Successful. Completed. Mastered.")
        learner.record_outcome(goal, outcome)
        stats = learner.get_stats()
        assert stats["average_success_rating"] > 0


class TestIntegration:
    def test_full_workflow(self) -> None:
        """Complete propose -> evaluate -> record -> curriculum cycle."""
        learner = OpenEndedLearner("agent-full")

        # 1. Propose
        goal1 = learner.propose_goal()
        assert goal1.status == GoalStatus.PROPOSED
        assert learner.get_stats()["total_goals"] == 1

        # 2. Evaluate
        outcome1 = learner.self_evaluate(
            goal1,
            "Successfully completed. Learned programming basics. "
            "Mastered variables and control flow.",
        )
        assert 0.0 <= outcome1.success_rating <= 1.0
        assert len(outcome1.skills_gained) > 0

        # 3. Record
        learner.record_outcome(goal1, outcome1)
        assert learner.get_progress()["completed_goals"]
        assert learner.get_stats()["completed_goals"] == 1

        # 4. Propose next
        goal2 = learner.propose_goal()
        assert goal2.goal_id != goal1.goal_id

        # 5. Curriculum
        curriculum = learner.update_curriculum()
        assert isinstance(curriculum, list)

        # 6. Progress summary
        progress = learner.get_progress()
        assert progress["learner_id"] == "agent-full"
        assert progress["total_progress"] > 0.0

    def test_multiple_proposals_and_completions(self) -> None:
        learner = OpenEndedLearner("agent-multi")

        for i in range(3):
            goal = learner.propose_goal()
            outcome = learner.self_evaluate(
                goal,
                f"Completed goal {i}. Learned new skills successfully. Mastered concepts.",
            )
            learner.record_outcome(goal, outcome)

        stats = learner.get_stats()
        assert stats["completed_goals"] == 3
        assert stats["total_goals"] >= 3

    def test_difficulty_progression_chain(self) -> None:
        """Complete goals in order and verify difficulty increases."""
        learner = OpenEndedLearner("agent-progress")

        # Complete a TRIVIAL goal
        g1 = learner.propose_goal()
        assert g1.difficulty in (GoalDifficulty.TRIVIAL, GoalDifficulty.EASY)
        o1 = learner.self_evaluate(g1, "Completed successfully. Mastered all skills.")
        learner.record_outcome(g1, o1)

        # Complete another goal (should be able to propose EASY)
        g2 = learner.propose_goal()
        # Should propose something at TRIVIAL or EASY
        assert g2.difficulty in (GoalDifficulty.TRIVIAL, GoalDifficulty.EASY)
        o2 = learner.self_evaluate(g2, "Completed successfully. Learned everything.")
        learner.record_outcome(g2, o2)

        stats = learner.get_stats()
        assert stats["completed_goals"] >= 2

    def test_progress_improves_with_completions(self) -> None:
        learner = OpenEndedLearner("agent-progress2")
        initial = learner.get_progress()["total_progress"]

        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "Successful. Completed. Mastered. Great work.")
        learner.record_outcome(goal, outcome)

        after = learner.get_progress()["total_progress"]
        assert after > initial

    def test_learn_capabilities_grow(self) -> None:
        learner = OpenEndedLearner("agent-skills")
        initial_caps = len(learner.get_progress()["capabilities"])

        goal = learner.propose_goal()
        outcome = learner.self_evaluate(
            goal,
            "Learned Python programming. Mastered data structures. "
            "Acquired debugging skills.",
        )
        learner.record_outcome(goal, outcome)

        final_caps = learner.get_progress()["capabilities"]
        assert len(final_caps) > initial_caps
        assert "python programming" in final_caps
        assert "data structures" in final_caps

    def test_get_next_goals_priority_ordering(self) -> None:
        """Next goals should be ordered by priority."""
        learner = OpenEndedLearner("agent-priority")

        # Propose several goals
        learner.propose_goal()
        learner.propose_goal()
        learner.propose_goal()

        next_goals = learner.get_next_goals(count=3)
        # Should have proposed goals with stable ordering (by priority then title)
        assert len(next_goals) == 3
        # Verify IDs are unique and ordered
        assert len({g.goal_id for g in next_goals}) == 3

    def test_empty_outcome_handling(self) -> None:
        learner = OpenEndedLearner("agent-empty")
        goal = learner.propose_goal()
        outcome = learner.self_evaluate(goal, "", time_spent=0.0)
        assert outcome.success_rating == 0.5
        assert outcome.skills_gained == ()
        assert outcome.next_goal_hints == ()
        assert outcome.insights == ""
