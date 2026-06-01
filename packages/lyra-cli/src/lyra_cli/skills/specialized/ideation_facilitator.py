"""
Ideation Facilitator Skill - Creative ideation and brainstorming facilitation.

Given a problem or opportunity, produces:
- Structured brainstorming session plan
- Idea generation techniques
- Idea evaluation criteria
- Prioritization framework
- Action plan for top ideas

Outputs structured ideation plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IdeationTechnique(StrEnum):
    """Brainstorming techniques."""

    BRAINSTORMING = "brainstorming"
    BRAINWRITING = "brainwriting"
    SCAMPER = "scamper"
    SIX_THINKING_HATS = "six_thinking_hats"
    MIND_MAPPING = "mind_mapping"
    REVERSE_BRAINSTORMING = "reverse_brainstorming"


@dataclass(frozen=True)
class IdeationSession:
    """Ideation session specification."""

    technique: IdeationTechnique
    duration_minutes: int
    participants: int
    materials_needed: tuple[str, ...]
    facilitation_steps: tuple[str, ...]


@dataclass(frozen=True)
class Idea:
    """Generated idea."""

    idea_id: str
    title: str
    description: str
    category: str
    feasibility_score: str
    impact_score: str
    novelty_score: str


@dataclass(frozen=True)
class EvaluationCriteria:
    """Idea evaluation criteria."""

    criterion_name: str
    weight: str
    scoring_guide: str


@dataclass(frozen=True)
class IdeationPlan:
    """Complete ideation plan."""

    problem_statement: str
    ideation_sessions: tuple[IdeationSession, ...]
    sample_ideas: tuple[Idea, ...]
    evaluation_criteria: tuple[EvaluationCriteria, ...]
    prioritization_framework: str
    action_plan: tuple[str, ...]


class IdeationFacilitator:
    """Ideation facilitation skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run ideation planning.

        Args:
            input_data: Dictionary with keys:
                - problem_statement: Problem or opportunity statement
                - participant_count: Optional participant count (default 8)

        Returns:
            Dictionary with ideation plan data.
        """
        problem = input_data.get("problem_statement", "")
        if not problem:
            return {"error": "No problem statement provided"}

        participant_count = int(input_data.get("participant_count", 8))

        sessions = self._design_sessions(participant_count)
        sample_ideas = self._generate_sample_ideas(problem)
        criteria = self._define_evaluation_criteria()
        framework = self._define_prioritization_framework()
        action_plan = self._create_action_plan()

        return IdeationPlan(
            problem_statement=problem,
            ideation_sessions=tuple(sessions),
            sample_ideas=tuple(sample_ideas),
            evaluation_criteria=tuple(criteria),
            prioritization_framework=framework,
            action_plan=tuple(action_plan),
        ).__dict__ | {
            "ideation_sessions": [s.__dict__ for s in sessions],
            "sample_ideas": [i.__dict__ for i in sample_ideas],
            "evaluation_criteria": [c.__dict__ for c in criteria],
        }

    @staticmethod
    def _design_sessions(participant_count: int) -> list[IdeationSession]:
        return [
            IdeationSession(
                technique=IdeationTechnique.BRAINSTORMING,
                duration_minutes=30,
                participants=participant_count,
                materials_needed=("Whiteboard", "Markers", "Post-it notes"),
                facilitation_steps=(
                    "1. Present problem statement (5 min)",
                    "2. Silent idea generation (10 min)",
                    "3. Round-robin sharing (10 min)",
                    "4. Group similar ideas (5 min)",
                ),
            ),
            IdeationSession(
                technique=IdeationTechnique.SCAMPER,
                duration_minutes=45,
                participants=participant_count,
                materials_needed=("SCAMPER worksheet", "Pens"),
                facilitation_steps=(
                    "1. Explain SCAMPER framework (5 min)",
                    "2. Substitute: What can be substituted? (5 min)",
                    "3. Combine: What can be combined? (5 min)",
                    "4. Adapt: What can be adapted? (5 min)",
                    "5. Modify: What can be modified? (5 min)",
                    "6. Put to other uses: Other uses? (5 min)",
                    "7. Eliminate: What can be removed? (5 min)",
                    "8. Reverse: What can be reversed? (5 min)",
                    "9. Consolidate ideas (5 min)",
                ),
            ),
            IdeationSession(
                technique=IdeationTechnique.SIX_THINKING_HATS,
                duration_minutes=60,
                participants=participant_count,
                materials_needed=("Colored hats or cards", "Flip chart"),
                facilitation_steps=(
                    "1. White Hat: Facts and information (10 min)",
                    "2. Red Hat: Emotions and feelings (10 min)",
                    "3. Black Hat: Risks and concerns (10 min)",
                    "4. Yellow Hat: Benefits and opportunities (10 min)",
                    "5. Green Hat: Creative ideas (10 min)",
                    "6. Blue Hat: Process and next steps (10 min)",
                ),
            ),
        ]

    @staticmethod
    def _generate_sample_ideas(problem: str) -> list[Idea]:
        return [
            Idea(
                idea_id="IDEA-001",
                title="Incremental Improvement",
                description="Optimize existing solution with minor enhancements",
                category="Incremental",
                feasibility_score="HIGH",
                impact_score="MEDIUM",
                novelty_score="LOW",
            ),
            Idea(
                idea_id="IDEA-002",
                title="Technology Integration",
                description="Integrate emerging technology (AI/ML) into solution",
                category="Innovation",
                feasibility_score="MEDIUM",
                impact_score="HIGH",
                novelty_score="HIGH",
            ),
            Idea(
                idea_id="IDEA-003",
                title="Process Redesign",
                description="Fundamentally redesign the process from scratch",
                category="Transformation",
                feasibility_score="LOW",
                impact_score="HIGH",
                novelty_score="MEDIUM",
            ),
        ]

    @staticmethod
    def _define_evaluation_criteria() -> list[EvaluationCriteria]:
        return [
            EvaluationCriteria(
                criterion_name="Feasibility",
                weight="30%",
                scoring_guide="1=Very difficult, 5=Very easy to implement",
            ),
            EvaluationCriteria(
                criterion_name="Impact",
                weight="40%",
                scoring_guide="1=Low impact, 5=Transformational impact",
            ),
            EvaluationCriteria(
                criterion_name="Novelty",
                weight="20%",
                scoring_guide="1=Incremental, 5=Breakthrough innovation",
            ),
            EvaluationCriteria(
                criterion_name="Alignment",
                weight="10%",
                scoring_guide="1=Poor fit, 5=Perfect strategic alignment",
            ),
        ]

    @staticmethod
    def _define_prioritization_framework() -> str:
        return (
            "Impact-Effort Matrix:\n"
            "- Quick Wins (High Impact, Low Effort): Prioritize first\n"
            "- Major Projects (High Impact, High Effort): Plan carefully\n"
            "- Fill-Ins (Low Impact, Low Effort): Do if time permits\n"
            "- Time Wasters (Low Impact, High Effort): Avoid\n\n"
            "Scoring: Weighted score = (Feasibility × 0.3) + (Impact × 0.4) + "
            "(Novelty × 0.2) + (Alignment × 0.1)"
        )

    @staticmethod
    def _create_action_plan() -> list[str]:
        return [
            "1. Conduct ideation sessions (Week 1)",
            "2. Consolidate and categorize ideas (Week 1)",
            "3. Evaluate ideas against criteria (Week 2)",
            "4. Prioritize using Impact-Effort matrix (Week 2)",
            "5. Develop detailed proposals for top 3 ideas (Week 3-4)",
            "6. Present to stakeholders for decision (Week 5)",
            "7. Create implementation roadmap for selected ideas (Week 6)",
        ]
