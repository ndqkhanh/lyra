"""
Reasoning Strategies for the Lyra Cognitive Architecture.

Implements multiple reasoning strategies that can be selected based on
task complexity and type. Each strategy follows a consistent interface:
accept a problem description and return structured reasoning output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from lyra_cognitive.models import ConfidenceLevel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReasoningTrace:
    """A single step in a reasoning chain."""

    step: int
    content: str
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReasoningResult:
    """The result of a reasoning strategy execution."""

    strategy: str
    conclusion: str
    trace: tuple[ReasoningTrace, ...]
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    alternatives: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def steps(self) -> int:
        """Number of reasoning steps taken."""
        return len(self.trace)


class ReasoningEngine:
    """
    Multi-strategy reasoning engine with selectable approaches.

    Supports:
    - Chain-of-Thought: sequential step-by-step reasoning.
    - Tree-of-Thoughts: branching exploration of multiple paths.
    - Reflexion: self-critique and iterative improvement.
    - Debate: multi-perspective analysis.
    """

    def __init__(self, max_depth: int = 10, branching_factor: int = 3):
        """
        Args:
            max_depth: Maximum reasoning depth for tree/chain strategies.
            branching_factor: Number of branches in tree-of-thoughts.
        """
        self._max_depth = max_depth
        self._branching_factor = branching_factor

    def chain_of_thought(
        self,
        problem: str,
        context: dict[str, Any] | None = None,
    ) -> ReasoningResult:
        """
        Sequential step-by-step reasoning through a problem.

        Decomposes the problem, reasons through each step, and synthesizes
        a conclusion.

        Args:
            problem: The problem to reason about.
            context: Optional context dict.

        Returns:
            ReasoningResult with the chain of reasoning.
        """
        logger.info("Reasoning: chain-of-thought for problem: %s", problem[:60])
        ctx = context or {}

        trace: list[ReasoningTrace] = []
        steps = self._decompose_problem(problem)

        for i, step_description in enumerate(steps):
            reasoning = self._reason_step(step_description, ctx, trace)
            trace.append(ReasoningTrace(
                step=i + 1,
                content=reasoning,
                confidence=ConfidenceLevel.MEDIUM,
            ))

        conclusion = self._synthesize_conclusion(problem, trace)
        overall_confidence = self._estimate_confidence(trace)

        return ReasoningResult(
            strategy="chain_of_thought",
            conclusion=conclusion,
            trace=tuple(trace),
            confidence=overall_confidence,
        )

    def tree_of_thoughts(
        self,
        problem: str,
        branching: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> ReasoningResult:
        """
        Explore multiple reasoning paths in parallel, then select the best.

        Args:
            problem: The problem to reason about.
            branching: Number of branches to explore (default: self._branching_factor).
            context: Optional context dict.

        Returns:
            ReasoningResult with the best path and alternatives.
        """
        bf = branching or self._branching_factor
        logger.info(
            "Reasoning: tree-of-thoughts (branching=%d) for: %s",
            bf,
            problem[:60],
        )

        # Generate multiple initial approaches
        approaches = self._generate_approaches(problem, bf)

        # Evaluate each approach
        best_score = -1.0
        best_trace: list[ReasoningTrace] = []
        best_conclusion = ""
        alternatives: list[str] = []

        for approach in approaches:
            trace: list[ReasoningTrace] = []
            steps = self._decompose_problem(approach)
            for i, step_description in enumerate(steps):
                reasoning = self._reason_step(step_description, {}, trace)
                trace.append(ReasoningTrace(
                    step=i + 1,
                    content=reasoning,
                    confidence=ConfidenceLevel.MEDIUM,
                ))

            conclusion = self._synthesize_conclusion(approach, trace)
            score = self._score_reasoning_path(trace, conclusion)

            if score > best_score:
                if best_conclusion:
                    alternatives.append(best_conclusion)
                best_score = score
                best_trace = trace
                best_conclusion = conclusion
            else:
                alternatives.append(conclusion)

        return ReasoningResult(
            strategy="tree_of_thoughts",
            conclusion=best_conclusion,
            trace=tuple(best_trace),
            confidence=ConfidenceLevel.from_score(best_score),
            alternatives=tuple(alternatives[:5]),
        )

    def reflexion(
        self,
        reasoning: str,
        iterations: int = 3,
        context: dict[str, Any] | None = None,
    ) -> ReasoningResult:
        """
        Self-critique and iteratively improve reasoning.

        Each iteration critiques the previous output and produces
        an improved version.

        Args:
            reasoning: The initial reasoning to refine.
            iterations: Number of critique-improve cycles.
            context: Optional context dict.

        Returns:
            ReasoningResult with the improved reasoning.
        """
        logger.info(
            "Reasoning: reflexion (%d iterations) for reasoning of length %d",
            iterations,
            len(reasoning),
        )

        current = reasoning
        trace: list[ReasoningTrace] = []

        for i in range(iterations):
            critique = self._critique_reasoning(current)
            trace.append(ReasoningTrace(
                step=i + 1,
                content=critique,
                confidence=ConfidenceLevel.MEDIUM,
            ))
            current = self._improve_reasoning(current, critique)

        confidence = ConfidenceLevel.HIGH if iterations >= 3 else ConfidenceLevel.MEDIUM

        return ReasoningResult(
            strategy="reflexion",
            conclusion=current,
            trace=tuple(trace),
            confidence=confidence,
        )

    def debate(
        self,
        proposition: str,
        perspectives: int = 3,
        context: dict[str, Any] | None = None,
    ) -> ReasoningResult:
        """
        Multi-perspective analysis through simulated debate.

        Generates pro, con, and neutral perspectives, then synthesizes.

        Args:
            proposition: The proposition to debate.
            perspectives: Number of perspectives (default 3: pro, con, neutral).
            context: Optional context dict.

        Returns:
            ReasoningResult with synthesized conclusion.
        """
        logger.info(
            "Reasoning: debate (%d perspectives) on: %s",
            perspectives,
            proposition[:60],
        )

        perspective_labels = self._get_perspective_labels(perspectives)
        arguments: list[str] = []
        trace: list[ReasoningTrace] = []

        for i, label in enumerate(perspective_labels):
            arg = self._argue_perspective(proposition, label)
            trace.append(ReasoningTrace(
                step=i + 1,
                content=f"[{label}] {arg}",
                confidence=ConfidenceLevel.MEDIUM,
                metadata={"perspective": label},
            ))
            arguments.append(arg)

        conclusion = self._synthesize_debate(proposition, arguments, perspective_labels)

        return ReasoningResult(
            strategy="debate",
            conclusion=conclusion,
            trace=tuple(trace),
            confidence=ConfidenceLevel.MEDIUM,
            alternatives=tuple(arguments),
        )

    # ── Private helpers ───────────────────────────────────────────────────

    def _decompose_problem(self, problem: str) -> list[str]:
        """Decompose a problem into sequential reasoning steps."""
        words = problem.split()
        wc = len(words)

        if wc <= 5:
            return [
                "Identify the core question",
                "Gather relevant facts",
                "Apply logical analysis",
                "Draw conclusion",
            ]
        elif "compare" in problem.lower() or "difference" in problem.lower():
            return [
                "Define each item being compared",
                "List key properties of each item",
                "Compare properties point-by-point",
                "Identify similarities and differences",
                "Draw comparative conclusion",
            ]
        else:
            return [
                "Parse and clarify the problem statement",
                "Identify assumptions and constraints",
                "Explore possible approaches",
                "Evaluate each approach against criteria",
                "Select best approach with justification",
                "Synthesize final answer",
            ]

    def _reason_step(
        self,
        step: str,
        context: dict[str, Any],
        previous: list[ReasoningTrace],
    ) -> str:
        """Reason through a single step (template-based for determinism)."""
        prev_summary = ""
        if previous:
            prev_content = previous[-1].content[:100]
            prev_summary = f"Given the previous finding: {prev_content}"

        return (
            f"Step analysis: {step}. "
            f"{prev_summary} "
            f"Evaluation: the most reasonable approach for '{step}' "
            f"is to proceed systematically with clear success criteria."
        )

    def _synthesize_conclusion(
        self,
        problem: str,
        trace: list[ReasoningTrace],
    ) -> str:
        """Synthesize a conclusion from the reasoning trace."""
        if not trace:
            return f"Unable to reach a conclusion for: {problem}"

        insights = [t.content[:80] for t in trace]
        combined = "; ".join(insights[:5])
        return (
            f"Conclusion for '{problem[:100]}': "
            f"After {len(trace)} reasoning steps ({combined}), "
            f"the recommended approach is to proceed with the highest-confidence "
            f"path identified during analysis."
        )

    def _estimate_confidence(self, trace: list[ReasoningTrace]) -> ConfidenceLevel:
        """Estimate overall confidence from trace."""
        if not trace:
            return ConfidenceLevel.UNKNOWN
        scores = {
            ConfidenceLevel.HIGH: 1.0,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.LOW: 0.3,
            ConfidenceLevel.UNKNOWN: 0.1,
        }
        avg = sum(scores[t.confidence] for t in trace) / len(trace)
        return ConfidenceLevel.from_score(avg)

    def _generate_approaches(self, problem: str, count: int) -> list[str]:
        """Generate multiple approaches to a problem."""
        templates = [
            f"Analyze {problem} through systematic decomposition",
            f"Solve {problem} using first-principles reasoning",
            f"Address {problem} via iterative refinement",
            f"Tackle {problem} with constraint-based optimization",
            f"Approach {problem} by analogical reasoning",
        ]
        return templates[:count]

    def _score_reasoning_path(
        self,
        trace: list[ReasoningTrace],
        conclusion: str,
    ) -> float:
        """Score a reasoning path for tree-of-thoughts selection."""
        score = 0.5
        # Prefer more steps (thoroughness)
        if len(trace) >= 3:
            score += 0.15
        # Prefer longer conclusions (detail)
        if len(conclusion) > 100:
            score += 0.15
        # Prefer structured conclusions
        if any(w in conclusion.lower() for w in ("therefore", "recommended", "because")):
            score += 0.1
        return min(1.0, score)

    def _critique_reasoning(self, reasoning: str) -> str:
        """Generate a self-critique of the reasoning."""
        issues: list[str] = []

        if len(reasoning) < 50:
            issues.append("Reasoning is too brief; lacks depth")
        if "assume" in reasoning.lower():
            issues.append("Relies on assumptions that should be verified")
        if reasoning.count(".") < 3:
            issues.append("Could benefit from more structured arguments")

        if not issues:
            issues.append("Reasoning appears sound; minor improvements possible")

        return "Critique: " + " | ".join(issues)

    def _improve_reasoning(self, original: str, critique: str) -> str:
        """Improve reasoning based on critique."""
        improved = original
        if "too brief" in critique:
            improved += (
                " Additionally, a more thorough analysis reveals that each step "
                "should be validated against known constraints and edge cases."
            )
        if "assumptions" in critique:
            improved += (
                " Note: assumptions identified in critique should be explicitly "
                "verified before proceeding."
            )
        return improved

    @staticmethod
    def _get_perspective_labels(count: int) -> list[str]:
        """Get perspective labels for debate."""
        defaults = ["Advocate (Pro)", "Critic (Con)", "Analyst (Neutral)", "Skeptic", "Optimist"]
        return defaults[:count]

    def _argue_perspective(self, proposition: str, perspective: str) -> str:
        """Generate an argument from a specific perspective."""
        if "pro" in perspective.lower() or "advocate" in perspective.lower():
            return (
                f"Supporting '{proposition[:60]}': this approach has clear benefits "
                f"including efficiency, clarity, and alignment with best practices."
            )
        elif "con" in perspective.lower() or "critic" in perspective.lower():
            return (
                f"Challenging '{proposition[:60]}': potential risks include "
                f"unexpected edge cases, scalability concerns, and maintenance overhead."
            )
        else:
            return (
                f"Analyzing '{proposition[:60]}': the proposition has both merits "
                f"and drawbacks. Trade-offs must be evaluated against specific context."
            )

    def _synthesize_debate(
        self,
        proposition: str,
        arguments: list[str],
        labels: list[str],
    ) -> str:
        """Synthesize debate arguments into a conclusion."""
        if not arguments:
            return f"No arguments available for: {proposition}"

        parts = [f"{label}: {arg[:60]}..." for label, arg in zip(labels, arguments)]
        return (
            f"Debate synthesis for '{proposition[:80]}': "
            f"Considering {len(arguments)} perspectives ({'; '.join(parts)}), "
            f"the balanced conclusion is to proceed with caution, incorporating "
            f"critical feedback while leveraging identified strengths."
        )
