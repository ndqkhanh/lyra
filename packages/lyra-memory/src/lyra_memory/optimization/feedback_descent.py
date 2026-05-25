"""
Feedback Descent — open-ended text optimization via pairwise comparison
with textual rationales and dimension-free convergence guarantees.

Source: Feedback Descent (Uw5G3H26ps), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4


class LLMClient(Protocol):
    """Protocol for LLM interaction."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class FeedbackPair:
    """Result of comparing two text variants."""

    candidate_a: str
    candidate_b: str
    winner: str  # "a" | "b" | "tie"
    rationale: str = ""
    reset: bool = False
    id: str = field(default_factory=lambda: uuid4().hex)

    @property
    def is_decisive(self) -> bool:
        return self.winner != "tie"


@dataclass
class FeedbackDescentOptimizer:
    """Open-ended text optimization via pairwise comparison.

    Iteratively improves text (prompts, plans, strategies) through
    LLM-driven proposal generation and pairwise comparison with feedback
    history as context. Uses reset-on-success heuristic to clear stale
    feedback and dimension-free convergence guarantees.
    """

    llm: LLMClient
    max_iterations: int = 10

    async def optimize(
        self,
        candidate: str,
        feedback_history: list[FeedbackPair] | None = None,
        iterations: int | None = None,
    ) -> str:
        """Iteratively improve text via pairwise comparisons.

        Args:
            candidate: The initial text to optimize
            feedback_history: Prior comparison results for context
            iterations: Number of optimization rounds (defaults to max_iterations)

        Returns:
            Best version of the text found
        """
        history = list(feedback_history or [])
        best = candidate
        n_iter = iterations if iterations is not None else self.max_iterations

        for _ in range(n_iter):
            proposal = await self._propose_variant(best, history)
            comparison = await self._compare(best, proposal, history)

            if comparison.winner == "b":
                best = proposal
                if comparison.reset:
                    history = []

            history.append(comparison)

        return best

    async def _propose_variant(
        self, current: str, history: list[FeedbackPair],
    ) -> str:
        """Generate an improved variant based on feedback history."""
        history_text = self._format_history(history) if history else "No prior feedback."

        prompt = f"""You are improving text through iterative refinement.

CURRENT TEXT:
{current[:3000]}

FEEDBACK HISTORY:
{history_text[:2000]}

Propose an improved variant. Consider the feedback patterns and suggest
a version that addresses past shortcomings while preserving strengths.
Output the variant text only."""

        return await self.llm.complete(prompt)

    async def _compare(
        self, current: str, proposal: str, history: list[FeedbackPair],
    ) -> FeedbackPair:
        """Compare two variants and determine the winner."""
        history_text = self._format_history(history) if history else "No prior feedback."

        prompt = f"""Compare these two text variants and determine which is better.

VARIANT A (current):
{current[:2000]}

VARIANT B (proposal):
{proposal[:2000]}

FEEDBACK HISTORY:
{history_text[:1500]}

Output JSON only:
{{
    "winner": "a" or "b" or "tie",
    "rationale": "Brief explanation of why the winner is better",
    "reset": true/false (true if the proposal represents a breakthrough that invalidates prior feedback)
}}"""

        response = await self.llm.complete(prompt)
        return self._parse_comparison(response, current, proposal)

    @staticmethod
    def _format_history(history: list[FeedbackPair]) -> str:
        lines = []
        for i, pair in enumerate(history):
            lines.append(f"Round {i+1}: Winner={pair.winner}, Rationale={pair.rationale[:200]}")
        return "\n".join(lines)

    @staticmethod
    def _parse_comparison(
        response: str, candidate_a: str, candidate_b: str,
    ) -> FeedbackPair:
        import json

        try:
            data = json.loads(_extract_json(response))
            return FeedbackPair(
                candidate_a=candidate_a,
                candidate_b=candidate_b,
                winner=str(data.get("winner", "tie")),
                rationale=str(data.get("rationale", "")),
                reset=bool(data.get("reset", False)),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return FeedbackPair(
                candidate_a=candidate_a,
                candidate_b=candidate_b,
                winner="a",
                rationale="parse error, defaulting to current",
            )


def _extract_json(text: str) -> str:
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text.strip()
