"""
Cross-Verification Collusion Defense — Run 17 Lying-with-Truths mitigation.

Per Lying with Truths (Hu et al., ACL 2026 Oral): colluding agents can manipulate
a victim's beliefs using ONLY truthful evidence fragments posted on public channels.
74.4% attack success on proprietary models. No covert comms, backdoors, or fakes
needed — the Generative Montage attack exploits LLM overthinking to assemble truthful
atoms into a misleading whole.

Also addresses Conjunctive Prompt Attacks (Arif et al., ACL 2026 Main): a trigger
in user query + hidden template in compromised agent — individually harmless,
combined harmful when routing connects them. Existing safeguards fail because no
single component appears malicious.

Defense strategies:
1. **Source independence check** — verify claims against INDEPENDENT sources,
   not just the channel they appeared on
2. **Composition monitoring** — track message combinations across routing paths
3. **Truthful-but-misleading detection** — identify coordinated truthful posting
4. **Cognitive anchoring** — force agents to verify against original source,
   not group consensus (Mandela Effect mitigation, ICLR 2026)
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CollusionRisk(str, Enum):
    """Risk level for potential collusion patterns."""
    NONE = "none"           # No suspicious patterns
    LOW = "low"             # Minor coordination, likely coincidental
    MEDIUM = "medium"       # Concerning pattern, needs verification
    HIGH = "high"           # Likely coordinated manipulation
    CRITICAL = "critical"   # Active collusion attack detected


@dataclass
class MessageRecord:
    """A single message passing through the swarm channel."""
    message_id: str
    agent_id: str
    content: str
    channel: str
    timestamp: float = field(default_factory=time.time)
    content_hash: str = ""
    sources_cited: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                self.content.encode()
            ).hexdigest()[:16]


@dataclass
class CollusionCheck:
    """Result of a collusion analysis pass."""
    risk: CollusionRisk
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    affected_agent_ids: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class CrossVerifier:
    """Cross-verification engine for multi-agent communication channels.

    Monitors swarm channels for patterns indicative of coordinated manipulation:
    1. Multiple agents posting the same truthful-but-misleading claim
    2. Agent pairs consistently amplifying each other's claims
    3. Claims that cite the same source but draw different conclusions
    4. Rapid consensus formation without independent verification

    This is NOT a fact-checker — it detects coordination PATTERNS, not content
    truth. The insight from Lying-with-Truths is that every individual message
    IS truthful — the deception is in the coordinated assembly.
    """

    # Thresholds for detection
    COORDINATION_WINDOW: float = 30.0  # seconds — messages within this window are "simultaneous"
    AMPLIFICATION_THRESHOLD: int = 3   # same claim repeated N+ times → suspicious
    CONSENSUS_SPEED_THRESHOLD: float = 5.0  # seconds — consensus faster than this → suspicious
    MIN_CORRELATED_PAIRS: int = 2  # minimum agent pairs amplifying same claim

    def __init__(self) -> None:
        self._history: list[MessageRecord] = []
        self._agent_pair_counts: dict[tuple[str, str], int] = defaultdict(int)
        self._claim_frequency: dict[str, list[float]] = defaultdict(list)
        self._flagged_agents: set[str] = set()

    def record_message(self, msg: MessageRecord) -> CollusionCheck:
        """Record a message passing through the swarm and check for collusion.

        Returns a CollusionCheck with risk assessment and recommendations.
        """
        self._history.append(msg)
        self._claim_frequency[msg.content_hash].append(msg.timestamp)

        # Prune old history
        self._prune_history()

        # Run detection checks
        checks: list[tuple[CollusionRisk, str]] = []

        # Check 1: Coordinated amplification
        amp_risk, amp_reason = self._check_amplification(msg)
        if amp_risk != CollusionRisk.NONE:
            checks.append((amp_risk, amp_reason))

        # Check 2: Rapid consensus without verification
        cons_risk, cons_reason = self._check_rapid_consensus(msg)
        if cons_risk != CollusionRisk.NONE:
            checks.append((cons_risk, cons_reason))

        # Check 3: Correlated agent pair activity
        pair_risk, pair_reason = self._check_agent_pairs(msg)
        if pair_risk != CollusionRisk.NONE:
            checks.append((pair_risk, pair_reason))

        # Resolve to highest risk
        risk_order = {
            CollusionRisk.NONE: 0,
            CollusionRisk.LOW: 1,
            CollusionRisk.MEDIUM: 2,
            CollusionRisk.HIGH: 3,
            CollusionRisk.CRITICAL: 4,
        }
        if not checks:
            return CollusionCheck(risk=CollusionRisk.NONE)

        max_risk = max(checks, key=lambda c: risk_order[c[0]])
        return CollusionCheck(
            risk=max_risk[0],
            reason="; ".join(r for _, r in checks),
            evidence=[r for _, r in checks],
            affected_agent_ids=list(self._flagged_agents),
            recommendations=self._generate_recommendations(max_risk[0]),
        )

    def verify_source_independence(
        self,
        claim: str,
        cited_sources: Sequence[str],
    ) -> CollusionCheck:
        """Check whether a claim is supported by INDEPENDENT sources.

        Key insight from Lying-with-Truths: colluding agents can all cite the
        same source to give the appearance of multi-source confirmation. This
        check verifies that cited sources are genuinely independent.
        """
        unique_sources = set(cited_sources)
        if len(unique_sources) < 2:
            return CollusionCheck(
                risk=CollusionRisk.LOW,
                reason="Single-source claim — cannot verify independence",
                evidence=list(cited_sources),
                recommendations=["Cross-reference with independent source"],
            )

        # Check if all sources trace to the same origin
        source_fingerprints = [
            self._fingerprint_source(s) for s in unique_sources
        ]
        if len(set(source_fingerprints)) == 1:
            return CollusionCheck(
                risk=CollusionRisk.HIGH,
                reason="All cited sources share the same origin fingerprint",
                evidence=list(unique_sources),
                recommendations=[
                    "Require at least one source from a different domain/origin",
                    "Flag claim for adversarial review",
                ],
            )

        return CollusionCheck(risk=CollusionRisk.NONE)

    # -- Internal detection checks -----------------------------------------

    def _check_amplification(self, msg: MessageRecord) -> tuple[CollusionRisk, str]:
        """Detect coordinated amplification: same claim repeated by multiple agents."""
        recent = self._claim_frequency[msg.content_hash]
        window_hits = [t for t in recent if msg.timestamp - t <= self.COORDINATION_WINDOW]
        if len(window_hits) >= self.AMPLIFICATION_THRESHOLD:
            return (
                CollusionRisk.HIGH,
                f"Claim amplified {len(window_hits)}× within {self.COORDINATION_WINDOW}s "
                f"(threshold: {self.AMPLIFICATION_THRESHOLD})",
            )
        return CollusionRisk.NONE, ""

    def _check_rapid_consensus(self, msg: MessageRecord) -> tuple[CollusionRisk, str]:
        """Detect suspiciously fast consensus formation."""
        recent_msgs = [
            m for m in self._history[-20:]
            if msg.timestamp - m.timestamp <= self.CONSENSUS_SPEED_THRESHOLD
        ]
        if len(recent_msgs) >= 5:
            # Check if all share the same stance
            hashes = [m.content_hash for m in recent_msgs]
            dominant_hash = max(set(hashes), key=hashes.count)
            agreement_count = hashes.count(dominant_hash)
            if agreement_count >= 4:
                return (
                    CollusionRisk.MEDIUM,
                    f"Rapid consensus: {agreement_count}/{len(recent_msgs)} agents agreed "
                    f"within {self.CONSENSUS_SPEED_THRESHOLD}s",
                )
        return CollusionRisk.NONE, ""

    def _check_agent_pairs(self, msg: MessageRecord) -> tuple[CollusionRisk, str]:
        """Detect agent pairs that consistently co-post."""
        recent = [
            m for m in self._history[-50:]
            if msg.timestamp - m.timestamp <= self.COORDINATION_WINDOW * 2
        ]
        for other in recent:
            if other.agent_id == msg.agent_id:
                continue
            pair: tuple[str, str] = (msg.agent_id, other.agent_id) if msg.agent_id < other.agent_id else (other.agent_id, msg.agent_id)
            self._agent_pair_counts[pair] += 1

        # Check if any pair exceeds threshold
        for pair, count in self._agent_pair_counts.items():
            if count >= 5:  # same pair co-posting 5+ times
                self._flagged_agents.update(pair)
                return (
                    CollusionRisk.MEDIUM,
                    f"Coordinated agent pair: {pair[0]}↔{pair[1]} co-posted "
                    f"{count}× (threshold: 5)",
                )
        return CollusionRisk.NONE, ""

    def _prune_history(self, max_age: float = 300.0) -> None:
        """Remove records older than max_age seconds."""
        now = time.time()
        self._history = [m for m in self._history if now - m.timestamp <= max_age]
        # Also prune claim frequencies
        for h in list(self._claim_frequency):
            self._claim_frequency[h] = [
                t for t in self._claim_frequency[h] if now - t <= max_age
            ]
            if not self._claim_frequency[h]:
                del self._claim_frequency[h]

    @staticmethod
    def _fingerprint_source(source: str) -> str:
        """Create a domain-origin fingerprint for a source."""
        normalized = source.lower().strip()
        # Extract domain-like pattern
        import re
        domain_match = re.search(r'(?:https?://)?([^/\s]+)', normalized)
        if domain_match:
            return domain_match.group(1)
        return hashlib.sha256(normalized.encode()).hexdigest()[:8]

    @staticmethod
    def _generate_recommendations(risk: CollusionRisk) -> list[str]:
        if risk == CollusionRisk.NONE:
            return []
        if risk == CollusionRisk.LOW:
            return ["Monitor for escalation"]
        if risk == CollusionRisk.MEDIUM:
            return [
                "Cross-verify claims against independent sources",
                "Consider anonymizing the channel to disrupt coordination",
            ]
        if risk in (CollusionRisk.HIGH, CollusionRisk.CRITICAL):
            return [
                "IMMEDIATE: Isolate suspected colluding agents",
                "Require independent source verification for all claims",
                "Flag all outputs from affected channels for adversarial review",
                "Log coordination pattern for security audit",
            ]
        return []

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "messages_recorded": len(self._history),
            "flagged_agents": list(self._flagged_agents),
            "active_claims": len(self._claim_frequency),
            "agent_pairs_tracked": len(self._agent_pair_counts),
        }


class CompositionMonitor:
    """Monitor for conjunctive attacks across routing paths.

    Per Conjunctive Prompt Attacks (Arif et al., ACL 2026 Main): a trigger in
    user query + hidden template in compromised agent — individually harmless,
    combined harmful when routing connects them. No single component appears
    malicious → existing safeguards fail.

    This monitor tracks message routing paths and detects when two individually
    benign messages combine to produce a harmful result through composition.
    """

    def __init__(self) -> None:
        self._routing_graph: dict[str, list[str]] = defaultdict(list)
        self._message_registry: dict[str, MessageRecord] = {}

    def record_routing(
        self,
        source_agent: str,
        target_agent: str,
        message: MessageRecord,
    ) -> None:
        """Record a message routing event."""
        self._routing_graph[source_agent].append(target_agent)
        self._message_registry[message.message_id] = message

    def check_composition(
        self,
        trigger_agent: str,
        template_agent: str,
    ) -> CollusionCheck:
        """Check if routing between two agents creates a dangerous composition.

        A conjunctive attack requires: (1) a trigger in the user's query, (2) a
        hidden template in a compromised agent, and (3) routing that connects them.
        """
        # Check if these agents are on a connected routing path
        if trigger_agent not in self._routing_graph:
            return CollusionCheck(risk=CollusionRisk.NONE)

        reachable = self._bfs_reachable(trigger_agent)
        if template_agent in reachable:
            return CollusionCheck(
                risk=CollusionRisk.MEDIUM,
                reason=(
                    f"Routing path exists from trigger agent '{trigger_agent}' "
                    f"to template agent '{template_agent}'"
                ),
                affected_agent_ids=[trigger_agent, template_agent],
                recommendations=[
                    "Verify neither agent carries hidden templates",
                    "Consider routing isolation between these agents",
                ],
            )
        return CollusionCheck(risk=CollusionRisk.NONE)

    def _bfs_reachable(self, start: str, max_depth: int = 5) -> set[str]:
        """BFS to find all agents reachable from start within max_depth."""
        visited: set[str] = set()
        frontier = [start]
        for _ in range(max_depth):
            if not frontier:
                break
            current = frontier.pop(0)
            if current in visited:
                continue
            visited.add(current)
            frontier.extend(self._routing_graph.get(current, []))
        return visited

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "agents_in_graph": len(self._routing_graph),
            "edges": sum(len(v) for v in self._routing_graph.values()),
            "registered_messages": len(self._message_registry),
        }
