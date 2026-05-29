"""
Multi-Perspective Synthesis.

Inspired by Co-STORM multi-agent discourse: five perspective agents debate
research findings to produce balanced, bias-mitigated synthesis.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PerspectiveType
# ---------------------------------------------------------------------------


class PerspectiveType(Enum):
    """The five canonical analysis perspectives."""

    OPTIMIST = "optimist"        # Focuses on potential, positives, opportunities
    SKEPTIC = "skeptic"          # Challenges assumptions, flags risks, demands evidence
    PRAGMATIST = "pragmatist"    # Grounds in practical constraints, feasibility
    INNOVATOR = "innovator"      # Explores novel combinations and future directions
    HISTORIAN = "historian"      # Contextualizes with prior work and historical patterns


PERSPECTIVE_DESCRIPTIONS: dict[PerspectiveType, str] = {
    PerspectiveType.OPTIMIST: (
        "Sees potential breakthroughs, positive applications, and best-case "
        "outcomes. Highlights what could go right and why this matters."
    ),
    PerspectiveType.SKEPTIC: (
        "Challenges claims, demands rigorous evidence, identifies weaknesses, "
        "and exposes over-statements. Asks 'what could go wrong?'"
    ),
    PerspectiveType.PRAGMATIST: (
        "Grounds discussion in real-world constraints — cost, scalability, "
        "data availability, and engineering feasibility."
    ),
    PerspectiveType.INNOVATOR: (
        "Explores novel combinations, cross-domain analogies, and speculative "
        "future directions that others may overlook."
    ),
    PerspectiveType.HISTORIAN: (
        "Places findings in historical context. Identifies recurring patterns, "
        "past attempts, and lessons from prior work."
    ),
}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerspectiveAnalysis:
    """Analysis produced by a single perspective agent.

    Attributes:
        perspective: The viewpoint.
        key_insights: Main observations from this perspective.
        strengths: What the research gets right.
        weaknesses: Limitations, risks, or gaps.
        score: Quality score (0.0-1.0) assigned by this perspective.
        novel_ideas: New directions proposed.
    """

    perspective: PerspectiveType
    key_insights: tuple[str, ...] = ()
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    score: float = 0.5
    novel_ideas: tuple[str, ...] = ()


@dataclass(frozen=True)
class DebateRound:
    """One round of multi-perspective debate.

    Attributes:
        round_number: Zero-based round index.
        analyses: Per-perspective analyses.
        critiques: Cross-perspective critiques as (from, to, text).
    """

    round_number: int
    analyses: tuple[PerspectiveAnalysis, ...] = ()
    critiques: tuple[tuple[str, str, str], ...] = ()  # (from_p, to_p, text)


@dataclass(frozen=True)
class SynthesisResult:
    """Final output of multi-perspective synthesis.

    Attributes:
        topic: The research topic.
        consensus_points: Areas where all perspectives agree.
        dissent_points: Areas of productive disagreement.
        balanced_report: The synthesized multi-perspective report.
        confidence: Overall synthesis confidence (0.0-1.0).
    """

    topic: str
    consensus_points: tuple[str, ...] = ()
    dissent_points: tuple[str, ...] = ()
    balanced_report: str = ""
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# PerspectiveAgent
# ---------------------------------------------------------------------------


class PerspectiveAgent:
    """Represents a single analytical viewpoint for multi-perspective debate.

    Each agent analyses findings through its lens, critiques other perspectives,
    and synthesises others' views into its own understanding.
    """

    def __init__(self, perspective: PerspectiveType) -> None:
        """Create an agent representing the given perspective.

        Args:
            perspective: The analytical lens this agent embodies.
        """
        self.perspective = perspective
        self._criteria = _build_criteria(perspective)

    # -- analysis ------------------------------------------------------------

    def analyze(self, findings: str) -> PerspectiveAnalysis:
        """Analyze research findings from this perspective.

        Uses heuristic keyword analysis to identify what this perspective
        considers important.  In production, this would integrate with an
        LLM for deeper semantic analysis.

        Args:
            findings: Research findings text.

        Returns:
            ``PerspectiveAnalysis`` from this viewpoint.
        """
        lowered = findings.lower()

        insights: list[str] = []
        strengths: list[str] = []
        weaknesses: list[str] = []
        novel: list[str] = []

        # Score: how well findings align with this perspective's criteria
        matches = 0
        for keyword in self._criteria["positive"]:
            if keyword.lower() in lowered:
                strengths.append(f"Addresses '{keyword}' (aligned with {self.perspective.value})")
                matches += 1
        for keyword in self._criteria["concern"]:
            if keyword.lower() not in lowered:
                weaknesses.append(f"Missing discussion of '{keyword}'")
            else:
                matches += 0.5

        # Generate perspective-specific insights
        for trigger, insight in self._criteria["triggers"].items():
            if trigger.lower() in lowered:
                insights.append(insight)

        if not insights:
            insights.append(
                f"[{self.perspective.value}] Findings reviewed; "
                f"no strong signals detected for this perspective."
            )

        score = min(matches / max(len(self._criteria["positive"]), 1) * 0.5 + 0.3, 1.0)

        # Novel ideas from this perspective
        novel = self._generate_novel_ideas(findings)

        logger.debug(
            "Agent[%s] analyzed findings: score=%.2f, %d insights",
            self.perspective.value,
            score,
            len(insights),
        )
        return PerspectiveAnalysis(
            perspective=self.perspective,
            key_insights=tuple(insights),
            strengths=tuple(strengths) if strengths else ("No strong signal alignment detected.",),
            weaknesses=tuple(weaknesses) if weaknesses else ("Insufficient coverage for this perspective.",),
            score=round(score, 4),
            novel_ideas=tuple(novel),
        )

    # -- critique ------------------------------------------------------------

    def critique(self, other_analysis: PerspectiveAnalysis) -> list[str]:
        """Challenge another perspective's analysis.

        Args:
            other_analysis: The analysis to critique.

        Returns:
            List of critique points.
        """
        critiques: list[str] = []

        # Each perspective has natural criticisms of others
        blindspots = _blindspots(self.perspective, other_analysis.perspective)
        for blindspot in blindspots:
            critiques.append(
                f"[{self.perspective.value} → {other_analysis.perspective.value}]: {blindspot}"
            )

        # Challenge numeric scores when they differ significantly
        if abs(self.perspective.value != other_analysis.perspective.value):
            critiques.append(
                f"[{self.perspective.value}]: Score {other_analysis.score} seems "
                f"{'high' if other_analysis.score > 0.7 else 'low'} — consider "
                f"broader evidence."
            )

        logger.debug(
            "Agent[%s] critiqued %s: %d points",
            self.perspective.value,
            other_analysis.perspective.value,
            len(critiques),
        )
        return critiques

    # -- synthesis -----------------------------------------------------------

    def synthesize(self, all_analyses: list[PerspectiveAnalysis]) -> PerspectiveAnalysis:
        """Incorporate other perspectives' views into this agent's synthesis.

        Args:
            all_analyses: All analyses from the current debate round.

        Returns:
            Updated analysis incorporating cross-perspective insights.
        """
        other_insights: list[str] = []
        for analysis in all_analyses:
            if analysis.perspective != self.perspective:
                for insight in analysis.key_insights[:2]:
                    other_insights.append(
                        f"[from {analysis.perspective.value}] {insight}"
                    )

        combined = list(self._criteria.get("synthesis_base", []))
        combined.extend(other_insights)

        avg_score = sum(a.score for a in all_analyses) / max(len(all_analyses), 1)

        return PerspectiveAnalysis(
            perspective=self.perspective,
            key_insights=tuple(combined),
            strengths=(f"Synthesized from {len(all_analyses)} perspectives.",),
            weaknesses=(),
            score=round(avg_score, 4),
        )

    # -- helpers -------------------------------------------------------------

    def _generate_novel_ideas(self, _findings: str) -> list[str]:
        """Propose novel research directions from this perspective."""
        prompts = {
            PerspectiveType.OPTIMIST: "Explore scaling to larger datasets and broader domains.",
            PerspectiveType.SKEPTIC: "Design rigorous ablation studies to isolate causal factors.",
            PerspectiveType.PRAGMATIST: "Evaluate cost-efficiency and real-world deployment paths.",
            PerspectiveType.INNOVATOR: "Combine with orthogonal techniques for novel architectures.",
            PerspectiveType.HISTORIAN: "Map findings to historical research trajectories and trends.",
        }
        return [prompts.get(self.perspective, "Consider cross-disciplinary connections.")]


# ---------------------------------------------------------------------------
# MultiPerspectiveSynthesizer
# ---------------------------------------------------------------------------


class MultiPerspectiveSynthesizer:
    """Orchestrates multi-perspective debate and synthesizes balanced reports."""

    def __init__(self) -> None:
        """Create synthesizer with all five perspective agents."""
        self._agents: dict[PerspectiveType, PerspectiveAgent] = {
            pt: PerspectiveAgent(pt) for pt in PerspectiveType
        }

    # -- debate --------------------------------------------------------------

    def debate(
        self,
        topic: str,
        findings: str,
        rounds: int = 2,
    ) -> list[DebateRound]:
        """Run a structured multi-perspective debate on *topic*.

        Args:
            topic: The research topic.
            findings: Research findings text to debate.
            rounds: Number of debate rounds.

        Returns:
            List of ``DebateRound`` results.
        """
        debate_rounds: list[DebateRound] = []

        for r in range(rounds):
            # Each agent analyses independently
            analyses = tuple(
                agent.analyze(findings)
                for agent in self._agents.values()
            )

            # Cross-perspective critiques
            critiques: list[tuple[str, str, str]] = []
            for agent in self._agents.values():
                for other_analysis in analyses:
                    if other_analysis.perspective != agent.perspective:
                        points = agent.critique(other_analysis)
                        for point in points:
                            critiques.append(
                                (agent.perspective.value, other_analysis.perspective.value, point)
                            )

            debate_rounds.append(
                DebateRound(
                    round_number=r,
                    analyses=analyses,
                    critiques=tuple(critiques),
                )
            )

            logger.info(
                "Debate round %d/%d: %d analyses, %d critiques",
                r + 1,
                rounds,
                len(analyses),
                len(critiques),
            )

        return debate_rounds

    # -- synthesis -----------------------------------------------------------

    def synthesize_perspectives(self, debate_rounds: list[DebateRound]) -> SynthesisResult:
        """Combine debate rounds into a balanced report.

        Args:
            debate_rounds: Output of ``debate()``.

        Returns:
            ``SynthesisResult`` with consensus, dissent, and balanced report.
        """
        if not debate_rounds:
            return SynthesisResult(topic="unknown")

        last_round = debate_rounds[-1]

        # Aggregate scores
        scores = [a.score for a in last_round.analyses]
        avg_confidence = sum(scores) / len(scores) if scores else 0.5

        # Identify consensus (insights shared by 3+ perspectives)
        insight_counter: Counter = Counter()
        for analysis in last_round.analyses:
            for insight in analysis.key_insights:
                insight_counter[insight] += 1

        consensus = tuple(
            insight for insight, count in insight_counter.items() if count >= 3
        )

        # Identify dissent (weaknesses / critiques unique to 1-2 perspectives)
        dissent: list[str] = []
        for analysis in last_round.analyses:
            for weakness in analysis.weaknesses:
                dissent.append(f"[{analysis.perspective.value}] {weakness}")

        # Build balanced report
        report_parts: list[str] = [
            "=== Multi-Perspective Synthesis Report ===\n",
            f"Confidence: {avg_confidence:.2f}\n",
        ]

        if consensus:
            report_parts.append("## Areas of Consensus")
            for point in consensus:
                report_parts.append(f"- {point}")

        report_parts.append("\n## Perspective Summaries")
        for analysis in last_round.analyses:
            report_parts.append(f"\n### {analysis.perspective.value.title()}")
            report_parts.append(f"Score: {analysis.score:.2f}")
            for insight in analysis.key_insights:
                report_parts.append(f"- {insight}")

        if dissent:
            report_parts.append("\n## Points of Disagreement")
            for point in dissent:
                report_parts.append(f"- {point}")

        balanced_report = "\n".join(report_parts)

        logger.info(
            "Synthesis complete: %d consensus, %d dissent, confidence=%.2f",
            len(consensus),
            len(dissent),
            avg_confidence,
        )
        return SynthesisResult(
            topic=last_round.analyses[0].key_insights[0] if last_round.analyses else "unknown",
            consensus_points=consensus,
            dissent_points=tuple(dissent),
            balanced_report=balanced_report,
            confidence=round(avg_confidence, 4),
        )

    # -- consensus / dissent -------------------------------------------------

    def identify_consensus(self, debate_rounds: list[DebateRound]) -> list[str]:
        """Extract areas of agreement across perspectives.

        Args:
            debate_rounds: Debate output.

        Returns:
            List of consensus statements.
        """
        if not debate_rounds:
            return []
        last = debate_rounds[-1]
        all_keywords: Counter = Counter()
        for analysis in last.analyses:
            for insight in analysis.key_insights:
                for word in insight.lower().split():
                    if len(word) > 4:
                        all_keywords[word] += 1

        # Words appearing in 4+ perspectives suggest consensus
        return sorted(
            word for word, count in all_keywords.items() if count >= 4
        )

    def highlight_dissent(self, debate_rounds: list[DebateRound]) -> list[str]:
        """Extract areas of productive disagreement.

        Args:
            debate_rounds: Debate output.

        Returns:
            List of dissent statements.
        """
        if not debate_rounds:
            return []
        last = debate_rounds[-1]
        dissent: list[str] = []
        for _, _, text in last.critiques:
            dissent.append(text)
        return dissent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_criteria(perspective: PerspectiveType) -> dict:
    """Build the heuristic criteria dictionary for a perspective."""
    criteria_map = {
        PerspectiveType.OPTIMIST: {
            "positive": ["breakthrough", "novel", "promising", "improvement",
                         "outperform", "state-of-the-art", "efficient", "scalable"],
            "concern": ["limitation", "failure", "risk"],
            "triggers": {
                "outperform": "Strong empirical results suggest a significant advance.",
                "novel": "Novelty indicates potential for high impact.",
                "improvement": "Incremental gains compound into meaningful progress.",
            },
        },
        PerspectiveType.SKEPTIC: {
            "positive": ["rigorous", "ablation", "reproducible", "baseline"],
            "concern": ["claim", "purport", "state-of-the-art", "breakthrough",
                        "revolutionize"],
            "triggers": {
                "state-of-the-art": "SOTA claims require careful benchmark scrutiny.",
                "without": "Claims of performance without proper baselines are suspect.",
                "simple": "Overly simple explanations may mask important complexity.",
            },
        },
        PerspectiveType.PRAGMATIST: {
            "positive": ["implementation", "deploy", "cost", "latency",
                         "throughput", "hardware", "memory"],
            "concern": ["theoretical", "asymptotic", "oracle"],
            "triggers": {
                "cost": "Cost considerations are critical for real-world adoption.",
                "hardware": "Hardware requirements determine practical feasibility.",
                "memory": "Memory constraints may limit deployment scenarios.",
            },
        },
        PerspectiveType.INNOVATOR: {
            "positive": ["novel", "unconventional", "cross-domain", "hybrid",
                         "combination", "analogy"],
            "concern": ["standard", "conventional", "traditional"],
            "triggers": {
                "novel": "A novel approach opens new research directions.",
                "combination": "Combining ideas from different domains can yield breakthroughs.",
                "hybrid": "Hybrid methods often outperform pure approaches.",
            },
        },
        PerspectiveType.HISTORIAN: {
            "positive": ["prior work", "historical", "evolution", "lineage",
                         "foundation", "classic"],
            "concern": ["first", "unprecedented", "revolutionary", "entirely new"],
            "triggers": {
                "prior": "Building on prior work is essential for cumulative progress.",
                "first": "Claims of being 'first' often ignore forgotten precedents.",
                "evolution": "Evolution of ideas reveals deeper research patterns.",
            },
        },
    }
    return criteria_map[perspective]


def _blindspots(from_p: PerspectiveType, to_p: PerspectiveType) -> list[str]:
    """Return natural blind-spot critiques from one perspective on another."""
    if from_p == to_p:
        return []

    pairs: dict[tuple[PerspectiveType, PerspectiveType], list[str]] = {
        (PerspectiveType.SKEPTIC, PerspectiveType.OPTIMIST): [
            "Optimistic framing may overstate significance.",
            "Positive results should be tempered with failure analysis.",
        ],
        (PerspectiveType.PRAGMATIST, PerspectiveType.INNOVATOR): [
            "Novel ideas must be grounded in implementation feasibility.",
            "Speculative directions need concrete evaluation plans.",
        ],
        (PerspectiveType.HISTORIAN, PerspectiveType.OPTIMIST): [
            "Historical patterns suggest breakthroughs are rarer than they appear.",
            "Optimism bias is well-documented in research communities.",
        ],
        (PerspectiveType.SKEPTIC, PerspectiveType.INNOVATOR): [
            "Novelty does not guarantee correctness.",
            "Innovation without rigorous testing is speculation.",
        ],
        (PerspectiveType.PRAGMATIST, PerspectiveType.OPTIMIST): [
            "Real-world constraints may limit applicability.",
            "Cost and scalability are under-emphasized.",
        ],
    }

    return pairs.get((from_p, to_p), [f"{to_p.value} perspective may overlook {from_p.value} concerns."])
