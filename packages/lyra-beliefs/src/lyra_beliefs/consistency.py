"""Belief consistency management: contradiction detection, resolution, minimal inconsistent subset finding, paraconsistent reasoning."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .belief_system import Belief, BeliefStatus, BeliefSystem

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────────


@dataclass
class Contradiction:
    """A detected contradiction between two or more beliefs.

    Attributes:
        belief_ids: The beliefs involved.
        reason: Why they contradict.
        severity: How severe the contradiction is (0-1).
        detected_at: When detected.
        resolved: Whether resolved.
    """

    belief_ids: list[str] = field(default_factory=list)
    reason: str = ""
    severity: float = 0.5
    detected_at: float = 0.0
    resolved: bool = False


@dataclass
class InconsistentSubset:
    """A minimal (or near-minimal) inconsistent subset of beliefs.

    Attributes:
        belief_ids: The beliefs forming the inconsistent subset.
        size: Number of beliefs.
        contradiction_type: Type of inconsistency.
    """

    belief_ids: list[str] = field(default_factory=list)
    size: int = 0
    contradiction_type: str = ""


@dataclass
class ResolutionStrategy:
    """Strategy for resolving a contradiction.

    Attributes:
        name: Strategy name.
        description: How it works.
        recommended_for: Suitable contradiction types.
    """

    name: str
    description: str
    recommended_for: list[str] = field(default_factory=list)


# ── Consistency Manager ────────────────────────────────────────────────


class ConsistencyManager:
    """Manages belief consistency: detects contradictions, finds minimal
    inconsistent subsets, and provides resolution strategies including
    paraconsistent reasoning support.
    """

    # Negation/opposition word pairs for contradiction detection
    OPPOSITION_PAIRS: list[tuple[set[str], set[str]]] = [
        ({"always", "must", "certainly", "definitely"}, {"never", "cannot", "impossible"}),
        ({"good", "effective", "best", "optimal"}, {"bad", "poor", "worst", "ineffective"}),
        ({"increase", "rise", "grow", "accelerate"}, {"decrease", "fall", "decline", "decelerate"}),
        ({"fast", "quick", "rapid", "instant"}, {"slow", "gradual", "delayed"}),
        ({"safe", "secure", "protected"}, {"dangerous", "insecure", "vulnerable"}),
        ({"simple", "easy", "trivial"}, {"complex", "difficult", "hard"}),
        ({"true", "correct", "accurate", "right"}, {"false", "wrong", "incorrect", "inaccurate"}),
        ({"possible", "feasible", "achievable"}, {"impossible", "infeasible"}),
    ]

    def __init__(self, belief_system: BeliefSystem) -> None:
        self.belief_system = belief_system
        self._contradictions: deque[Contradiction] = deque(maxlen=1000)
        self._resolution_strategies: dict[str, ResolutionStrategy] = {}
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register built-in resolution strategies."""
        strategies = [
            ResolutionStrategy(
                name="confidence_comparison",
                description="Keep the belief with higher confidence, retract the other",
                recommended_for=["direct_opposition", "confidence_mismatch"],
            ),
            ResolutionStrategy(
                name="evidence_weighting",
                description="Weight beliefs by evidence count; keep the better-evidenced one",
                recommended_for=["evidence_conflict"],
            ),
            ResolutionStrategy(
                name="source_trust",
                description="Prefer beliefs from more reliable sources",
                recommended_for=["source_conflict"],
            ),
            ResolutionStrategy(
                name="temporal_recency",
                description="Prefer the more recently updated belief (newer information)",
                recommended_for=["temporal_drift"],
            ),
            ResolutionStrategy(
                name="domain_expert",
                description="Prefer domain-specific beliefs over general ones",
                recommended_for=["domain_conflict"],
            ),
            ResolutionStrategy(
                name="paraconsistent_accept",
                description="Accept both beliefs provisionally, flag for review",
                recommended_for=["unresolvable"],
            ),
        ]
        for s in strategies:
            self._resolution_strategies[s.name] = s

    # ── Contradiction detection ────────────────────────────────────────

    def detect_contradictions(self) -> list[Contradiction]:
        """Detect all contradictions in the belief system.

        Compares every pair of active beliefs in the same domain
        for opposing keywords that indicate contradiction.

        Returns:
            List of detected contradictions.
        """
        import time as _time
        contradictions: list[Contradiction] = []

        active_beliefs = [
            (bid, b) for bid, b in self.belief_system._beliefs.items()
            if b.status == BeliefStatus.ACTIVE
        ]

        # Group by domain for efficiency
        by_domain: dict[str, list[tuple[str, Belief]]] = defaultdict(list)
        for bid, b in active_beliefs:
            by_domain[b.domain].append((bid, b))

        for _domain, beliefs in by_domain.items():
            for i in range(len(beliefs)):
                for j in range(i + 1, len(beliefs)):
                    bid_a, b_a = beliefs[i]
                    bid_b, b_b = beliefs[j]

                    reason, severity = self._check_contradiction(b_a, b_b)
                    if reason:
                        contradictions.append(Contradiction(
                            belief_ids=[bid_a, bid_b],
                            reason=reason,
                            severity=severity,
                            detected_at=_time.time(),
                        ))

        self._contradictions.extend(contradictions)
        return contradictions

    def _check_contradiction(
        self, belief_a: Belief, belief_b: Belief
    ) -> tuple[str, float]:
        """Check if two beliefs contradict each other.

        Returns:
            Tuple of (reason_string_or_empty, severity_score).
        """
        words_a = set(belief_a.statement.lower().split())
        words_b = set(belief_b.statement.lower().split())
        overlap = words_a & words_b

        # Must share significant topic overlap to be contradictory
        if len(overlap) < 2:
            return "", 0.0

        # Check for opposing keywords
        for pos_set, neg_set in self.OPPOSITION_PAIRS:
            a_pos = words_a & pos_set
            a_neg = words_a & neg_set
            b_pos = words_b & pos_set
            b_neg = words_b & neg_set

            # Case 1: A says positive, B says negative (or vice versa)
            if (a_pos and b_neg) or (a_neg and b_pos):
                # Severity depends on confidence of both beliefs
                severity = (belief_a.confidence + belief_b.confidence) / 2.0
                return (
                    f"'{belief_a.statement[:60]}...' vs '{belief_b.statement[:60]}...' "
                    f"(opposing: {a_pos or a_neg} vs {b_pos or b_neg})",
                    severity,
                )

        return "", 0.0

    # ── Minimal inconsistent subset ─────────────────────────────────────

    def find_minimal_inconsistent_subsets(
        self, max_size: int = 5
    ) -> list[InconsistentSubset]:
        """Find minimal (or near-minimal) inconsistent subsets of beliefs.

        Uses a heuristic approach to find small sets of beliefs that
        together form an inconsistency.

        Args:
            max_size: Maximum subset size to search for.

        Returns:
            List of inconsistent subsets.
        """
        subsets: list[InconsistentSubset] = []
        contradictions = list(self._contradictions)

        # Start from detected contradictions (size 2)
        for contra in contradictions:
            if not any(set(contra.belief_ids) == set(s.belief_ids) for s in subsets):
                subsets.append(InconsistentSubset(
                    belief_ids=contra.belief_ids,
                    size=len(contra.belief_ids),
                    contradiction_type="pairwise",
                ))

        # For larger subsets, check transitive contradictions
        # If A contradicts B and B contradicts C, then {A, B, C} might be inconsistent
        for size in range(3, min(max_size + 1, 10)):
            # Build contradiction graph
            graph: dict[str, set[str]] = defaultdict(set)
            for contra in contradictions:
                ids = contra.belief_ids
                if len(ids) == 2:
                    graph[ids[0]].add(ids[1])
                    graph[ids[1]].add(ids[0])

            # Find connected components (approximation of inconsistent subgraphs)
            visited: set[str] = set()
            for node in graph:
                if node in visited:
                    continue
                component = self._bfs_component(graph, node)
                visited.update(component)
                if len(component) >= size:
                    subset = list(component)[:size]
                    subsets.append(InconsistentSubset(
                        belief_ids=subset,
                        size=size,
                        contradiction_type="transitive",
                    ))

        return subsets

    def _bfs_component(self, graph: dict[str, set[str]], start: str) -> set[str]:
        """BFS to find connected component in contradiction graph."""
        from collections import deque
        queue = deque([start])
        visited: set[str] = {start}
        while queue:
            node = queue.popleft()
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    # ── Resolution ─────────────────────────────────────────────────────

    def resolve_contradiction(
        self,
        contradiction: Contradiction,
        strategy_name: str = "confidence_comparison",
    ) -> dict[str, Any]:
        """Resolve a contradiction using the specified strategy.

        Args:
            contradiction: The contradiction to resolve.
            strategy_name: Which resolution strategy to use.

        Returns:
            Resolution report dict.
        """
        strategy = self._resolution_strategies.get(strategy_name)
        if strategy is None:
            return {"resolved": False, "error": f"Unknown strategy: {strategy_name}"}

        beliefs = []
        for bid in contradiction.belief_ids:
            belief = self.belief_system._beliefs.get(bid)
            if belief:
                beliefs.append((bid, belief))

        if len(beliefs) < 2:
            return {"resolved": False, "error": "Need at least 2 beliefs to resolve"}

        (bid_a, b_a), (bid_b, b_b) = beliefs[0], beliefs[1]

        if strategy_name == "confidence_comparison":
            if b_a.confidence >= b_b.confidence:
                b_b.status = BeliefStatus.RETRACTED
                kept, retracted = bid_a, bid_b
            else:
                b_a.status = BeliefStatus.RETRACTED
                kept, retracted = bid_b, bid_a

        elif strategy_name == "evidence_weighting":
            evidence_a = len(b_a.evidence)
            evidence_b = len(b_b.evidence)
            if evidence_a >= evidence_b:
                b_b.status = BeliefStatus.RETRACTED
                kept, retracted = bid_a, bid_b
            else:
                b_a.status = BeliefStatus.RETRACTED
                kept, retracted = bid_b, bid_a

        elif strategy_name == "source_trust":
            if b_a.source_reliability >= b_b.source_reliability:
                b_b.status = BeliefStatus.RETRACTED
                kept, retracted = bid_a, bid_b
            else:
                b_a.status = BeliefStatus.RETRACTED
                kept, retracted = bid_b, bid_a

        elif strategy_name == "temporal_recency":
            if b_a.last_updated >= b_b.last_updated:
                b_b.status = BeliefStatus.RETRACTED
                kept, retracted = bid_a, bid_b
            else:
                b_a.status = BeliefStatus.RETRACTED
                kept, retracted = bid_b, bid_a

        elif strategy_name == "domain_expert":
            # Prefer domain-specific to "general"
            if b_a.domain != "general" and b_b.domain == "general":
                b_b.status = BeliefStatus.RETRACTED
                kept, retracted = bid_a, bid_b
            elif b_b.domain != "general" and b_a.domain == "general":
                b_a.status = BeliefStatus.RETRACTED
                kept, retracted = bid_b, bid_a
            else:
                # Fall back to confidence
                if b_a.confidence >= b_b.confidence:
                    b_b.status = BeliefStatus.RETRACTED
                    kept, retracted = bid_a, bid_b
                else:
                    b_a.status = BeliefStatus.RETRACTED
                    kept, retracted = bid_b, bid_a

        elif strategy_name == "paraconsistent_accept":
            # Accept both but flag as disputed
            b_a.status = BeliefStatus.DISPUTED
            b_b.status = BeliefStatus.DISPUTED
            kept, retracted = bid_a, bid_b  # Both kept

        else:
            # Default: confidence
            if b_a.confidence >= b_b.confidence:
                b_b.status = BeliefStatus.RETRACTED
                kept, retracted = bid_a, bid_b
            else:
                b_a.status = BeliefStatus.RETRACTED
                kept, retracted = bid_b, bid_a

        contradiction.resolved = True
        logger.info("Contradiction resolved with '%s': kept=%s, retracted=%s",
                    strategy_name, kept[:8], retracted[:8])

        return {
            "resolved": True,
            "strategy": strategy_name,
            "kept": kept,
            "retracted": retracted,
        }

    def resolve_all(
        self, strategy_name: str = "confidence_comparison"
    ) -> dict[str, Any]:
        """Detect and resolve all contradictions.

        Args:
            strategy_name: Strategy to apply to all contradictions.

        Returns:
            Resolution summary.
        """
        contradictions = self.detect_contradictions()
        resolved = 0

        for contra in contradictions:
            result = self.resolve_contradiction(contra, strategy_name)
            if result.get("resolved"):
                resolved += 1

        return {
            "detected": len(contradictions),
            "resolved": resolved,
            "strategy": strategy_name,
        }

    # ── Paraconsistent reasoning support ───────────────────────────────

    def paraconsistent_query(
        self, domain: str
    ) -> dict[str, Any]:
        """Support paraconsistent reasoning: query a domain while
        accepting that contradictions may exist.

        In paraconsistent logic, contradictions do not imply everything.
        This returns both sides of detected contradictions for the domain.

        Args:
            domain: Domain to query.

        Returns:
            Dict with supportive and contradictory evidence.
        """
        domain_beliefs = self.belief_system.get_by_domain(domain)
        active = [b for b in domain_beliefs if b.status == BeliefStatus.ACTIVE]

        # Find positions on different topics
        topics: dict[str, dict[str, list[Belief]]] = defaultdict(
            lambda: {"supporting": [], "opposing": []}
        )

        for b in active:
            # Extract topic from statement (first few significant words)
            topic_words = [w for w in b.statement.lower().split() if len(w) > 3][:3]
            topic = " ".join(topic_words) if topic_words else "unknown"

            # Check which side of opposition pairs this belief falls on
            words = set(b.statement.lower().split())
            for pos_set, neg_set in self.OPPOSITION_PAIRS:
                if words & pos_set:
                    topics[topic]["supporting"].append(b)
                    break
                elif words & neg_set:
                    topics[topic]["opposing"].append(b)
                    break
            else:
                topics[topic]["supporting"].append(b)  # Default neutral

        # Filter to topics with disagreement
        disputed_topics = {
            topic: sides
            for topic, sides in topics.items()
            if sides["supporting"] and sides["opposing"]
        }

        return {
            "domain": domain,
            "active_beliefs": len(active),
            "disputed_topics": len(disputed_topics),
            "topics": {
                topic: {
                    "supporting_count": len(sides["supporting"]),
                    "opposing_count": len(sides["opposing"]),
                    "supporting_confidence": float(np.mean(
                        [b.confidence for b in sides["supporting"]]
                    )),
                    "opposing_confidence": float(np.mean(
                        [b.confidence for b in sides["opposing"]]
                    )) if sides["opposing"] else 0.0,
                }
                for topic, sides in disputed_topics.items()
            },
            "paraconsistent_note": (
                "Both supporting and opposing beliefs are preserved. "
                "Contradictions do not entail arbitrary conclusions."
            ),
        }

    # ── Statistics ─────────────────────────────────────────────────────

    @property
    def contradiction_count(self) -> int:
        """Number of detected contradictions."""
        return len(self._contradictions)

    @property
    def unresolved_count(self) -> int:
        """Number of unresolved contradictions."""
        return sum(1 for c in self._contradictions if not c.resolved)

    @property
    def summary(self) -> dict[str, Any]:
        """Get consistency manager summary."""
        return {
            "total_contradictions": self.contradiction_count,
            "unresolved": self.unresolved_count,
            "resolved": self.contradiction_count - self.unresolved_count,
            "strategies": list(self._resolution_strategies.keys()),
            "is_consistent": self.contradiction_count == 0,
        }
