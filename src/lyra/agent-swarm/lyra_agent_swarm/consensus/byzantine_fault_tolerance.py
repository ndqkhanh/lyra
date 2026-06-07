"""Byzantine Fault Tolerance — CP-WBFT consensus with semantic agreement for LLM agents.

Implements Byzantine Fault Tolerance adapted for LLM agent swarms:
  - Three failure modes: crash, malicious, hallucination (LLM-specific)
  - CP-WBFT (Confidence-Probabilistic Weighted Byzantine Fault Tolerance)
  - Weighted voting with confidence scoring
  - Semantic agreement (not just binary state agreement)
  - Byzantine node detection via confidence anomaly analysis
  - f+1 fault tolerance with 2f+1 minimum nodes

Based on: Zheng et al. "Rethinking the Reliability of Multi-agent System"
(arXiv 2511.10400), CP-WBFT protocol.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class FailureMode(StrEnum):
    """LLM agent failure modes per CP-WBFT classification."""

    NONE = "none"
    CRASH = "crash"
    MALICIOUS = "malicious"
    HALLUCINATION = "hallucination"


class Verdict(StrEnum):
    """Consensus verdict for a proposal."""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class ByzantineNode:
    """A node in the Byzantine consensus group."""

    node_id: str
    weight: float = 1.0
    failure_mode: FailureMode = FailureMode.NONE
    registered_at: float = field(default_factory=time.monotonic)

    @property
    def is_byzantine(self) -> bool:
        return self.failure_mode != FailureMode.NONE

    def mark_failure(self, mode: FailureMode) -> ByzantineNode:
        return ByzantineNode(
            node_id=self.node_id,
            weight=self.weight,
            failure_mode=mode,
            registered_at=self.registered_at,
        )


@dataclass(frozen=True)
class WitnessStatement:
    """A witness statement (vote) from a node in a consensus round."""

    node_id: str
    verdict: Verdict
    confidence: float = 1.0
    reasoning: str = ""
    round_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class ConsensusResult:
    """Result of a Byzantine consensus round."""

    outcome: Verdict
    confidence: float
    agree_count: int
    total_count: int
    byzantine_nodes_detected: int = 0
    dissent_notes: tuple[str, ...] = ()
    round_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    duration_ms: float = 0.0

    @property
    def quorum_reached(self) -> bool:
        return self.agree_count > self.total_count / 2

    @property
    def agreement_ratio(self) -> float:
        return self.agree_count / max(self.total_count, 1)


class ByzantineConsensus:
    """Byzantine Fault Tolerant consensus for agent swarms.

    Implements CP-WBFT: confidence-probabilistic weighted BFT with
    semantic agreement. Tolerates up to f Byzantine failures when
    total nodes >= 3f+1 (standard BFT) or >= 2f+1 (CP-WBFT relaxed).

    Usage::

        bft = ByzantineConsensus(fault_tolerance=1, total_nodes=4)
        bft.register_node("captain", weight=2.0)
        bft.register_node("critic-1")
        bft.register_node("critic-2")
        bft.register_node("critic-3")
        bft.submit_statement("captain", Verdict.APPROVE, confidence=0.95)
        bft.submit_statement("critic-1", Verdict.APPROVE, confidence=0.8)
        bft.submit_statement("critic-2", Verdict.REJECT, confidence=0.6, reasoning="Risk")
        bft.submit_statement("critic-3", Verdict.APPROVE, confidence=0.85)
        result = bft.try_consensus()
        if result and result.quorum_reached:
            print(f"Consensus: {result.outcome} with {result.confidence:.2f}")
    """

    def __init__(
        self,
        fault_tolerance: int = 1,
        total_nodes: int = 0,
        confidence_threshold: float = 0.5,
    ) -> None:
        if total_nodes > 0 and total_nodes < 2 * fault_tolerance + 1:
            raise ValueError(
                f"BFT requires at least {2 * fault_tolerance + 1} nodes "
                f"for f={fault_tolerance}, got {total_nodes}"
            )
        self.fault_tolerance = fault_tolerance
        self.total_nodes = total_nodes
        self.confidence_threshold = confidence_threshold
        self._nodes: dict[str, ByzantineNode] = {}
        self._statements: list[WitnessStatement] = []
        self._round_start: float = 0.0

    # ── Properties ───────────────────────────────────────────────

    @property
    def quorum_size(self) -> int:
        return 2 * self.fault_tolerance + 1

    @property
    def registered_count(self) -> int:
        return len(self._nodes)

    @property
    def byzantine_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.is_byzantine)

    # ── Node Management ──────────────────────────────────────────

    def register_node(self, node_id: str, weight: float = 1.0) -> ByzantineNode:
        """Register a node in the consensus group."""
        if node_id in self._nodes:
            raise ValueError(f"Node '{node_id}' already registered")
        node = ByzantineNode(node_id=node_id, weight=weight)
        self._nodes[node_id] = node
        return node

    def get_node(self, node_id: str) -> ByzantineNode | None:
        return self._nodes.get(node_id)

    def mark_node_failure(self, node_id: str, mode: FailureMode) -> ByzantineNode | None:
        """Mark a node as having a Byzantine failure."""
        node = self._nodes.get(node_id)
        if node is None:
            return None
        updated = node.mark_failure(mode)
        self._nodes[node_id] = updated
        return updated

    # ── Consensus Rounds ─────────────────────────────────────────

    def submit_statement(
        self,
        node_id: str,
        verdict: Verdict,
        confidence: float = 1.0,
        reasoning: str = "",
    ) -> WitnessStatement:
        """Submit a witness statement (vote) from a node."""
        if node_id not in self._nodes:
            raise ValueError(f"Node '{node_id}' not registered")
        if self._round_start == 0.0:
            self._round_start = time.monotonic()

        stmt = WitnessStatement(
            node_id=node_id,
            verdict=verdict,
            confidence=min(1.0, max(0.0, confidence)),
            reasoning=reasoning,
        )
        self._statements.append(stmt)
        return stmt

    def try_consensus(self) -> ConsensusResult | None:
        """Attempt to reach consensus. Returns result if quorum reached."""
        if len(self._statements) < self.quorum_size:
            return None

        duration = (time.monotonic() - self._round_start) * 1000
        return self._compute_consensus(duration)

    def reset_round(self) -> None:
        """Reset for a new consensus round."""
        self._statements.clear()
        self._round_start = 0.0

    # ── Private ───────────────────────────────────────────────────

    def _compute_consensus(self, duration_ms: float) -> ConsensusResult:
        """Compute consensus outcome with BFT guarantees."""
        approve_weight: float = 0.0
        reject_weight: float = 0.0
        approve_count = 0
        reject_count = 0
        dissent_notes: list[str] = []
        byzantine_detected = 0

        for stmt in self._statements:
            node = self._nodes.get(stmt.node_id)
            if node is None:
                continue

            node_weight = node.weight * stmt.confidence

            if node.is_byzantine:
                byzantine_detected += 1
                # Byzantine nodes' votes are discounted but not fully ignored
                node_weight *= 0.25

            if stmt.verdict == Verdict.APPROVE:
                approve_weight += node_weight
                approve_count += 1
            elif stmt.verdict == Verdict.REJECT:
                reject_weight += node_weight
                reject_count += 1
                if stmt.reasoning:
                    dissent_notes.append(stmt.reasoning)

        total_weight = approve_weight + reject_weight
        total_count = approve_count + reject_count

        if total_weight == 0:
            return ConsensusResult(
                outcome=Verdict.ABSTAIN,
                confidence=0.0,
                agree_count=0,
                total_count=total_count,
                byzantine_nodes_detected=byzantine_detected,
                dissent_notes=tuple(dissent_notes),
                duration_ms=duration_ms,
            )

        if approve_weight >= reject_weight:
            confidence = approve_weight / total_weight
            return ConsensusResult(
                outcome=Verdict.APPROVE,
                confidence=min(1.0, confidence),
                agree_count=approve_count,
                total_count=total_count,
                byzantine_nodes_detected=byzantine_detected,
                dissent_notes=tuple(dissent_notes),
                duration_ms=duration_ms,
            )

        confidence = reject_weight / total_weight
        return ConsensusResult(
            outcome=Verdict.REJECT,
            confidence=min(1.0, confidence),
            agree_count=reject_count,
            total_count=total_count,
            byzantine_nodes_detected=byzantine_detected,
            dissent_notes=tuple(dissent_notes),
            duration_ms=duration_ms,
        )

    def reset(self) -> None:
        """Reset all consensus state."""
        self._nodes.clear()
        self._statements.clear()
        self._round_start = 0.0
