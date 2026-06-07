"""
Adversarial Verification — multi-agent debate panel for claim verification.

Implements a 3-agent adversarial verification loop that cross-checks
research claims against an ``EvidenceGraph``, triangulates across
multiple independent sources, and produces confidence-bracketed verdicts.
An appeal process allows rejected claims to be revised and resubmitted
with new evidence.

Key features
------------
- **3-agent debate panel**: each agent reviews the claim independently
  from a different perspective (supporter, skeptic, domain expert).
- **Cross-source triangulation**: verify against 3+ independent sources
  in the evidence graph.
- **ConfidenceBracket**: HIGH (>2/3 agree), MEDIUM (split), LOW (<1/3 agree).
- **Appeal process**: if a claim is rejected, the author can revise and
  resubmit with new evidence for re-verification.

References
----------
- Constitutional AI: Bai et al., Anthropic, 2022
- DeepScientist/DGM: arXiv 2505.22954v3
- Argus evidence graph: arXiv 2503.12419
"""

from __future__ import annotations

import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from lyra.research.evidence_graph import (
    EdgeType,
    EvidenceGraph,
    GraphQuery,
    VerificationResult,
    VerificationStatus,
)


# =============================================================================
# Enums and data structures
# =============================================================================


class ConfidenceBracket(str, Enum):
    """Confidence bracket based on panel agreement.

    - **HIGH**: >2/3 of panelists agree.
    - **MEDIUM**: panel is split (1/3 to 2/3).
    - **LOW**: <1/3 of panelists agree.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentRole(str, Enum):
    """Role/perspective for an adversarial verification agent."""

    SUPPORTER = "supporter"
    SKEPTIC = "skeptic"
    DOMAIN_EXPERT = "domain_expert"


@dataclass(frozen=True)
class PanelVerdict:
    """Individual verdict from a single panel agent.

    Attributes:
        agent_id: Identifier for the agent.
        role: The agent's assigned perspective.
        approved: Whether the agent approves the claim.
        confidence: Agent's confidence in their verdict (0.0–1.0).
        reasoning: Free-text justification.
        supporting_sources: Sources the agent considers supporting.
        contradicting_sources: Sources the agent considers contradicting.
    """

    agent_id: str
    role: AgentRole
    approved: bool
    confidence: float
    reasoning: str = ""
    supporting_sources: tuple[str, ...] = ()
    contradicting_sources: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "approved": self.approved,
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
            "supporting_sources": list(self.supporting_sources),
            "contradicting_sources": list(self.contradicting_sources),
        }


@dataclass(frozen=True)
class Verdict:
    """Final verdict from the adversarial verification loop.

    Attributes:
        verdict_id: Unique identifier.
        claim: The claim that was verified.
        approved: Whether the claim passed verification.
        confidence_bracket: HIGH / MEDIUM / LOW.
        mean_confidence: Average confidence across all panelists.
        panel_verdicts: All individual panelist verdicts.
        cross_source_count: Number of independent sources triangulated.
        triangulation_summary: Description of source agreement.
        appeal_available: Whether an appeal can be filed.
        timestamp: Unix timestamp.
    """

    verdict_id: str = ""
    claim: str = ""
    approved: bool = False
    confidence_bracket: ConfidenceBracket = ConfidenceBracket.LOW
    mean_confidence: float = 0.0
    panel_verdicts: tuple[PanelVerdict, ...] = ()
    cross_source_count: int = 0
    triangulation_summary: str = ""
    appeal_available: bool = True
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict_id": self.verdict_id,
            "claim": self.claim,
            "approved": self.approved,
            "confidence_bracket": self.confidence_bracket.value,
            "mean_confidence": round(self.mean_confidence, 4),
            "panel_verdicts": [v.to_dict() for v in self.panel_verdicts],
            "cross_source_count": self.cross_source_count,
            "triangulation_summary": self.triangulation_summary,
            "appeal_available": self.appeal_available,
            "timestamp": self.timestamp,
        }


# =============================================================================
# Agent signature types
# =============================================================================

# A verification agent: (claim, evidence_graph, role) -> PanelVerdict
VerificationAgent = Callable[[str, EvidenceGraph, AgentRole], PanelVerdict]


# =============================================================================
# Default stub agents
# =============================================================================


def _default_supporter(
    claim: str, graph: EvidenceGraph, role: AgentRole
) -> PanelVerdict:
    """Default stub supporter agent.

    Scans the evidence graph for nodes that support the claim and
    returns an approving verdict.
    """
    supporting = graph.find_evidence_for(claim, top_k=5)
    sources = tuple(n.source for n in supporting if n.source)
    confidence = (
        sum(n.confidence for n in supporting) / max(len(supporting), 1)
    )

    if supporting:
        reasoning = (
            f"Found {len(supporting)} supporting evidence nodes in the graph. "
            f"Average confidence: {confidence:.2f}."
        )
        approved = confidence >= 0.5
    else:
        reasoning = "No supporting evidence found, but no contradicting evidence either."
        approved = True  # Default to approve when no evidence either way

    return PanelVerdict(
        agent_id="supporter-001",
        role=role,
        approved=approved,
        confidence=max(0.3, min(1.0, confidence)),
        reasoning=reasoning,
        supporting_sources=tuple(sources),
    )


def _default_skeptic(
    claim: str, graph: EvidenceGraph, role: AgentRole
) -> PanelVerdict:
    """Default stub skeptic agent.

    Scans the evidence graph for contradicting evidence and returns
    a challenging verdict.
    """
    contradicting = graph.find_evidence_against(claim, top_k=5)
    sources = tuple(n.source for n in contradicting if n.source)
    confidence = (
        sum(n.confidence for n in contradicting)
        / max(len(contradicting), 1)
    )

    if contradicting:
        reasoning = (
            f"Found {len(contradicting)} contradicting evidence nodes. "
            f"Average confidence: {confidence:.2f}."
        )
        approved = confidence < 0.3
    else:
        reasoning = "No contradicting evidence found in the graph."
        approved = True  # Default to approve when no evidence found

    return PanelVerdict(
        agent_id="skeptic-001",
        role=role,
        approved=approved,
        confidence=max(0.3, min(1.0, 1.0 - confidence)),
        reasoning=reasoning,
        contradicting_sources=tuple(sources),
    )


def _default_domain_expert(
    claim: str, graph: EvidenceGraph, role: AgentRole
) -> PanelVerdict:
    """Default stub domain expert agent.

    Cross-references the claim against all evidence in the graph and
    returns a balanced verdict based on evidence balance.
    """
    supporting = graph.find_evidence_for(claim, top_k=5)
    contradicting = graph.find_evidence_against(claim, top_k=5)

    support_conf = (
        sum(n.confidence for n in supporting) / max(len(supporting), 1)
    )
    contradict_conf = (
        sum(n.confidence for n in contradicting)
        / max(len(contradicting), 1)
    )

    balance = len(supporting) * support_conf - len(contradicting) * contradict_conf

    if balance > 0.5:
        approved = True
        reasoning = (
            f"Evidence balance is positive ({balance:.2f}). "
            f"{len(supporting)} supporting vs {len(contradicting)} contradicting."
        )
        confidence = 0.5 + min(0.5, balance)
    elif balance < -0.3:
        approved = False
        reasoning = (
            f"Evidence balance is negative ({balance:.2f}). "
            f"{len(supporting)} supporting vs {len(contradicting)} contradicting."
        )
        confidence = 0.5 + min(0.5, -balance)
    else:
        approved = True
        reasoning = (
            f"Evidence balance is near-neutral ({balance:.2f}). "
            f"Approving with caution."
        )
        confidence = 0.5

    return PanelVerdict(
        agent_id="expert-001",
        role=role,
        approved=approved,
        confidence=confidence,
        reasoning=reasoning,
        supporting_sources=tuple(n.source for n in supporting if n.source),
        contradicting_sources=tuple(n.source for n in contradicting if n.source),
    )


# Default panel of 3 agents
_DEFAULT_PANEL: tuple[tuple[AgentRole, VerificationAgent], ...] = (
    (AgentRole.SUPPORTER, _default_supporter),
    (AgentRole.SKEPTIC, _default_skeptic),
    (AgentRole.DOMAIN_EXPERT, _default_domain_expert),
)


# =============================================================================
# AdversarialVerificationLoop
# =============================================================================


class AdversarialVerificationLoop:
    """Multi-agent adversarial verification for research claims.

    A 3-agent debate panel (supporter, skeptic, domain expert) reviews
    each claim independently, cross-referencing against the evidence graph.
    Verdicts are aggregated into confidence-bracketed outcomes. Rejected
    claims can appeal with new evidence.

    Usage::

        graph = EvidenceGraph()
        verifier = AdversarialVerificationLoop(evidence_graph=graph)

        # Verify a claim
        verdict = verifier.verify_claim("LoRA reduces memory by 4x")

        # Cross-source triangulation
        result = verifier.triangulate(claim, min_sources=3)

        # Appeal a rejected claim
        graph.add_evidence("New evidence...", source="arxiv:2302.0", confidence=0.9)
        appeal_verdict = verifier.appeal(verdict.verdict_id)
    """

    def __init__(
        self,
        evidence_graph: EvidenceGraph,
        panel: (
            list[tuple[AgentRole, VerificationAgent]] | None
        ) = None,
        min_sources_for_triangulation: int = 3,
        max_appeals: int = 3,
    ) -> None:
        """
        Args:
            evidence_graph: The shared ``EvidenceGraph`` to cross-reference.
            panel: List of ``(AgentRole, VerificationAgent)`` pairs.
                Defaults to three agents: supporter, skeptic, domain expert.
            min_sources_for_triangulation: Minimum number of independent
                sources required for HIGH confidence.
            max_appeals: Maximum number of appeals per claim.
        """
        self.graph = evidence_graph
        self._panel = list(panel or _DEFAULT_PANEL)
        self._min_sources = min_sources_for_triangulation
        self._max_appeals = max_appeals

        # Verdict store: verdict_id -> Verdict
        self._verdicts: dict[str, Verdict] = {}

        # Appeal tracker: claim_hash -> [verdict_ids]
        self._appeal_tracker: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Core verification
    # ------------------------------------------------------------------

    def verify_claim(
        self,
        claim: str,
        evidence_graph: EvidenceGraph | None = None,
        sources: list[str] | None = None,
    ) -> Verdict:
        """Run the adversarial verification loop on a claim.

        Each panelist independently reviews the claim against the evidence
        graph (or an optionally provided sub-graph). Verdicts are aggregated
        into a final ``Verdict`` with confidence bracket.

        Args:
            claim: The claim to verify.
            evidence_graph: Optional sub-graph to use instead of the main graph.
            sources: Optional pre-identified source list for triangulation.

        Returns:
            The aggregated ``Verdict``.
        """
        graph = evidence_graph or self.graph
        verdict_id = str(uuid.uuid4())
        now = time.time()

        panel_verdicts: list[PanelVerdict] = []
        for role, agent_fn in self._panel:
            pv = agent_fn(claim, graph, role)
            panel_verdicts.append(pv)

        # --- Aggregate ---
        approve_count = sum(1 for v in panel_verdicts if v.approved)
        total_votes = len(panel_verdicts)
        approve_ratio = approve_count / max(total_votes, 1)

        approved = approve_ratio > 0.5
        mean_confidence = (
            sum(v.confidence for v in panel_verdicts) / max(total_votes, 1)
        )

        # Confidence bracket
        if approve_ratio > 2.0 / 3.0 or (1 - approve_ratio) > 2.0 / 3.0:
            bracket = ConfidenceBracket.HIGH
        elif approve_ratio > 1.0 / 3.0:
            bracket = ConfidenceBracket.MEDIUM
        else:
            bracket = ConfidenceBracket.LOW

        # Cross-source count
        all_sources: set[str] = set()
        for pv in panel_verdicts:
            all_sources.update(pv.supporting_sources)
            all_sources.update(pv.contradicting_sources)
        if sources:
            all_sources.update(sources)

        cross_source_count = len(
            {s for s in all_sources if s}
        )

        # Triangulation summary
        triangulation_summary = self._build_triangulation_summary(
            panel_verdicts, cross_source_count
        )

        # Appeal availability
        claim_key = self._claim_key(claim)
        prior_appeals = len(self._appeal_tracker.get(claim_key, []))
        appeal_available = prior_appeals < self._max_appeals

        verdict = Verdict(
            verdict_id=verdict_id,
            claim=claim,
            approved=approved,
            confidence_bracket=bracket,
            mean_confidence=round(mean_confidence, 4),
            panel_verdicts=tuple(panel_verdicts),
            cross_source_count=cross_source_count,
            triangulation_summary=triangulation_summary,
            appeal_available=appeal_available,
            timestamp=now,
        )

        self._verdicts[verdict_id] = verdict
        self._appeal_tracker.setdefault(claim_key, []).append(verdict_id)

        # Record the verification result in the evidence graph
        self._record_in_graph(claim, verdict, graph)

        return verdict

    # ------------------------------------------------------------------
    # Cross-source triangulation
    # ------------------------------------------------------------------

    def triangulate(
        self,
        claim: str,
        min_sources: int | None = None,
        evidence_graph: EvidenceGraph | None = None,
    ) -> dict[str, Any]:
        """Cross-source triangulation: verify against 3+ independent sources.

        Queries the evidence graph for the claim and analyses source
        agreement across independent sources.

        Args:
            claim: The claim to triangulate.
            min_sources: Minimum number of sources required (defaults to
                ``self._min_sources``).
            evidence_graph: Optional sub-graph.

        Returns:
            Dict with ``source_agreement``, ``unique_sources``, ``verdict``,
            and ``score``.
        """
        graph = evidence_graph or self.graph
        min_src = min_sources or self._min_sources

        # Run the verification first
        verdict = self.verify_claim(claim, evidence_graph=graph)

        # Collect unique sources from the verdict
        all_sources: set[str] = set()
        for pv in verdict.panel_verdicts:
            all_sources.update(pv.supporting_sources)
            all_sources.update(pv.contradicting_sources)

        unique_sources = sorted({s for s in all_sources if s})

        # Analyse source agreement
        source_votes: dict[str, list[bool]] = {}
        for pv in verdict.panel_verdicts:
            for src in pv.supporting_sources:
                if src:
                    source_votes.setdefault(src, []).append(True)
            for src in pv.contradicting_sources:
                if src:
                    source_votes.setdefault(src, []).append(False)

        # Per-source agreement
        source_agreement: dict[str, float] = {}
        for src, votes in source_votes.items():
            agree_ratio = sum(1 for v in votes if v) / max(len(votes), 1)
            source_agreement[src] = round(agree_ratio, 4)

        # Overall triangulation score
        if len(unique_sources) >= min_src and verdict.approved:
            score = min(1.0, len(unique_sources) / max(min_src, 1))
        elif len(unique_sources) >= min_src:
            score = max(0.0, 1.0 - len(unique_sources) / max(min_src, 1))
        else:
            score = 0.0

        return {
            "verdict": verdict.to_dict(),
            "unique_sources": unique_sources,
            "source_count": len(unique_sources),
            "minimum_required": min_src,
            "source_agreement": source_agreement,
            "triangulation_score": round(score, 4),
            "triangulation_passed": len(unique_sources) >= min_src,
        }

    # ------------------------------------------------------------------
    # Appeal process
    # ------------------------------------------------------------------

    def appeal(
        self,
        original_verdict_id: str,
        revised_claim: str | None = None,
    ) -> Verdict | None:
        """Appeal a rejected claim with optional revised text.

        If the original verdict was approved, no appeal is needed (returns
        the original verdict). Otherwise, re-runs verification and records
        the new verdict.

        Args:
            original_verdict_id: The verdict to appeal.
            revised_claim: Optionally revised claim text. If ``None``,
                uses the original claim.

        Returns:
            New ``Verdict`` from the appeal, or ``None`` if the maximum
            number of appeals has been exhausted.
        """
        original = self._verdicts.get(original_verdict_id)
        if original is None:
            return None

        # Check if appeal is still available
        if not original.appeal_available:
            return None

        # If already approved, return the original
        if original.approved:
            return original

        claim = revised_claim or original.claim
        claim_key = self._claim_key(original.claim)
        prior_appeals = len(self._appeal_tracker.get(claim_key, []))

        # Check max appeals using the original claim key
        if prior_appeals >= self._max_appeals:
            return None

        # Re-run verification
        verdict = self.verify_claim(claim)

        # Mark appeal as consumed if no revised claim (same claim re-verified)
        if revised_claim is None:
            verdict_verdict = self._verdicts.get(verdict.verdict_id)
            if verdict_verdict is not None:
                has_appeals = (
                    len(self._appeal_tracker.get(claim_key, []))
                    < self._max_appeals
                )
                verdict_verdict = Verdict(
                    verdict_id=verdict_verdict.verdict_id,
                    claim=verdict_verdict.claim,
                    approved=verdict_verdict.approved,
                    confidence_bracket=verdict_verdict.confidence_bracket,
                    mean_confidence=verdict_verdict.mean_confidence,
                    panel_verdicts=verdict_verdict.panel_verdicts,
                    cross_source_count=verdict_verdict.cross_source_count,
                    triangulation_summary=verdict_verdict.triangulation_summary,
                    appeal_available=has_appeals,
                    timestamp=verdict_verdict.timestamp,
                )
                self._verdicts[verdict.verdict_id] = verdict_verdict

        return verdict

    def get_verdict(self, verdict_id: str) -> Verdict | None:
        """Retrieve a stored verdict by ID."""
        return self._verdicts.get(verdict_id)

    def get_appeal_history(self, claim: str) -> list[Verdict]:
        """Return the full appeal history for a claim.

        Args:
            claim: The claim to look up.

        Returns:
            List of ``Verdict`` instances in chronological order.
        """
        claim_key = self._claim_key(claim)
        verdict_ids = self._appeal_tracker.get(claim_key, [])
        return [
            self._verdicts[vid]
            for vid in verdict_ids
            if vid in self._verdicts
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_in_graph(
        self,
        claim: str,
        verdict: Verdict,
        graph: EvidenceGraph,
    ) -> None:
        """Record the verification outcome as evidence in the graph.

        Creates a new evidence node for the claim (if one doesn't exist)
        and adds SUPPORTS/CONTRADICTS edges based on the verdict.
        """
        # Check if a similar node already exists
        existing = graph.query(
            GraphQuery(claim_substring=claim[:60], limit=1)
        )

        if existing:
            node_id = existing[0].node_id
        else:
            node_id = graph.add_evidence(
                claim=claim,
                source=f"adversarial-verification/{verdict.verdict_id}",
                confidence=verdict.mean_confidence,
                metadata={
                    "verdict_id": verdict.verdict_id,
                    "verification_method": "adversarial_panel",
                },
            )

        # If verdict approves, mark node based on confidence bracket
        if verdict.approved:
            confidence = 0.7 if verdict.confidence_bracket == ConfidenceBracket.HIGH else 0.5
            graph.update_node(
                node_id,
                verification_status=VerificationStatus.VERIFIED,
                confidence=max(graph.get_node(node_id).confidence if graph.get_node(node_id) else 0, confidence),
            )
        else:
            confidence = 0.3 if verdict.confidence_bracket == ConfidenceBracket.LOW else 0.4
            graph.update_node(
                node_id,
                verification_status=VerificationStatus.DISPUTED,
                confidence=min(
                    graph.get_node(node_id).confidence if graph.get_node(node_id) else 1,
                    confidence,
                ),
            )

    @staticmethod
    def _build_triangulation_summary(
        panel_verdicts: list[PanelVerdict],
        cross_source_count: int,
    ) -> str:
        """Build a human-readable triangulation summary."""
        approve_count = sum(1 for v in panel_verdicts if v.approved)
        total = len(panel_verdicts)

        source_plural = "source" if cross_source_count == 1 else "sources"
        return (
            f"Panel: {approve_count}/{total} agents approve. "
            f"Triangulated across {cross_source_count} {source_plural}."
        )

    @staticmethod
    def _claim_key(claim: str) -> str:
        """Normalize a claim to a stable key for appeal tracking."""
        return claim.lower().strip()
