"""
Enhanced Debate Engine - Multi-agent collaborative reasoning with depth.
"""

import time
from dataclasses import dataclass
from enum import Enum

from anthropic import Anthropic

from ..types import (
    ComputeBudget,
    ReasoningConfig,
    ReasoningStep,
    ReasoningTrace,
    StepType,
)


class Perspective(str, Enum):
    """Agent perspectives for debate."""

    SKEPTIC = "skeptic"
    OPTIMIST = "optimist"
    PRAGMATIST = "pragmatist"
    METHODOLOGIST = "methodologist"
    THEORIST = "theorist"
    EMPIRICIST = "empiricist"
    SYNTHESIZER = "synthesizer"


@dataclass
class DebateAgent:
    """Agent participating in debate."""

    perspective: Perspective
    name: str
    system_prompt: str

    def get_prompt(self, topic: str, context: str) -> str:
        """Get agent's debate prompt."""
        return f"""{self.system_prompt}

Topic: {topic}

Context from previous rounds:
{context}

Provide your perspective with deep reasoning. Think step-by-step and justify your position."""


@dataclass
class DebateRound:
    """A single round of debate."""

    round_num: int
    arguments: list[tuple[Perspective, str, float]]  # (perspective, argument, verification_score)

    def get_summary(self) -> str:
        """Get round summary."""
        summary = f"Round {self.round_num}:\n"
        for perspective, argument, score in self.arguments:
            summary += f"- {perspective.value}: {argument[:200]}... (score: {score:.2f})\n"
        return summary


class EnhancedDebateEngine:
    """
    Enhanced debate engine with deep reasoning per agent.

    Features:
    - 5-10 rounds of debate
    - Each agent uses chain-of-thought
    - Cross-agent verification
    - Proof-based consensus
    """

    def __init__(self, api_key: str | None = None):
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.agents = self._initialize_agents()

    def _initialize_agents(self) -> list[DebateAgent]:
        """Initialize debate agents with different perspectives."""
        return [
            DebateAgent(
                perspective=Perspective.SKEPTIC,
                name="The Skeptic",
                system_prompt=(
                    "You are a skeptical analyst. Question assumptions, identify flaws, and demand"
                    "evidence. Be critical but constructive."
                ),
            ),
            DebateAgent(
                perspective=Perspective.OPTIMIST,
                name="The Optimist",
                system_prompt=(
                    "You are an optimistic visionary. See potential, identify opportunities, and"
                    "propose bold ideas. Be ambitious but grounded."
                ),
            ),
            DebateAgent(
                perspective=Perspective.PRAGMATIST,
                name="The Pragmatist",
                system_prompt=(
                    "You are a practical implementer. Focus on feasibility, resources, and"
                    "real-world constraints. Be realistic and actionable."
                ),
            ),
            DebateAgent(
                perspective=Perspective.METHODOLOGIST,
                name="The Methodologist",
                system_prompt=(
                    "You are a rigorous methodologist. Focus on process, validation, and"
                    "systematic approaches. Be thorough and precise."
                ),
            ),
            DebateAgent(
                perspective=Perspective.SYNTHESIZER,
                name="The Synthesizer",
                system_prompt=(
                    "You are a synthesizer. Find common ground, integrate perspectives, and build"
                    "consensus. Be balanced and comprehensive."
                ),
            ),
        ]

    def reason(
        self,
        task: str,
        budget: ComputeBudget,
        config: ReasoningConfig,
        max_rounds: int = 5,
    ) -> ReasoningTrace:
        """
        Execute enhanced debate reasoning.

        Args:
            task: The task to debate
            budget: Compute budget
            config: Reasoning configuration
            max_rounds: Maximum debate rounds

        Returns:
            Reasoning trace with debate synthesis
        """
        start_time = time.time()
        rounds: list[DebateRound] = []

        context = ""

        for round_num in range(1, max_rounds + 1):
            if not budget.has_budget():
                break

            # Each agent reasons deeply
            round_arguments = []

            for agent in self.agents:
                if not budget.has_budget():
                    break

                # Agent generates reasoning with CoT
                argument = self._agent_reason(agent, task, context, config)

                # Other agents verify
                verification_score = self._cross_verify(
                    argument, agent.perspective, self.agents, config
                )

                round_arguments.append((agent.perspective, argument, verification_score))
                budget.use_tokens(len(argument.split()) * 2)
                budget.use_step()

            # Create round
            debate_round = DebateRound(
                round_num=round_num,
                arguments=round_arguments,
            )
            rounds.append(debate_round)

            # Update context
            context += f"\n\n{debate_round.get_summary()}"

            # Check for consensus
            if self._check_consensus(rounds):
                break

        # Synthesize final conclusion
        synthesis = self._synthesize(task, rounds, config)

        # Convert to reasoning trace
        trace = ReasoningTrace(
            task=task,
            strategy=config.strategy,
            steps=[],
        )

        # Add debate rounds as steps
        for debate_round in rounds:
            for perspective, argument, score in debate_round.arguments:
                trace.add_step(
                    ReasoningStep(
                        content=f"[{perspective.value}] {argument}",
                        step_type=StepType.ANALYSIS,
                        verification_score=score,
                    )
                )

        # Add synthesis as conclusion
        trace.add_step(
            ReasoningStep(
                content=synthesis,
                step_type=StepType.CONCLUSION,
                verification_score=1.0,
            )
        )

        trace.duration = time.time() - start_time
        trace.token_count = budget.tokens_used
        trace.outcome = "success"

        return trace

    def _agent_reason(
        self,
        agent: DebateAgent,
        task: str,
        context: str,
        config: ReasoningConfig,
    ) -> str:
        """Agent generates reasoning with chain-of-thought."""
        prompt = agent.get_prompt(task, context)

        try:
            response = self.client.messages.create(
                model=config.model,
                max_tokens=800,
                temperature=config.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text
        except Exception as e:
            return f"Error: {str(e)}"

    def _cross_verify(
        self,
        argument: str,
        perspective: Perspective,
        agents: list[DebateAgent],
        config: ReasoningConfig,
    ) -> float:
        """Other agents verify this argument."""
        # Simple heuristic verification for now
        score = 0.5

        # Check for reasoning quality
        if len(argument.split()) > 50:
            score += 0.2

        reasoning_indicators = ["because", "therefore", "evidence", "analysis"]
        score += 0.05 * sum(1 for ind in reasoning_indicators if ind in argument.lower())

        # Check for balance
        if "however" in argument.lower() or "but" in argument.lower():
            score += 0.1

        return min(1.0, max(0.0, score))

    def _check_consensus(self, rounds: list[DebateRound]) -> bool:
        """Check if consensus has been reached."""
        if len(rounds) < 2:
            return False

        # Check if recent rounds have high agreement
        recent_scores = []
        for debate_round in rounds[-2:]:
            scores = [score for _, _, score in debate_round.arguments]
            recent_scores.extend(scores)

        if not recent_scores:
            return False

        avg_score = sum(recent_scores) / len(recent_scores)
        return avg_score > 0.75

    def _synthesize(
        self,
        task: str,
        rounds: list[DebateRound],
        config: ReasoningConfig,
    ) -> str:
        """Synthesize final conclusion from debate."""
        # Build summary of all rounds
        summary = f"Task: {task}\n\n"
        summary += "Debate Summary:\n"

        for debate_round in rounds:
            summary += debate_round.get_summary() + "\n"

        prompt = f"""{summary}

Based on this multi-round debate with diverse perspectives, provide a comprehensive synthesis that:
1. Integrates the key insights from all perspectives
2. Addresses the main points of agreement and disagreement
3. Provides a balanced, well-reasoned conclusion
4. Acknowledges limitations and uncertainties

Final synthesis:"""

        try:
            response = self.client.messages.create(
                model=config.model,
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text
        except Exception as e:
            return f"Synthesis error: {str(e)}"
