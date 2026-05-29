from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "GoalStatus",
    "GoalDifficulty",
    "CurriculumPhase",
    "LearningGoal",
    "GoalOutcome",
    "CurriculumStep",
    "LearnerProfile",
    "OpenEndedLearner",
]

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GoalStatus(str, Enum):
    """Status of a learning goal."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    SUPERSEDED = "superseded"


class GoalDifficulty(str, Enum):
    """Difficulty level of a learning goal."""

    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class CurriculumPhase(str, Enum):
    """Phase of a curriculum."""

    FOUNDATIONS = "foundations"
    CORE = "core"
    ADVANCED = "advanced"
    SPECIALIZED = "specialized"
    FRONTIER = "frontier"


# ---------------------------------------------------------------------------
# Public frozen dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LearningGoal:
    """A single learning objective with metadata.

    Parameters
    ----------
    goal_id : str
        Unique identifier for this goal.
    title : str
        Human-readable title.
    description : str
        Detailed description of what the goal entails.
    domain : str
        Subject domain (e.g. "Mathematics", "Programming").
    difficulty : GoalDifficulty
        Difficulty level.
    prerequisites : tuple[str, ...]
        Titles of goals that should be completed first.
    estimated_steps : int
        Estimated number of study sessions or steps.
    status : GoalStatus
        Current lifecycle status.
    progress_score : float
        Score from 0.0 to 1.0 indicating progress.
    created_at : datetime
        Timestamp when the goal was created.
    completed_at : datetime | None
        Timestamp when the goal was completed, or None.
    """

    goal_id: str
    title: str
    description: str
    domain: str
    difficulty: GoalDifficulty
    prerequisites: tuple[str, ...]
    estimated_steps: int
    status: GoalStatus
    progress_score: float
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class GoalOutcome:
    """Structured result of self-evaluation for a completed goal.

    Parameters
    ----------
    goal_id : str
        Identifier of the goal this outcome is for.
    success_rating : float
        Self-assessed success rating from 0.0 to 1.0.
    time_spent_seconds : float
        Time spent working on the goal in seconds.
    skills_gained : tuple[str, ...]
        Skills extracted from the outcome description.
    insights : str
        Free-text insights from the evaluation.
    next_goal_hints : tuple[str, ...]
        Suggested next goals based on this outcome.
    """

    goal_id: str
    success_rating: float
    time_spent_seconds: float
    skills_gained: tuple[str, ...]
    insights: str
    next_goal_hints: tuple[str, ...]


@dataclass(frozen=True)
class CurriculumStep:
    """A phase-aligned set of learning goals.

    Parameters
    ----------
    step_id : str
        Unique identifier for this step.
    phase : CurriculumPhase
        The curriculum phase this step belongs to.
    goals : tuple[LearningGoal, ...]
        Learning goals in this step.
    estimated_duration_hours : float
        Total estimated time for this step in hours.
    review_criteria : str
        Criteria for considering this step complete.
    """

    step_id: str
    phase: CurriculumPhase
    goals: tuple[LearningGoal, ...]
    estimated_duration_hours: float
    review_criteria: str


@dataclass(frozen=True)
class LearnerProfile:
    """Snapshot of learner state.

    Parameters
    ----------
    learner_id : str
        Unique identifier for the learner.
    capabilities : tuple[str, ...]
        Current known capabilities sorted alphabetically.
    knowledge_gaps : tuple[str, ...]
        Identified knowledge gaps sorted alphabetically.
    completed_goals : tuple[str, ...]
        Goal IDs of completed goals sorted alphabetically.
    total_progress : float
        Aggregate progress score from 0.0 to 1.0.
    current_phase : CurriculumPhase
        Current curriculum phase.
    """

    learner_id: str
    capabilities: tuple[str, ...]
    knowledge_gaps: tuple[str, ...]
    completed_goals: tuple[str, ...]
    total_progress: float
    current_phase: CurriculumPhase


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DIFFICULTY_ORDER: list[GoalDifficulty] = [
    GoalDifficulty.TRIVIAL,
    GoalDifficulty.EASY,
    GoalDifficulty.MEDIUM,
    GoalDifficulty.HARD,
    GoalDifficulty.EXPERT,
]

_PHASE_ORDER: list[CurriculumPhase] = [
    CurriculumPhase.FOUNDATIONS,
    CurriculumPhase.CORE,
    CurriculumPhase.ADVANCED,
    CurriculumPhase.SPECIALIZED,
    CurriculumPhase.FRONTIER,
]

_POSITIVE_KEYWORDS: frozenset[str] = frozenset({
    "successful",
    "completed",
    "understood",
    "mastered",
    "learned",
    "implemented",
    "solved",
    "achieved",
    "excellent",
    "great",
    "smooth",
    "easy",
    "straightforward",
    "confident",
    "proficient",
    "accomplished",
    "grasped",
    "fluent",
})

_NEGATIVE_KEYWORDS: frozenset[str] = frozenset({
    "failed",
    "struggled",
    "confused",
    "unclear",
    "difficult",
    "incomplete",
    "unresolved",
    "stuck",
    "poor",
    "bad",
    "unsure",
    "challenging",
    "overwhelming",
    "error",
    "bug",
    "problem",
    "lost",
})


def _difficulty_to_phase(difficulty: GoalDifficulty) -> CurriculumPhase:
    """Map a goal difficulty to the corresponding curriculum phase."""
    idx = _DIFFICULTY_ORDER.index(difficulty)
    return _PHASE_ORDER[idx]


# ---------------------------------------------------------------------------
# Internal goal template
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _GoalTemplate:
    """Template for generating learning goals."""

    title: str
    description: str
    domain: str
    difficulty: GoalDifficulty
    prerequisites: tuple[str, ...]
    estimated_steps: int


_GOAL_CATALOG: list[_GoalTemplate] = [
    # Mathematics
    _GoalTemplate(
        "Basic Arithmetic Operations",
        "Learn fundamental arithmetic: addition, subtraction, multiplication, and division",
        "Mathematics",
        GoalDifficulty.TRIVIAL,
        (),
        1,
    ),
    _GoalTemplate(
        "Fundamental Algebra",
        "Understand variables, equations, and algebraic expressions",
        "Mathematics",
        GoalDifficulty.EASY,
        ("Basic Arithmetic Operations",),
        3,
    ),
    _GoalTemplate(
        "Introduction to Geometry",
        "Study shapes, angles, and basic geometric proofs",
        "Mathematics",
        GoalDifficulty.EASY,
        ("Basic Arithmetic Operations",),
        3,
    ),
    _GoalTemplate(
        "Calculus Fundamentals",
        "Learn limits, derivatives, and integrals",
        "Mathematics",
        GoalDifficulty.MEDIUM,
        ("Fundamental Algebra",),
        5,
    ),
    _GoalTemplate(
        "Probability Theory",
        "Understand probability spaces, random variables, and distributions",
        "Mathematics",
        GoalDifficulty.MEDIUM,
        ("Fundamental Algebra",),
        4,
    ),
    _GoalTemplate(
        "Statistics Essentials",
        "Study descriptive statistics, hypothesis testing, and confidence intervals",
        "Mathematics",
        GoalDifficulty.MEDIUM,
        ("Probability Theory",),
        4,
    ),
    _GoalTemplate(
        "Linear Algebra",
        "Master vectors, matrices, eigenvalues, and linear transformations",
        "Mathematics",
        GoalDifficulty.HARD,
        ("Calculus Fundamentals",),
        6,
    ),
    _GoalTemplate(
        "Advanced Statistics",
        "Study Bayesian inference, ANOVA, and regression analysis",
        "Mathematics",
        GoalDifficulty.HARD,
        ("Statistics Essentials",),
        6,
    ),
    _GoalTemplate(
        "Abstract Mathematics",
        "Explore group theory, ring theory, and mathematical proofs at graduate level",
        "Mathematics",
        GoalDifficulty.EXPERT,
        ("Linear Algebra",),
        8,
    ),
    # Programming
    _GoalTemplate(
        "Programming Basics",
        "Learn variables, data types, and basic program structure",
        "Programming",
        GoalDifficulty.TRIVIAL,
        (),
        2,
    ),
    _GoalTemplate(
        "Control Flow and Functions",
        "Master loops, conditionals, and function definitions",
        "Programming",
        GoalDifficulty.EASY,
        ("Programming Basics",),
        3,
    ),
    _GoalTemplate(
        "Data Structures Introduction",
        "Study arrays, lists, stacks, and queues",
        "Programming",
        GoalDifficulty.EASY,
        ("Programming Basics",),
        4,
    ),
    _GoalTemplate(
        "Object-Oriented Programming",
        "Learn classes, inheritance, polymorphism, and encapsulation",
        "Programming",
        GoalDifficulty.MEDIUM,
        ("Control Flow and Functions",),
        5,
    ),
    _GoalTemplate(
        "Algorithm Design",
        "Study sorting, searching, and graph algorithms",
        "Programming",
        GoalDifficulty.MEDIUM,
        ("Data Structures Introduction",),
        5,
    ),
    _GoalTemplate(
        "Advanced Data Structures",
        "Master trees, hash tables, and balanced data structures",
        "Programming",
        GoalDifficulty.HARD,
        ("Object-Oriented Programming", "Algorithm Design"),
        6,
    ),
    _GoalTemplate(
        "Compiler Design",
        "Study lexical analysis, parsing, and code generation",
        "Programming",
        GoalDifficulty.EXPERT,
        ("Advanced Data Structures",),
        8,
    ),
    # Data Science
    _GoalTemplate(
        "Data Literacy",
        "Understand data types, collection methods, and basic analysis concepts",
        "Data Science",
        GoalDifficulty.TRIVIAL,
        (),
        1,
    ),
    _GoalTemplate(
        "Data Visualization",
        "Create charts, graphs, and dashboards to communicate insights",
        "Data Science",
        GoalDifficulty.EASY,
        ("Data Literacy",),
        3,
    ),
    _GoalTemplate(
        "Exploratory Data Analysis",
        "Apply statistical and visual techniques to explore datasets",
        "Data Science",
        GoalDifficulty.MEDIUM,
        ("Data Visualization",),
        4,
    ),
    _GoalTemplate(
        "Statistical Modeling",
        "Build and validate statistical models from data",
        "Data Science",
        GoalDifficulty.HARD,
        ("Exploratory Data Analysis", "Probability Theory"),
        6,
    ),
    _GoalTemplate(
        "Advanced Analytics",
        "Design complex analytical pipelines and experimental frameworks",
        "Data Science",
        GoalDifficulty.EXPERT,
        ("Statistical Modeling",),
        8,
    ),
    # Machine Learning
    _GoalTemplate(
        "Machine Learning Overview",
        "Survey ML paradigms and fundamental concepts",
        "Machine Learning",
        GoalDifficulty.EASY,
        ("Programming Basics",),
        2,
    ),
    _GoalTemplate(
        "Supervised Learning",
        "Study regression, classification, and supervised algorithms",
        "Machine Learning",
        GoalDifficulty.MEDIUM,
        ("Machine Learning Overview", "Probability Theory"),
        5,
    ),
    _GoalTemplate(
        "Unsupervised Learning",
        "Study clustering, dimensionality reduction, and unsupervised methods",
        "Machine Learning",
        GoalDifficulty.MEDIUM,
        ("Machine Learning Overview",),
        5,
    ),
    _GoalTemplate(
        "Neural Networks",
        "Build and train neural network architectures from scratch",
        "Machine Learning",
        GoalDifficulty.HARD,
        ("Supervised Learning", "Linear Algebra"),
        6,
    ),
    _GoalTemplate(
        "Ensemble Methods",
        "Master random forests, boosting, and bagging techniques",
        "Machine Learning",
        GoalDifficulty.HARD,
        ("Supervised Learning",),
        6,
    ),
    _GoalTemplate(
        "Deep Learning Architectures",
        "Design advanced deep networks including CNNs and RNNs",
        "Machine Learning",
        GoalDifficulty.EXPERT,
        ("Neural Networks",),
        8,
    ),
    # Software Engineering
    _GoalTemplate(
        "Version Control Basics",
        "Learn git fundamentals and collaborative workflows",
        "Software Engineering",
        GoalDifficulty.TRIVIAL,
        (),
        1,
    ),
    _GoalTemplate(
        "Testing Fundamentals",
        "Write unit tests, integration tests, and practice TDD",
        "Software Engineering",
        GoalDifficulty.EASY,
        ("Programming Basics",),
        3,
    ),
    _GoalTemplate(
        "Design Patterns",
        "Study common software design patterns and their applications",
        "Software Engineering",
        GoalDifficulty.MEDIUM,
        ("Object-Oriented Programming",),
        5,
    ),
    _GoalTemplate(
        "System Architecture",
        "Design scalable software systems with clean architecture",
        "Software Engineering",
        GoalDifficulty.HARD,
        ("Design Patterns",),
        7,
    ),
    _GoalTemplate(
        "Distributed Systems",
        "Study consensus algorithms, distributed storage, and fault tolerance",
        "Software Engineering",
        GoalDifficulty.EXPERT,
        ("System Architecture",),
        8,
    ),
    # Systems
    _GoalTemplate(
        "Computer Fundamentals",
        "Understand CPU, memory, storage, and basic hardware concepts",
        "Systems",
        GoalDifficulty.TRIVIAL,
        (),
        1,
    ),
    _GoalTemplate(
        "Operating System Basics",
        "Learn processes, memory management, and file systems",
        "Systems",
        GoalDifficulty.EASY,
        ("Computer Fundamentals",),
        4,
    ),
    _GoalTemplate(
        "Network Protocols",
        "Study TCP/IP, HTTP, DNS, and network architecture",
        "Systems",
        GoalDifficulty.MEDIUM,
        ("Operating System Basics",),
        5,
    ),
    # Natural Language Processing
    _GoalTemplate(
        "Text Processing",
        "Learn tokenization, parsing, and text preprocessing techniques",
        "Natural Language Processing",
        GoalDifficulty.MEDIUM,
        ("Programming Basics",),
        3,
    ),
    _GoalTemplate(
        "Language Models",
        "Study n-grams, embeddings, and sequence models for language",
        "Natural Language Processing",
        GoalDifficulty.HARD,
        ("Text Processing", "Neural Networks"),
        6,
    ),
    _GoalTemplate(
        "Transformer Architectures",
        "Master attention mechanisms and transformer-based models",
        "Natural Language Processing",
        GoalDifficulty.EXPERT,
        ("Language Models",),
        8,
    ),
    # Computer Vision
    _GoalTemplate(
        "Image Processing Basics",
        "Learn filtering, edge detection, and image transformations",
        "Computer Vision",
        GoalDifficulty.MEDIUM,
        ("Programming Basics",),
        4,
    ),
    _GoalTemplate(
        "Computer Vision Models",
        "Study object detection, segmentation, and vision architectures",
        "Computer Vision",
        GoalDifficulty.HARD,
        ("Image Processing Basics", "Neural Networks"),
        6,
    ),
    _GoalTemplate(
        "Generative Vision Models",
        "Master GANs, diffusion models, and vision transformers",
        "Computer Vision",
        GoalDifficulty.EXPERT,
        ("Computer Vision Models",),
        8,
    ),
    # Reinforcement Learning
    _GoalTemplate(
        "RL Fundamentals",
        "Learn Markov decision processes, value functions, and policies",
        "Reinforcement Learning",
        GoalDifficulty.MEDIUM,
        ("Probability Theory",),
        4,
    ),
    _GoalTemplate(
        "Deep Reinforcement Learning",
        "Study DQN, policy gradients, and actor-critic methods",
        "Reinforcement Learning",
        GoalDifficulty.HARD,
        ("RL Fundamentals", "Neural Networks"),
        6,
    ),
    _GoalTemplate(
        "Advanced RL",
        "Explore multi-agent RL, inverse RL, and model-based methods",
        "Reinforcement Learning",
        GoalDifficulty.EXPERT,
        ("Deep Reinforcement Learning",),
        8,
    ),
]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class OpenEndedLearner:
    """Self-directed open-ended learner.

    Proposes learning goals based on domain-coverage gaps, difficulty
    progression, and prerequisite chains. Supports self-evaluation outcome
    analysis and curriculum generation.

    Parameters
    ----------
    learner_id : str
        Unique identifier for this learner.
    capabilities : tuple[str, ...] | None
        Initial set of known capabilities. Defaults to ``("basic_literacy",)``.

    Examples
    --------
    >>> learner = OpenEndedLearner("agent-1")
    >>> goal = learner.propose_goal()
    >>> outcome = learner.self_evaluate(goal, "Successfully completed.")
    >>> learner.record_outcome(goal, outcome)
    """

    def __init__(self, learner_id: str, capabilities: tuple[str, ...] | None = None) -> None:
        self._learner_id = learner_id
        self._initial_capabilities: tuple[str, ...] = (
            tuple(sorted(capabilities)) if capabilities else ("basic_literacy",)
        )
        self._capabilities: set[str] = set(self._initial_capabilities)
        self._goals: dict[str, LearningGoal] = {}
        self._outcomes: dict[str, GoalOutcome] = {}
        self._completed_ids: set[str] = set()
        self._completed_titles: set[str] = set()
        self._goal_counter = 0
        self._current_phase = CurriculumPhase.FOUNDATIONS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def propose_goal(
        self,
        domain: str | None = None,
        difficulty: str | None = None,
    ) -> LearningGoal:
        """Propose a new learning goal.

        Uses heuristics based on domain-coverage gaps, difficulty progression,
        and prerequisite chains when *domain* and *difficulty* are not
        specified.

        Parameters
        ----------
        domain : str | None
            Restrict proposal to a specific domain.
        difficulty : str | None
            Restrict proposal to a specific difficulty level.

        Returns
        -------
        LearningGoal
            A newly proposed goal with status ``PROPOSED``.
        """
        diff_enum: GoalDifficulty | None = GoalDifficulty(difficulty) if difficulty else None

        reachable = self._reachable_difficulties()
        unavailable_titles = self._unavailable_titles()
        completed_titles_set = self._completed_titles.copy()
        domain_counts = self._domain_goal_counts()

        candidates: list[tuple[int, str, _GoalTemplate]] = []

        for tmpl in _GOAL_CATALOG:
            if tmpl.title in unavailable_titles:
                continue
            if domain is not None and tmpl.domain != domain:
                continue
            if diff_enum is not None and tmpl.difficulty != diff_enum:
                continue
            if tmpl.difficulty not in reachable:
                continue

            # Prerequisites must all be satisfied.
            prereqs_met = all(p in completed_titles_set for p in tmpl.prerequisites)
            if not prereqs_met:
                continue

            score = 0

            # Base score for an available goal
            score += 100

            # Domain-diversity bonus: prefer underrepresented domains
            dc = domain_counts.get(tmpl.domain, 0)
            score += max(0, 20 - dc * 5)

            # Difficulty appropriateness: prefer next-level-up
            target_idx = _DIFFICULTY_ORDER.index(tmpl.difficulty)
            max_completed_idx = self._max_completed_idx()
            if target_idx == max_completed_idx + 1:
                score += 30
            elif target_idx <= max_completed_idx:
                score += 10

            # Stable tiebreaker: title alphabetically
            candidates.append((score, tmpl.title, tmpl))

        if not candidates:
            fallback_domain = domain or "General"
            fallback_diff = diff_enum or GoalDifficulty.TRIVIAL
            # Ensure fallback difficulty is within reachable bounds
            if fallback_diff not in reachable:
                fallback_diff = reachable[0] if reachable else GoalDifficulty.TRIVIAL
            return self._make_and_store_goal(
                title=f"Explore {fallback_domain}",
                description=f"General exploration of {fallback_domain}",
                domain=fallback_domain,
                difficulty=fallback_diff,
                prerequisites=(),
                estimated_steps=1,
            )

        # Sort descending by score, then ascending by title (stable)
        candidates.sort(key=lambda x: (-x[0], x[1]))
        _, _, best_tmpl = candidates[0]

        return self._make_and_store_goal(
            title=best_tmpl.title,
            description=best_tmpl.description,
            domain=best_tmpl.domain,
            difficulty=best_tmpl.difficulty,
            prerequisites=best_tmpl.prerequisites,
            estimated_steps=best_tmpl.estimated_steps,
        )

    def self_evaluate(
        self,
        goal: LearningGoal,
        outcome_description: str,
        time_spent: float = 0.0,
    ) -> GoalOutcome:
        """Self-evaluate progress toward a goal from an outcome description.

        Performs keyword-based sentiment analysis to derive a success rating,
        extracts skill names from the text, and generates next-goal hints.

        Parameters
        ----------
        goal : LearningGoal
            The goal being evaluated.
        outcome_description : str
            Free-text description of the outcome.
        time_spent : float
            Time spent on the goal in seconds.

        Returns
        -------
        GoalOutcome
            Structured evaluation result.
        """
        success_rating = self._calculate_success_rating(outcome_description, time_spent, goal.estimated_steps)
        skills = self._extract_skills(outcome_description)
        hints = self._generate_next_hints(outcome_description, goal.domain)

        return GoalOutcome(
            goal_id=goal.goal_id,
            success_rating=success_rating,
            time_spent_seconds=time_spent,
            skills_gained=skills,
            insights=outcome_description.strip(),
            next_goal_hints=hints,
        )

    def update_curriculum(self) -> list[CurriculumStep]:
        """Auto-generate a curriculum based on completed goals.

        Determines the current phase from the highest-difficulty completed
        goal and groups goals (proposed, active, and completed) into phase-
        aligned curriculum steps.

        Returns
        -------
        list[CurriculumStep]
            Steps covering all phases with associated goals.
        """
        steps: list[CurriculumStep] = []

        # Determine and update current phase from completed goals
        max_idx = self._max_completed_idx()
        if max_idx >= 0:
            new_phase = _difficulty_to_phase(_DIFFICULTY_ORDER[max_idx])
            new_phase_idx = _PHASE_ORDER.index(new_phase)
            current_phase_idx = _PHASE_ORDER.index(self._current_phase)
            if new_phase_idx > current_phase_idx:
                self._current_phase = new_phase

        # Group goals by the phase their difficulty maps to
        phase_goal_map: dict[CurriculumPhase, list[LearningGoal]] = {p: [] for p in CurriculumPhase}
        for g in self._goals.values():
            phase = _difficulty_to_phase(g.difficulty)
            phase_goal_map[phase].append(g)

        # Create steps (stable phase order)
        for phase in _PHASE_ORDER:
            goals_in_phase = phase_goal_map.get(phase, [])
            if goals_in_phase:
                sorted_goals = tuple(sorted(goals_in_phase, key=lambda g: g.goal_id))
                total_hours = sum(g.estimated_steps * 2.0 for g in sorted_goals)
                steps.append(
                    CurriculumStep(
                        step_id=f"cur_{phase.value}_{self._learner_id}",
                        phase=phase,
                        goals=sorted_goals,
                        estimated_duration_hours=total_hours,
                        review_criteria=(
                            f"Complete all {phase.value} learning goals"
                            f" with satisfactory outcomes"
                        ),
                    )
                )

        return steps

    def record_outcome(self, goal: LearningGoal, outcome: GoalOutcome) -> None:
        """Record a completed goal outcome and update learner state.

        Marks the goal as completed, stores the outcome, and enriches the
        learner's capability set with extracted skills.

        Parameters
        ----------
        goal : LearningGoal
            The goal that was completed.
        outcome : GoalOutcome
            The outcome to record.
        """
        completed_goal = LearningGoal(
            goal_id=goal.goal_id,
            title=goal.title,
            description=goal.description,
            domain=goal.domain,
            difficulty=goal.difficulty,
            prerequisites=goal.prerequisites,
            estimated_steps=goal.estimated_steps,
            status=GoalStatus.COMPLETED,
            progress_score=outcome.success_rating,
            created_at=goal.created_at,
            completed_at=datetime.now(),
        )
        self._goals[goal.goal_id] = completed_goal
        self._outcomes[goal.goal_id] = outcome
        self._completed_ids.add(goal.goal_id)
        self._completed_titles.add(goal.title)

        for skill in outcome.skills_gained:
            self._capabilities.add(skill)

    def get_next_goals(self, count: int = 3) -> list[LearningGoal]:
        """Return the next *count* proposed goals sorted by priority.

        Priority is computed from domain diversity, difficulty appropriateness,
        and prerequisite satisfaction.

        Parameters
        ----------
        count : int
            Maximum number of goals to return.

        Returns
        -------
        list[LearningGoal]
            Proposed goals sorted descending by priority.
        """
        proposed = [g for g in self._goals.values() if g.status == GoalStatus.PROPOSED]
        if not proposed:
            return []

        completed_titles = self._completed_titles.copy()
        domain_counts = self._domain_goal_counts()
        max_completed_idx = self._max_completed_idx()

        scored: list[tuple[int, str, LearningGoal]] = []
        for g in proposed:
            score = 0
            dc = domain_counts.get(g.domain, 0)
            score += max(0, 20 - dc * 5)

            target_idx = _DIFFICULTY_ORDER.index(g.difficulty)
            if target_idx == max_completed_idx + 1:
                score += 30
            elif target_idx <= max_completed_idx:
                score += 10

            prereqs_met = all(p in completed_titles for p in g.prerequisites)
            if prereqs_met:
                score += 50

            scored.append((score, g.title, g))

        # Stable sort: descending score, ascending title
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [g for _, _, g in scored[:count]]

    def estimate_readiness(self, goal: LearningGoal) -> float:
        """Estimate readiness for a goal from 0.0 to 1.0.

        Readiness is the fraction of prerequisites that have been completed.

        Parameters
        ----------
        goal : LearningGoal
            The goal to evaluate readiness for.

        Returns
        -------
        float
            Readiness score between 0.0 and 1.0.
        """
        if not goal.prerequisites:
            return 1.0
        met = sum(1 for p in goal.prerequisites if p in self._completed_titles)
        return met / len(goal.prerequisites)

    def get_progress(self) -> dict[str, Any]:
        """Return a summary of learner progress.

        Returns
        -------
        dict[str, Any]
            Progress summary with keys ``learner_id``, ``total_progress``,
            ``completed_goals``, ``current_phase``, ``capabilities``,
            ``knowledge_gaps``, and ``outstanding_goals``.
        """
        len(self._completed_ids)
        total_goals = len(self._goals)
        total_progress = 0.0
        if total_goals > 0:
            total_progress = sum(
                g.progress_score for g in self._goals.values() if g.status == GoalStatus.COMPLETED
            ) / max(total_goals, 1)

        completed_goal_ids = tuple(sorted(self._completed_ids))
        capabilities = tuple(sorted(self._capabilities))
        knowledge_gaps = self._identify_knowledge_gaps()

        outstanding = [
            g for g in self._goals.values()
            if g.status in (GoalStatus.PROPOSED, GoalStatus.ACTIVE)
        ]

        return {
            "learner_id": self._learner_id,
            "total_progress": round(total_progress, 2),
            "completed_goals": completed_goal_ids,
            "current_phase": self._current_phase.value,
            "capabilities": capabilities,
            "knowledge_gaps": knowledge_gaps,
            "outstanding_goals": len(outstanding),
        }

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics for the learner.

        Returns
        -------
        dict[str, Any]
            Statistics including counts, average ratings, phase distribution,
            and domain distribution.
        """
        all_goals = list(self._goals.values())
        completed_goals = [g for g in all_goals if g.status == GoalStatus.COMPLETED]
        proposed_goals = [g for g in all_goals if g.status == GoalStatus.PROPOSED]
        abandoned_goals = [g for g in all_goals if g.status == GoalStatus.ABANDONED]

        avg_rating = 0.0
        if completed_goals and self._outcomes:
            ratings = [
                self._outcomes[g.goal_id].success_rating
                for g in completed_goals
                if g.goal_id in self._outcomes
            ]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)

        phase_distribution: dict[str, int] = {}
        for g in all_goals:
            phase = _difficulty_to_phase(g.difficulty).value
            phase_distribution[phase] = phase_distribution.get(phase, 0) + 1

        domain_distribution: dict[str, int] = {}
        for g in all_goals:
            domain_distribution[g.domain] = domain_distribution.get(g.domain, 0) + 1

        return {
            "learner_id": self._learner_id,
            "total_goals": len(all_goals),
            "completed_goals": len(completed_goals),
            "proposed_goals": len(proposed_goals),
            "abandoned_goals": len(abandoned_goals),
            "average_success_rating": round(avg_rating, 2),
            "current_phase": self._current_phase.value,
            "phase_distribution": dict(sorted(phase_distribution.items())),
            "domain_distribution": dict(sorted(domain_distribution.items())),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_goal_id(self) -> str:
        self._goal_counter += 1
        return f"g_{self._goal_counter:04d}"

    def _make_and_store_goal(
        self,
        title: str,
        description: str,
        domain: str,
        difficulty: GoalDifficulty,
        prerequisites: tuple[str, ...],
        estimated_steps: int,
    ) -> LearningGoal:
        goal_id = self._next_goal_id()
        goal = LearningGoal(
            goal_id=goal_id,
            title=title,
            description=description,
            domain=domain,
            difficulty=difficulty,
            prerequisites=prerequisites,
            estimated_steps=estimated_steps,
            status=GoalStatus.PROPOSED,
            progress_score=0.0,
            created_at=datetime.now(),
            completed_at=None,
        )
        self._goals[goal_id] = goal
        return goal

    def _reachable_difficulties(self) -> list[GoalDifficulty]:
        """Return difficulty levels the learner can currently attempt."""
        max_idx = self._max_completed_idx()
        if max_idx < 0:
            return _DIFFICULTY_ORDER[:2]  # TRIVIAL and EASY
        return _DIFFICULTY_ORDER[: max_idx + 2]

    def _max_completed_idx(self) -> int:
        max_idx = -1
        for g in self._goals.values():
            if g.status == GoalStatus.COMPLETED:
                idx = _DIFFICULTY_ORDER.index(g.difficulty)
                if idx > max_idx:
                    max_idx = idx
        return max_idx

    def _unavailable_titles(self) -> set[str]:
        completed = {g.title for g in self._goals.values() if g.status == GoalStatus.COMPLETED}
        proposed = {g.title for g in self._goals.values() if g.status == GoalStatus.PROPOSED}
        return completed | proposed

    def _domain_goal_counts(self) -> Counter[str]:
        counts: Counter[str] = Counter()
        for g in self._goals.values():
            if g.status in (GoalStatus.COMPLETED, GoalStatus.ACTIVE, GoalStatus.PROPOSED):
                counts[g.domain] += 1
        return counts

    def _identify_knowledge_gaps(self) -> tuple[str, ...]:
        """Identify domains with no completed or proposed goals.

        Returns
        -------
        tuple[str, ...]
            Domain names sorted alphabetically that represent knowledge gaps.
        """
        catalog_domains: set[str] = set()
        domain_has_goals: set[str] = set()
        for t in _GOAL_CATALOG:
            catalog_domains.add(t.domain)
        for g in self._goals.values():
            if g.status in (GoalStatus.COMPLETED, GoalStatus.ACTIVE, GoalStatus.PROPOSED):
                domain_has_goals.add(g.domain)
        gaps = sorted(catalog_domains - domain_has_goals)
        return tuple(gaps)

    @staticmethod
    def _calculate_success_rating(
        outcome_description: str,
        time_spent: float,
        estimated_steps: int,
    ) -> float:
        """Calculate a 0.0-1.0 rating from keyword sentiment and time."""
        words = set(re.findall(r"\b[a-zA-Z]+\b", outcome_description.lower()))
        pos = sum(1 for w in words if w in _POSITIVE_KEYWORDS)
        neg = sum(1 for w in words if w in _NEGATIVE_KEYWORDS)
        total = pos + neg

        base = 0.5
        if total > 0:
            base = pos / total

        penalty = 0.0
        if estimated_steps > 0 and time_spent > 0:
            ratio = time_spent / estimated_steps
            if ratio < 0.3:
                penalty = 0.2
            elif ratio > 3.0:
                penalty = 0.15

        return round(max(0.0, min(1.0, base - penalty)), 2)

    @staticmethod
    def _extract_skills(text: str) -> tuple[str, ...]:
        """Extract skill names from outcome text using patterns."""
        extracted: set[str] = set()
        patterns = [
            r"(?:learned|mastered|studied|practiced|completed)\s+([A-Za-z][A-Za-z\s]{1,40}?)(?:\.|,|;|$|\sand\s)",
            r"(?:skill(?:s)?)\s+(?:in|with|using)\s+([A-Za-z][A-Za-z\s]{1,40}?)(?:\.|,|;|$|\sand\s)",
            r"(?:understanding|knowledge)\s+(?:of|in)\s+([A-Za-z][A-Za-z\s]{1,40}?)(?:\.|,|;|$|\sand\s)",
            r"(?:now\s+)?understand\s+([A-Za-z][A-Za-z\s]{1,40}?)(?:\.|,|;|$|\sand\s)",
            r"(?:gained|developed|acquired)\s+([A-Za-z][A-Za-z\s]{1,40}?)(?:\.|,|;|$|\sand\s)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                skill = match.group(1).strip().lower()
                if len(skill) > 2:
                    extracted.add(skill)
        return tuple(sorted(extracted))

    def _generate_next_hints(self, outcome_description: str, domain: str) -> tuple[str, ...]:
        """Generate suggestions for next goals based on outcome and domain."""
        if not outcome_description.strip():
            return ()

        completed_titles = self._completed_titles.copy()
        proposed_titles = {g.title for g in self._goals.values() if g.status == GoalStatus.PROPOSED}
        unavailable = completed_titles | proposed_titles

        related = [
            t.title
            for t in _GOAL_CATALOG
            if t.domain == domain and t.title not in unavailable
        ]
        related.sort()
        return tuple(related[:3])
