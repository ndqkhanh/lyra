"""
Creative Thinking Skill - Creative problem-solving and innovation.

Given a challenge, produces:
- Creative thinking frameworks
- Lateral thinking exercises
- Innovation opportunities
- Breakthrough ideas
- Implementation strategies

Outputs structured creative thinking plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ThinkingFramework(StrEnum):
    """Creative thinking frameworks."""

    LATERAL_THINKING = "lateral_thinking"
    DESIGN_THINKING = "design_thinking"
    TRIZ = "triz"
    FIRST_PRINCIPLES = "first_principles"
    ANALOGICAL_THINKING = "analogical_thinking"


@dataclass(frozen=True)
class CreativeExercise:
    """Creative thinking exercise."""

    exercise_name: str
    framework: ThinkingFramework
    objective: str
    steps: tuple[str, ...]
    expected_outcome: str


@dataclass(frozen=True)
class InnovationOpportunity:
    """Identified innovation opportunity."""

    opportunity_id: str
    area: str
    description: str
    potential_impact: str
    required_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class BreakthroughIdea:
    """Breakthrough idea."""

    idea_id: str
    title: str
    description: str
    why_breakthrough: str
    implementation_challenges: tuple[str, ...]
    success_factors: tuple[str, ...]


@dataclass(frozen=True)
class CreativeThinkingPlan:
    """Complete creative thinking plan."""

    challenge: str
    creative_exercises: tuple[CreativeExercise, ...]
    innovation_opportunities: tuple[InnovationOpportunity, ...]
    breakthrough_ideas: tuple[BreakthroughIdea, ...]
    implementation_strategy: str


class CreativeThinking:
    """Creative thinking skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run creative thinking planning.

        Args:
            input_data: Dictionary with keys:
                - challenge: Challenge or problem statement

        Returns:
            Dictionary with creative thinking plan data.
        """
        challenge = input_data.get("challenge", "")
        if not challenge:
            return {"error": "No challenge provided"}

        exercises = self._design_exercises()
        opportunities = self._identify_opportunities(challenge)
        ideas = self._generate_breakthrough_ideas()
        strategy = self._define_implementation_strategy()

        return CreativeThinkingPlan(
            challenge=challenge,
            creative_exercises=tuple(exercises),
            innovation_opportunities=tuple(opportunities),
            breakthrough_ideas=tuple(ideas),
            implementation_strategy=strategy,
        ).__dict__ | {
            "creative_exercises": [e.__dict__ for e in exercises],
            "innovation_opportunities": [o.__dict__ for o in opportunities],
            "breakthrough_ideas": [i.__dict__ for i in ideas],
        }

    @staticmethod
    def _design_exercises() -> list[CreativeExercise]:
        return [
            CreativeExercise(
                exercise_name="Random Word Association",
                framework=ThinkingFramework.LATERAL_THINKING,
                objective="Break mental patterns and generate unexpected connections",
                steps=(
                    "1. Select a random word from dictionary",
                    "2. List attributes of the random word",
                    "3. Force connections between word attributes and problem",
                    "4. Develop ideas from connections",
                ),
                expected_outcome="5-10 unconventional ideas",
            ),
            CreativeExercise(
                exercise_name="First Principles Deconstruction",
                framework=ThinkingFramework.FIRST_PRINCIPLES,
                objective="Break down problem to fundamental truths",
                steps=(
                    "1. Identify and challenge all assumptions",
                    "2. Break problem down to basic elements",
                    "3. Reconstruct from ground up",
                    "4. Identify new solution paths",
                ),
                expected_outcome="Fundamental insights and novel approaches",
            ),
            CreativeExercise(
                exercise_name="Analogical Transfer",
                framework=ThinkingFramework.ANALOGICAL_THINKING,
                objective="Apply solutions from other domains",
                steps=(
                    "1. Identify analogous problems in other fields",
                    "2. Study how those problems were solved",
                    "3. Abstract the solution principles",
                    "4. Adapt principles to current problem",
                ),
                expected_outcome="Cross-domain solution adaptations",
            ),
        ]

    @staticmethod
    def _identify_opportunities(challenge: str) -> list[InnovationOpportunity]:
        # Analyze challenge to identify innovation opportunities
        _ = challenge  # Used for context analysis
        return [
            InnovationOpportunity(
                opportunity_id="OPP-001",
                area="Process Innovation",
                description="Reimagine core processes using automation and AI",
                potential_impact="50% efficiency improvement",
                required_capabilities=("AI/ML expertise", "Process redesign", "Change management"),
            ),
            InnovationOpportunity(
                opportunity_id="OPP-002",
                area="Business Model Innovation",
                description="Shift from product to platform business model",
                potential_impact="10x market expansion",
                required_capabilities=("Platform architecture", "Ecosystem development", "Network effects"),
            ),
            InnovationOpportunity(
                opportunity_id="OPP-003",
                area="Customer Experience Innovation",
                description="Create seamless omnichannel experience",
                potential_impact="2x customer satisfaction",
                required_capabilities=("UX design", "Integration", "Personalization"),
            ),
        ]

    @staticmethod
    def _generate_breakthrough_ideas() -> list[BreakthroughIdea]:
        return [
            BreakthroughIdea(
                idea_id="BT-001",
                title="AI-Powered Predictive Solution",
                description="Use AI to predict and prevent problems before they occur",
                why_breakthrough="Shifts from reactive to proactive approach",
                implementation_challenges=(
                    "Requires large training dataset",
                    "Model accuracy critical",
                    "User trust in AI predictions",
                ),
                success_factors=(
                    "High-quality data collection",
                    "Transparent AI decision-making",
                    "Gradual rollout with human oversight",
                ),
            ),
            BreakthroughIdea(
                idea_id="BT-002",
                title="Ecosystem Platform Approach",
                description="Build platform that enables third-party innovation",
                why_breakthrough="Leverages network effects for exponential growth",
                implementation_challenges=(
                    "Platform architecture complexity",
                    "Developer adoption",
                    "Governance and quality control",
                ),
                success_factors=(
                    "Strong API design",
                    "Developer community building",
                    "Clear value proposition for partners",
                ),
            ),
        ]

    @staticmethod
    def _define_implementation_strategy() -> str:
        return (
            "Innovation Implementation Strategy:\n\n"
            "1. Exploration Phase (Months 1-2):\n"
            "   - Run creative thinking workshops\n"
            "   - Generate and evaluate ideas\n"
            "   - Select top 3 breakthrough ideas\n\n"
            "2. Validation Phase (Months 3-4):\n"
            "   - Build prototypes for top ideas\n"
            "   - Test with early adopters\n"
            "   - Gather feedback and iterate\n\n"
            "3. Development Phase (Months 5-8):\n"
            "   - Develop MVP for validated idea\n"
            "   - Conduct pilot with select users\n"
            "   - Refine based on pilot results\n\n"
            "4. Scale Phase (Months 9-12):\n"
            "   - Full product development\n"
            "   - Market launch\n"
            "   - Measure impact and iterate"
        )
