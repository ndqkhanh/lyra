"""
Hypothesis Generation Engine - Creative hypothesis generation with novelty assessment.
"""

import time
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

from ..types import (
    ComputeBudget,
    ReasoningConfig,
    ReasoningStep,
    ReasoningTrace,
    StepType,
)


@dataclass
class Hypothesis:
    """A generated hypothesis."""

    content: str
    novelty_score: float
    feasibility_score: float
    surprise_score: float
    overall_score: float
    reasoning: str


class HypothesisEngine:
    """
    Hypothesis generation engine with novelty and feasibility assessment.

    Features:
    - Creative hypothesis generation
    - Novelty assessment
    - Feasibility checking
    - Surprise maximization
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def reason(
        self,
        task: str,
        budget: ComputeBudget,
        config: ReasoningConfig,
        num_hypotheses: int = 5,
    ) -> ReasoningTrace:
        """
        Generate and evaluate hypotheses.

        Args:
            task: The task/question to generate hypotheses for
            budget: Compute budget
            config: Reasoning configuration
            num_hypotheses: Number of hypotheses to generate

        Returns:
            Reasoning trace with ranked hypotheses
        """
        start_time = time.time()

        # Generate diverse hypotheses
        hypotheses = []
        for i in range(num_hypotheses):
            if not budget.has_budget():
                break

            hypothesis = self._generate_hypothesis(task, i, config)

            if hypothesis:
                # Assess hypothesis
                assessed = self._assess_hypothesis(hypothesis, task, config)
                hypotheses.append(assessed)

                budget.use_tokens(len(hypothesis.split()) * 3)
                budget.use_step()

        # Sort by overall score
        hypotheses.sort(key=lambda h: h.overall_score, reverse=True)

        # Convert to reasoning trace
        trace = ReasoningTrace(
            task=task,
            strategy=config.strategy,
            steps=[],
        )

        # Add hypotheses as steps
        for i, hyp in enumerate(hypotheses, 1):
            trace.add_step(
                ReasoningStep(
                    content=f"Hypothesis {i}: {hyp.content}\n\nAssessment:\n{hyp.reasoning}",
                    step_type=StepType.HYPOTHESIS,
                    verification_score=hyp.overall_score,
                    metadata={
                        "novelty": hyp.novelty_score,
                        "feasibility": hyp.feasibility_score,
                        "surprise": hyp.surprise_score,
                    },
                )
            )

        # Add synthesis conclusion
        if hypotheses:
            best = hypotheses[0]
            conclusion = f"""Best Hypothesis: {best.content}

This hypothesis scores highest on:
- Novelty: {best.novelty_score:.2f}
- Feasibility: {best.feasibility_score:.2f}
- Surprise: {best.surprise_score:.2f}
- Overall: {best.overall_score:.2f}

Reasoning: {best.reasoning}"""

            trace.add_step(
                ReasoningStep(
                    content=conclusion,
                    step_type=StepType.CONCLUSION,
                    verification_score=best.overall_score,
                )
            )

        trace.duration = time.time() - start_time
        trace.token_count = budget.tokens_used
        trace.outcome = "success" if hypotheses else "incomplete"

        return trace

    def _generate_hypothesis(
        self,
        task: str,
        iteration: int,
        config: ReasoningConfig,
    ) -> Optional[str]:
        """Generate a creative hypothesis."""
        prompt = f"""Task: {task}

Generate a creative, non-obvious hypothesis or approach for this task.

Requirements:
- Be specific and concrete
- Avoid obvious or conventional approaches
- Think outside the box
- Make it testable/actionable

Iteration {iteration + 1} - Generate a DIFFERENT hypothesis from previous ones.

Hypothesis:"""

        try:
            response = self.client.messages.create(
                model=config.model,
                max_tokens=400,
                temperature=config.temperature + 0.3,  # Higher temp for creativity
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text
        except Exception:
            return None

    def _assess_hypothesis(
        self,
        hypothesis: str,
        task: str,
        config: ReasoningConfig,
    ) -> Hypothesis:
        """Assess hypothesis on multiple dimensions."""
        # Assess novelty
        novelty_score = self._assess_novelty(hypothesis)

        # Assess feasibility
        feasibility_score = self._assess_feasibility(hypothesis)

        # Assess surprise
        surprise_score = self._assess_surprise(hypothesis, task)

        # Calculate overall score
        overall_score = (
            novelty_score * 0.4 +
            feasibility_score * 0.3 +
            surprise_score * 0.3
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            hypothesis, novelty_score, feasibility_score, surprise_score
        )

        return Hypothesis(
            content=hypothesis,
            novelty_score=novelty_score,
            feasibility_score=feasibility_score,
            surprise_score=surprise_score,
            overall_score=overall_score,
            reasoning=reasoning,
        )

    def _assess_novelty(self, hypothesis: str) -> float:
        """Assess novelty of hypothesis."""
        score = 0.5  # Base score

        # Check for creative indicators
        creative_words = [
            "novel", "new", "innovative", "unique", "unconventional",
            "alternative", "different", "creative", "original"
        ]
        score += 0.05 * sum(1 for word in creative_words if word in hypothesis.lower())

        # Reward longer, more detailed hypotheses
        word_count = len(hypothesis.split())
        if word_count > 50:
            score += 0.2
        elif word_count > 30:
            score += 0.1

        # Penalize generic phrases
        generic_phrases = ["we could", "it might", "perhaps", "maybe"]
        score -= 0.05 * sum(1 for phrase in generic_phrases if phrase in hypothesis.lower())

        return min(1.0, max(0.0, score))

    def _assess_feasibility(self, hypothesis: str) -> float:
        """Assess feasibility of hypothesis."""
        score = 0.5  # Base score

        # Check for concrete details
        concrete_indicators = [
            "by", "using", "through", "via", "with", "implement",
            "measure", "test", "validate", "experiment"
        ]
        score += 0.05 * sum(1 for ind in concrete_indicators if ind in hypothesis.lower())

        # Check for actionable language
        action_words = ["can", "will", "would", "should", "could"]
        score += 0.03 * sum(1 for word in action_words if word in hypothesis.lower())

        # Penalize vague language
        vague_words = ["somehow", "something", "might", "possibly"]
        score -= 0.05 * sum(1 for word in vague_words if word in hypothesis.lower())

        return min(1.0, max(0.0, score))

    def _assess_surprise(self, hypothesis: str, task: str) -> float:
        """Assess how surprising the hypothesis is."""
        score = 0.5  # Base score

        # Check for unexpected connections
        connection_words = ["combine", "integrate", "merge", "link", "connect"]
        score += 0.1 * sum(1 for word in connection_words if word in hypothesis.lower())

        # Check for contrarian elements
        contrarian_words = ["contrary", "opposite", "inverse", "reverse", "against"]
        score += 0.1 * sum(1 for word in contrarian_words if word in hypothesis.lower())

        # Check for interdisciplinary elements
        interdisciplinary_words = [
            "biology", "physics", "psychology", "economics", "sociology",
            "mathematics", "computer science", "philosophy"
        ]
        score += 0.05 * sum(1 for word in interdisciplinary_words if word in hypothesis.lower())

        return min(1.0, max(0.0, score))

    def _generate_reasoning(
        self,
        hypothesis: str,
        novelty: float,
        feasibility: float,
        surprise: float,
    ) -> str:
        """Generate reasoning for hypothesis assessment."""
        reasoning = []

        # Novelty assessment
        if novelty > 0.7:
            reasoning.append(f"High novelty ({novelty:.2f}): This hypothesis presents a fresh perspective.")
        elif novelty < 0.4:
            reasoning.append(f"Low novelty ({novelty:.2f}): This hypothesis is relatively conventional.")
        else:
            reasoning.append(f"Moderate novelty ({novelty:.2f}): This hypothesis has some novel elements.")

        # Feasibility assessment
        if feasibility > 0.7:
            reasoning.append(f"High feasibility ({feasibility:.2f}): This hypothesis is actionable and testable.")
        elif feasibility < 0.4:
            reasoning.append(f"Low feasibility ({feasibility:.2f}): This hypothesis may be difficult to implement.")
        else:
            reasoning.append(f"Moderate feasibility ({feasibility:.2f}): This hypothesis is somewhat actionable.")

        # Surprise assessment
        if surprise > 0.7:
            reasoning.append(f"High surprise ({surprise:.2f}): This hypothesis is unexpected and creative.")
        elif surprise < 0.4:
            reasoning.append(f"Low surprise ({surprise:.2f}): This hypothesis is relatively predictable.")
        else:
            reasoning.append(f"Moderate surprise ({surprise:.2f}): This hypothesis has some surprising elements.")

        return " ".join(reasoning)
