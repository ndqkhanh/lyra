"""
Collusion Detector — covert communication detection in multi-agent debates.

Detects collusive behaviour among debate panelists using three
orthogonal signals:

  1. **Metaphor profile divergence** (CoMet, arXiv 2505.18218):
     Compare the metaphor / framing profile of each agent.  Colluding
     agents converge on shared metaphor sets to signal covertly.

  2. **Narrative overfitting** (Lying with Truths, arXiv 2601.01685):
     Detect when an agent's arguments align too perfectly with another
     agent's expected position — narrative overfitting indicates
     pre-coordinated talking points.

  3. **Identity clustering** (Diversity Collapse, arXiv 2604.18005):
     When anonymized agents still cluster into identity-based voting
     blocs, collusion is likely.

Each signal produces a risk sub-score; the detector aggregates these
into a final CollusionRisk with an appropriate mitigation strategy.

References
----------
- CoMet: Metaphor-Driven Collusion Detection in Multi-Agent Debate.
  arXiv 2505.18218
- Lying with Truths: Narrative Overfitting as a Collusion Signal.
  arXiv 2601.01685
- Diversity Collapse in Multi-Agent Alignment.  arXiv 2604.18005
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from lyra.verification.debate_panel import Argument, Ballot, DebateResult, Perspective

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Risk Levels
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """Collusion risk severity."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Signal Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetaphorSignal:
    """Result of metaphor-profile divergence analysis.

    Attributes:
        detected: Whether anomalous metaphor convergence was found.
        score: 0.0 (no convergence) to 1.0 (full convergence).
        converging_pairs: List of (agent_a, agent_b, similarity) tuples
            that exceeded the threshold.
        dominant_metaphors: Most common shared metaphors across agents.
    """

    detected: bool
    score: float
    converging_pairs: list[tuple[str, str, float]]
    dominant_metaphors: list[str]


@dataclass(frozen=True)
class NarrativeOverfitSignal:
    """Result of narrative-overfitting analysis.

    Attributes:
        detected: Whether narrative overfitting was found.
        score: 0.0 to 1.0.
        overfitted_pairs: List of (agent_a, agent_b, overlap_score)
            tuples that exceed threshold.
        overlapping_claims: Shared claims or talking points.
    """

    detected: bool
    score: float
    overfitted_pairs: list[tuple[str, str, float]]
    overlapping_claims: list[str]


@dataclass(frozen=True)
class IdentityClusterSignal:
    """Result of identity-clustering analysis.

    Attributes:
        detected: Whether identity-based bloc voting was found.
        score: 0.0 to 1.0.
        clusters: Mapping from cluster label to list of agent IDs.
        cluster_agreement: Per-cluster voting agreement rate.
    """

    detected: bool
    score: float
    clusters: dict[str, list[str]]
    cluster_agreement: float


@dataclass(frozen=True)
class CollusionRisk:
    """Aggregated collusion risk assessment.

    Attributes:
        risk_level: Overall risk severity.
        risk_score: 0.0 (no risk) to 1.0 (confirmed collusion).
        metaphor_signal: Result from metaphor-profile analysis.
        narrative_signal: Result from narrative-overfitting analysis.
        identity_signal: Result from identity-clustering analysis.
        mitigation: Recommended mitigation action.
        signals_triggered: Which signals contributed (metaphor,
            narrative, identity).
    """

    risk_level: RiskLevel
    risk_score: float
    metaphor_signal: MetaphorSignal | None
    narrative_signal: NarrativeOverfitSignal | None
    identity_signal: IdentityClusterSignal | None
    mitigation: str
    signals_triggered: tuple[str, ...]


# ---------------------------------------------------------------------------
# CollusionDetector
# ---------------------------------------------------------------------------


class CollusionDetector:
    """Detects collusive behaviour in multi-agent debates.

    Usage::

        detector = CollusionDetector()
        risk = detector.monitor_communication(
            debate_result.arguments, debate_result.voting_record
        )
        if risk.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            mitigation = risk.mitigation  # "force_identity_anonymization"
    """

    # Common metaphor / framing categories
    _METAPHOR_WAR = frozenset({
        "attack", "defend", "fight", "battle", "win", "lose",
        "victory", "defeat", "strategy", "weapon", "armor",
        "offensive", "defensive", "campaign", "retreat",
    })

    _METAPHOR_HEALTH = frozenset({
        "healthy", "sick", "diagnosis", "cure", "treatment",
        "symptom", "disease", "recovery", "heal", "patient",
        "prescription", "therapy",
    })

    _METAPHOR_JOURNEY = frozenset({
        "path", "road", "direction", "destination", "milestone",
        "step", "progress", "journey", "trajectory", "route",
        "map", "guide", "forward", "ahead",
    })

    _METAPHOR_CONSTRUCTION = frozenset({
        "build", "foundation", "structure", "framework",
        "scaffold", "pillar", "cornerstone", "architecture",
        "blueprint", "design", "construct", "erect",
    })

    _METAPHOR_CATEGORIES: dict[str, frozenset] = {
        "war": _METAPHOR_WAR,
        "health": _METAPHOR_HEALTH,
        "journey": _METAPHOR_JOURNEY,
        "construction": _METAPHOR_CONSTRUCTION,
    }

    def __init__(
        self,
        metaphor_threshold: float = 0.6,
        narrative_threshold: float = 0.7,
        identity_threshold: float = 0.65,
        combined_threshold_low: float = 0.15,
        combined_threshold_medium: float = 0.35,
        combined_threshold_high: float = 0.55,
        combined_threshold_critical: float = 0.75,
    ) -> None:
        """
        Args:
            metaphor_threshold: Jaccard similarity above this flags
                metaphor convergence.
            narrative_threshold: Claim overlap above this flags
                narrative overfitting.
            identity_threshold: Bloc voting agreement above this
                flags identity clustering.
            combined_threshold_*: Overall risk score boundaries.
        """
        self._metaphor_threshold = metaphor_threshold
        self._narrative_threshold = narrative_threshold
        self._identity_threshold = identity_threshold
        self._thresholds = {
            "low": combined_threshold_low,
            "medium": combined_threshold_medium,
            "high": combined_threshold_high,
            "critical": combined_threshold_critical,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def monitor_communication(
        self,
        arguments: tuple[Argument, ...],
        voting_record: tuple[Ballot, ...],
    ) -> CollusionRisk:
        """Run all collusion detection signals on a debate.

        Args:
            arguments: All arguments from the debate.
            voting_record: All ballots cast.

        Returns:
            CollusionRisk with aggregated risk and mitigation.
        """
        # Run three detection signals
        metaphor_signal = self._detect_metaphor_profile_divergence(arguments)
        narrative_signal = self._detect_narrative_overfitting(arguments)
        identity_signal = self._detect_identity_clustering(
            arguments, voting_record
        )

        # Aggregate risk
        signals_triggered: list[str] = []
        score = 0.0
        n_signals = 0

        if metaphor_signal.detected:
            signals_triggered.append("metaphor")
            score += metaphor_signal.score
            n_signals += 1

        if narrative_signal.detected:
            signals_triggered.append("narrative")
            score += narrative_signal.score
            n_signals += 1

        if identity_signal.detected:
            signals_triggered.append("identity")
            score += identity_signal.score
            n_signals += 1

        risk_score = score / max(n_signals, 1)

        risk_level = self._classify_risk(risk_score)
        mitigation = self._select_mitigation(
            risk_level, signals_triggered
        )

        return CollusionRisk(
            risk_level=risk_level,
            risk_score=round(risk_score, 4),
            metaphor_signal=metaphor_signal,
            narrative_signal=narrative_signal,
            identity_signal=identity_signal,
            mitigation=mitigation,
            signals_triggered=tuple(signals_triggered),
        )

    # ------------------------------------------------------------------
    # Signal 1: Metaphor Profile Divergence (CoMet)
    # ------------------------------------------------------------------

    def _detect_metaphor_profile_divergence(
        self,
        arguments: tuple[Argument, ...],
    ) -> MetaphorSignal:
        """Detect abnormal metaphor convergence across agents.

        Computes a metaphor profile for each agent (distribution over
        metaphor categories).  Colluding agents share unusually similar
        profiles.
        """
        agent_profiles: dict[str, Counter] = {}

        for arg in arguments:
            if arg.anonymous_id not in agent_profiles:
                agent_profiles[arg.anonymous_id] = Counter()
            category = self._classify_metaphor(arg.content)
            if category:
                agent_profiles[arg.anonymous_id][category] += 1

        # Compute pairwise Jaccard similarity
        agent_ids = list(agent_profiles.keys())
        converging_pairs: list[tuple[str, str, float]] = []

        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                sim = self._jaccard_metaphor(
                    agent_profiles[agent_ids[i]],
                    agent_profiles[agent_ids[j]],
                )
                if sim >= self._metaphor_threshold:
                    converging_pairs.append((agent_ids[i], agent_ids[j], round(sim, 4)))

        detected = len(converging_pairs) > 0
        score = self._aggregate_pair_score(converging_pairs, len(agent_ids))

        # Dominant metaphors across all agents
        global_metaphors: Counter = Counter()
        for profile in agent_profiles.values():
            global_metaphors.update(profile)
        dominant = [cat for cat, _ in global_metaphors.most_common(3)]

        return MetaphorSignal(
            detected=detected,
            score=round(score, 4),
            converging_pairs=converging_pairs,
            dominant_metaphors=dominant,
        )

    def _classify_metaphor(self, text: str) -> str | None:
        """Classify text into a metaphor category, if any."""
        lower = text.lower()
        for category, keywords in self._METAPHOR_CATEGORIES.items():
            if any(kw in lower for kw in keywords):
                return category
        return None

    @staticmethod
    def _jaccard_metaphor(
        profile_a: Counter,
        profile_b: Counter,
    ) -> float:
        """Jaccard similarity between two metaphor profiles."""
        all_categories = set(profile_a) | set(profile_b)
        if not all_categories:
            return 0.0

        intersection = sum(
            min(profile_a.get(c, 0), profile_b.get(c, 0))
            for c in all_categories
        )
        union = sum(
            max(profile_a.get(c, 0), profile_b.get(c, 0))
            for c in all_categories
        )
        return intersection / union if union > 0 else 0.0

    # ------------------------------------------------------------------
    # Signal 2: Narrative Overfitting (Lying with Truths)
    # ------------------------------------------------------------------

    def _detect_narrative_overfitting(
        self,
        arguments: tuple[Argument, ...],
    ) -> NarrativeOverfitSignal:
        """Detect when agents share unusually similar claims.

        Extracts claim-like phrases and compares overlap between agents.
        """
        agent_claims: dict[str, set[str]] = {}

        for arg in arguments:
            if arg.anonymous_id not in agent_claims:
                agent_claims[arg.anonymous_id] = set()
            claims = self._extract_claims(arg.content)
            agent_claims[arg.anonymous_id].update(claims)

        agent_ids = list(agent_claims.keys())
        overfitted_pairs: list[tuple[str, str, float]] = []
        all_overlapping: set[str] = set()

        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                overlap = self._compute_claim_overlap(
                    agent_claims[agent_ids[i]],
                    agent_claims[agent_ids[j]],
                )
                if overlap >= self._narrative_threshold:
                    overfitted_pairs.append(
                        (agent_ids[i], agent_ids[j], round(overlap, 4))
                    )
                    shared = agent_claims[agent_ids[i]] & agent_claims[agent_ids[j]]
                    all_overlapping.update(shared)

        detected = len(overfitted_pairs) > 0
        score = self._aggregate_pair_score(overfitted_pairs, len(agent_ids))

        return NarrativeOverfitSignal(
            detected=detected,
            score=round(score, 4),
            overfitted_pairs=overfitted_pairs,
            overlapping_claims=sorted(all_overlapping)[:10],
        )

    @staticmethod
    def _extract_claims(text: str) -> set[str]:
        """Extract claim-like phrases from argument text.

        Looks for declarative statements that represent factual claims.
        """
        claims: set[str] = set()

        # Pattern: "X is Y", "X are Y", "X should Y"
        patterns = [
            r"(?:The\s+)?\w+\s+is\s+\w[^.,;!?]+",
            r"(?:The\s+)?\w+\s+are\s+\w[^.,;!?]+",
            r"(?:The\s+)?\w+\s+should\s+\w[^.,;!?]+",
            r"(?:The\s+)?\w+\s+must\s+\w[^.,;!?]+",
            r"(?:The\s+)?\w+\s+provides?\s+\w[^.,;!?]+",
            r"(?:The\s+)?\w+\s+enables?\s+\w[^.,;!?]+",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                # Normalise: lowercase, strip trailing punctuation
                normalised = m.strip().rstrip(".,;!?").lower()
                if len(normalised) > 15:  # Minimum meaningful claim length
                    claims.add(normalised)

        return claims

    @staticmethod
    def _compute_claim_overlap(
        claims_a: set[str],
        claims_b: set[str],
    ) -> float:
        """Jaccard overlap of claim sets between two agents."""
        if not claims_a or not claims_b:
            return 0.0
        intersection = len(claims_a & claims_b)
        union = len(claims_a | claims_b)
        return intersection / union if union > 0 else 0.0

    # ------------------------------------------------------------------
    # Signal 3: Identity Clustering (Diversity Collapse)
    # ------------------------------------------------------------------

    def _detect_identity_clustering(
        self,
        arguments: tuple[Argument, ...],
        voting_record: tuple[Ballot, ...],
    ) -> IdentityClusterSignal:
        """Detect when agents cluster into identity-based voting blocs.

        Identifies clusters by mapping agent perspectives to their
        anonymized IDs and checking for high intra-cluster voting
        agreement.
        """
        # Build perspective -> agent mapping
        perspective_agents: dict[str, list[str]] = {}
        for arg in arguments:
            key = arg.perspective.value if hasattr(arg.perspective, "value") else str(arg.perspective)  # fmt: skip
            if key not in perspective_agents:
                perspective_agents[key] = []
            if arg.anonymous_id not in perspective_agents[key]:
                perspective_agents[key].append(arg.anonymous_id)

        # Build ballot lookup
        ballot_by_id: dict[str, Ballot] = {
            b.anonymous_id: b for b in voting_record
        }

        # Measure intra-cluster agreement
        cluster_agreements: list[float] = []

        for cluster_id, agent_ids in perspective_agents.items():
            if len(agent_ids) < 2:
                continue
            cluster_votes = [
                ballot_by_id[a].approve
                for a in agent_ids
                if a in ballot_by_id
            ]
            if len(cluster_votes) < 2:
                continue
            # Agreement = fraction voting the same way
            approve_count = sum(1 for v in cluster_votes if v)
            majority = max(approve_count, len(cluster_votes) - approve_count)
            agreement = majority / len(cluster_votes)
            cluster_agreements.append(agreement)

        if not cluster_agreements:
            return IdentityClusterSignal(
                detected=False,
                score=0.0,
                clusters={},
                cluster_agreement=0.0,
            )

        mean_agreement = sum(cluster_agreements) / len(cluster_agreements)
        detected = mean_agreement >= self._identity_threshold

        return IdentityClusterSignal(
            detected=detected,
            score=round(mean_agreement, 4),
            clusters={k: v for k, v in perspective_agents.items()},
            cluster_agreement=round(mean_agreement, 4),
        )

    # ------------------------------------------------------------------
    # Aggregation & Mitigation
    # ------------------------------------------------------------------

    def _classify_risk(self, score: float) -> RiskLevel:
        """Map a risk score to a RiskLevel."""
        if score >= self._thresholds["critical"]:
            return RiskLevel.CRITICAL
        if score >= self._thresholds["high"]:
            return RiskLevel.HIGH
        if score >= self._thresholds["medium"]:
            return RiskLevel.MEDIUM
        if score >= self._thresholds["low"]:
            return RiskLevel.LOW
        return RiskLevel.NONE

    @staticmethod
    def _select_mitigation(
        risk_level: RiskLevel,
        signals_triggered: list[str],
    ) -> str:
        """Choose the appropriate mitigation strategy."""
        if risk_level == RiskLevel.NONE:
            return "none"

        mitigations: list[str] = []

        if risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            mitigations.append("force_identity_anonymization")
            mitigations.append("inject_disruption_agent")

        if risk_level == RiskLevel.MEDIUM:
            if "metaphor" in signals_triggered:
                mitigations.append("force_identity_anonymization")
            if "narrative" in signals_triggered:
                mitigations.append("inject_disruption_agent")
            mitigations.append("randomized_topology")

        if risk_level == RiskLevel.LOW:
            mitigations.append("randomized_topology")

        return "; ".join(mitigations) if mitigations else "none"

    @staticmethod
    def _aggregate_pair_score(
        pairs: list[tuple[str, str, float]],
        n_agents: int,
    ) -> float:
        """Aggregate pairwise scores into a 0-1 signal score."""
        if n_agents < 2 or not pairs:
            return 0.0
        mean_pair_score = sum(p[2] for p in pairs) / len(pairs)
        # Weight by proportion of possibly-colluding agents
        unique_colluders = len({p[0] for p in pairs} | {p[1] for p in pairs})
        coverage = unique_colluders / n_agents
        return mean_pair_score * coverage
