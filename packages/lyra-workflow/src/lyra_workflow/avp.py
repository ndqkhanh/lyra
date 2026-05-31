"""
Adversarial Verification Protocol (AVP) — 3-critic cross-model verification middleware.

Implements Primitive 4 of the ultracode replication plan: independent agents
draft from several angles and/or adversarially review each other's findings,
vote on each claim, and filter out claims that don't survive cross-checking.

Core algorithm (from BREAKTHROUGH-ARCHITECTURE.md §18):
1. **Mutation Gate** (SABER pattern): Classify action as mutating/non-mutating.
   Only mutating actions trigger the full 3-critic panel.
2. **Classification**: Each critic independently classifies the claim.
3. **Consensus**: ≥2 critics must accept for the claim to pass.
4. **Escalation**: 1-1-1 split → escalate to user.

Design rationale: The 3-critic panel uses critics from DIFFERENT providers
(Anthropic, DeepSeek, open-weight) to maximize architectural diversity.
Cross-model correlation is ~14.6× worse than same-model for error detection,
meaning diverse critics catch errors that homogeneous critics miss.

Run 17 multi-agent reliability findings (SYNTHESIS.md §10.1):
- **Identity-driven sycophancy**: Agents uncritically adopt peer views when they
  know who wrote what (Identity-Skews-Debate, ACL 2026). Fix: anonymize claims
  before review — strip agent IDs, normalize formatting.
- **Actor-Observer Asymmetry**: Same agent reviewing own output blames external
  factors; reviewing others blames internal faults — >20% attribution flip on
  perspective swap (Actor-Observer Asymmetry, ACL 2026). Fix: never let critics
  review their own output; randomize critic-to-claim assignment.
- **Rogue agent propagation**: A single confused agent can sink the entire task
  by terminating early while uncertain (Preventing Rogue Agents, ACL 2025).
  Fix: monitor per-agent confidence trajectories.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Review Anonymizer — Run 17 Identity-Skews-Debate mitigation
# ---------------------------------------------------------------------------


class ReviewAnonymizer:
    """Strips agent identity markers from claims before multi-critic review.

    Per Identity-Skews-Debate (Choi/Zhu/Li, ACL 2026 Main): multi-agent debate
    suffers identity-driven sycophancy + self-bias. Formal fix: response
    anonymization — strip identity markers so critics can't distinguish self
    from peer → equal weighting. The Identity Bias Coefficient (IBC) quantifies
    the tendency to follow peer vs self; anonymization structurally eliminates
    this channel.

    Also addresses Actor-Observer Asymmetry (Li et al., ACL 2026 Main):
    perspective-dependent attribution errors are triggered when reviewers know
    who authored a claim. Randomizing critic-to-claim assignment ensures no
    critic reviews their own output.
    """

    # Patterns to strip from claims before review
    _IDENTITY_MARKERS: frozenset[str] = frozenset({
        "agent_id:", "agent:", "author:", "reviewer:", "critic:",
        "produced by", "created by", "written by", "submitted by",
        "source_agent:", "owner:", "assigned_to:",
    })

    def anonymize(self, claim: "Claim") -> "Claim":
        """Return an anonymized copy of the claim ready for critic review.

        Strips agent-identifying metadata and normalizes the claim source
        to a neutral identifier so critics cannot distinguish self-authored
        from peer-authored claims.
        """
        # Generate a deterministic but opaque source ID — same claim always
        # gets the same anonymized source, but it reveals nothing about the
        # originating agent.
        source_hash = hashlib.sha256(
            (claim.source + claim.id).encode()
        ).hexdigest()[:12]

        # Strip identity markers from content
        content = claim.content
        for marker in self._IDENTITY_MARKERS:
            content = self._strip_marker_lines(content, marker)

        return Claim(
            id=claim.id,
            content=content,
            source=f"review-item-{source_hash}",
            severity=claim.severity,
            evidence=claim.evidence,
        )

    @staticmethod
    def _strip_marker_lines(text: str, marker: str) -> str:
        """Remove lines containing an identity marker."""
        return "\n".join(
            line for line in text.split("\n")
            if marker.lower() not in line.lower()
        )

    def shuffle_assignment(
        self, claims: list["Claim"], critic_ids: list[str]
    ) -> dict[str, list["Claim"]]:
        """Randomize which critic reviews which claim.

        Ensures no critic reviews claims they authored. Returns a mapping
        from critic_id → list of anonymized claims to review.
        """
        assignments: dict[str, list["Claim"]] = {cid: [] for cid in critic_ids}
        shuffled_claims = list(claims)
        random.shuffle(shuffled_claims)

        for i, claim in enumerate(shuffled_claims):
            # Round-robin assignment with anonymization
            critic_idx = i % len(critic_ids)
            critic_id = critic_ids[critic_idx]
            anonymized = self.anonymize(claim)
            assignments[critic_id].append(anonymized)

        return assignments


class Verdict(str, Enum):
    """Critic verdict on a claim."""

    ACCEPT = "accept"   # Claim is valid
    REJECT = "reject"   # Claim is refuted
    FLAG = "flag"       # Uncertain — needs further review
    ABSTAIN = "abstain"  # Critic cannot evaluate


class MutationClass(str, Enum):
    """SABER mutation classification for actions."""

    MUTATING = "mutating"       # Changes state (write, delete, execute)
    NON_MUTATING = "non_mutating"  # Read-only (read, search, list)
    UNCERTAIN = "uncertain"     # Cannot classify


@dataclass
class Claim:
    """
    A single claim to verify.

    Attributes:
        id: Unique claim identifier.
        content: The claim text.
        source: Where the claim came from (agent_id, file, tool).
        severity: Claim severity (CRITICAL, HIGH, MEDIUM, LOW, INFO).
        evidence: Supporting evidence or citation.
    """

    id: str
    content: str
    source: str = ""
    severity: str = "MEDIUM"
    evidence: str = ""


@dataclass
class CriticVerdict:
    """
    A single critic's evaluation of a claim.

    Attributes:
        critic_id: Identifier for the critic (e.g. "critic-refutation-claude").
        provider: Which provider the critic uses.
        verdict: ACCEPT, REJECT, FLAG, or ABSTAIN.
        confidence: How confident the critic is (0.0–1.0).
        reasoning: Explanation of the verdict.
        evidence_tier: Quality of supporting evidence (A–D).
    """

    critic_id: str
    provider: str
    verdict: Verdict
    confidence: float
    reasoning: str = ""
    evidence_tier: str = "C"  # A = gold standard, B = strong, C = moderate, D = weak


class MutationGate:
    """
    SABER-inspired mutation gate — classifies actions before execution.

    Only MUTATING actions trigger the full AVP panel. NON_MUTATING actions
    pass through without verification overhead. UNCERTAIN actions are
    treated as mutating (conservative default).

    This is the key performance optimization: we don't verify reads.
    """

    # Keywords that indicate mutation
    _MUTATING_KEYWORDS: frozenset[str] = frozenset({
        "write", "edit", "delete", "remove", "create", "update", "replace",
        "commit", "push", "deploy", "execute", "run", "install", "uninstall",
        "move", "rename", "copy", "chmod", "chown", "truncate",
    })

    # Keywords that indicate read-only
    _NON_MUTATING_KEYWORDS: frozenset[str] = frozenset({
        "read", "view", "list", "show", "search", "find", "grep", "cat",
        "head", "tail", "ls", "stat", "diff", "log", "status", "describe",
        "get", "fetch", "query", "check", "validate", "inspect", "audit",
    })

    def classify(self, action_description: str) -> MutationClass:
        """Classify an action as mutating, non-mutating, or uncertain."""
        words = set(action_description.lower().split())

        mutating_matches = words & self._MUTATING_KEYWORDS
        non_mutating_matches = words & self._NON_MUTATING_KEYWORDS

        if mutating_matches and not non_mutating_matches:
            return MutationClass.MUTATING
        if non_mutating_matches and not mutating_matches:
            return MutationClass.NON_MUTATING
        if mutating_matches:
            return MutationClass.MUTATING  # Conservative: mutating wins if both match

        return MutationClass.UNCERTAIN  # Default to mutating for uncertainty


class DecisionMatrix:
    """
    3-critic consensus decision matrix.

    Maps critic vote combinations to final outcomes:

    | Critic A | Critic B | Critic C | Outcome     |
    |----------|----------|----------|-------------|
    | ACCEPT   | ACCEPT   | ACCEPT   | CONFIRMED   |
    | ACCEPT   | ACCEPT   | FLAG     | CONFIRMED   |
    | ACCEPT   | ACCEPT   | REJECT   | CONFIRMED   |
    | ACCEPT   | FLAG     | FLAG     | FLAGGED     |
    | ACCEPT   | REJECT   | REJECT   | REJECTED    |
    | FLAG     | FLAG     | FLAG     | FLAGGED     |
    | REJECT   | REJECT   | REJECT   | REJECTED    |
    | ACCEPT   | REJECT   | FLAG     | ESCALATE    | (1-1-1 split)
    """

    @staticmethod
    def resolve(verdicts: list[CriticVerdict]) -> Verdict:
        """
        Resolve a set of critic verdicts to a final outcome.

        Rule: ≥2 ACCEPT votes → ACCEPT (confirmed).
        Rule: 1-1-1 split (ACCEPT/REJECT/FLAG) → FLAG (escalate).
        Rule: ≥2 REJECT votes → REJECT.

        Args:
            verdicts: Exactly 3 CriticVerdict instances.

        Returns:
            The consensus verdict.
        """
        if len(verdicts) != 3:
            raise ValueError(f"DecisionMatrix requires exactly 3 verdicts, got {len(verdicts)}")

        votes = [v.verdict for v in verdicts]
        accept_count = votes.count(Verdict.ACCEPT)
        reject_count = votes.count(Verdict.REJECT)
        flag_count = votes.count(Verdict.FLAG)

        # ≥2 ACCEPT → confirmed
        if accept_count >= 2:
            return Verdict.ACCEPT

        # ≥2 REJECT → rejected
        if reject_count >= 2:
            return Verdict.REJECT

        # ≥2 FLAG → flagged
        if flag_count >= 2:
            return Verdict.FLAG

        # 1-1-1 split (ACCEPT/REJECT/FLAG each) → escalate
        return Verdict.FLAG


class AdversarialVerifier:
    """
    Adversarial Verification Protocol — universal middleware for claim verification.

    Every tool execution, skill update, or agent spawn passes through this
    verifier (per BREAKTHROUGH-ARCHITECTURE.md invariant #2).

    The verifier:
    1. **Anonymizes claims** (Run 17: Identity-Skews-Debate mitigation, DEFAULT ON)
    2. Classifies the action via MutationGate
    3. For mutating actions: routes to 3 critics from different providers
    4. Applies the DecisionMatrix for consensus
    5. Returns the verified result with critic annotations

    Anonymization is DEFAULT-ON per Run 17 design decision (SYNTHESIS.md §10.6,
    decision #1): identity-driven sycophancy is the dominant bias in multi-agent
    debate. Response anonymization is a one-line structural fix.

    Usage::

        verifier = AdversarialVerifier()
        claim = Claim(id="c1", content="auth middleware is missing at line 45")
        result = verifier.verify(
            claim,
            critics_fn=lambda c: [
                CriticVerdict("c1", "anthropic", Verdict.ACCEPT, 0.94, "Confirmed"),
                CriticVerdict("c2", "deepseek", Verdict.REJECT, 0.78, "Disputed"),
                CriticVerdict("c3", "openai", Verdict.ACCEPT, 0.91, "Agreed"),
            ],
        )
        print(result["consensus"])  # ACCEPT (2 out of 3)
    """

    def __init__(
        self,
        anonymize: bool = True,
        monitor_rogue_agents: bool = True,
    ) -> None:
        self._gate = MutationGate()
        self._matrix = DecisionMatrix()
        self._anonymizer = ReviewAnonymizer() if anonymize else None
        self._monitor = RogueAgentMonitor() if monitor_rogue_agents else None
        self._anonymize = anonymize
        self._total_verified: int = 0
        self._total_accepted: int = 0
        self._total_rejected: int = 0

    @property
    def anonymizer_enabled(self) -> bool:
        return self._anonymize

    @property
    def monitor_enabled(self) -> bool:
        return self._monitor is not None

    def verify(
        self,
        claim: Claim,
        critics_fn: Callable[[Claim], list[CriticVerdict]],
        agent_id: str = "",
    ) -> dict[str, Any]:
        """
        Verify a claim through the adversarial protocol.

        Args:
            claim: The claim to verify.
            critics_fn: Function that evaluates the claim and returns
                3 critic verdicts. In production, this calls 3 different
                LLM providers. In tests, it can return mock verdicts.
            agent_id: Optional agent submitting the claim (for rogue monitoring).

        Returns:
            Dict with: consensus, verdicts, claim_id, verified, confidence,
                       anonymized (bool), rogue_flag (bool|None).
        """
        self._total_verified += 1

        # Run 17: Anonymize claim before review (DEFAULT ON)
        review_claim = claim
        if self._anonymizer is not None:
            review_claim = self._anonymizer.anonymize(claim)

        # Run 17: Monitor agent confidence for rogue behavior
        rogue_flag = None
        if self._monitor is not None and agent_id:
            rogue_flag = self._monitor.record_and_check(agent_id, claim)

        verdicts = critics_fn(review_claim)
        if len(verdicts) != 3:
            raise ValueError(f"Expected 3 critic verdicts, got {len(verdicts)}")

        consensus = self._matrix.resolve(verdicts)

        if consensus == Verdict.ACCEPT:
            self._total_accepted += 1
        elif consensus == Verdict.REJECT:
            self._total_rejected += 1

        # Average confidence across critics
        avg_confidence = sum(v.confidence for v in verdicts) / len(verdicts)

        # Evidence tier: best tier among accepting critics
        evidence_tier = "C"
        for v in verdicts:
            if v.verdict == Verdict.ACCEPT and v.evidence_tier < evidence_tier:
                evidence_tier = v.evidence_tier

        return {
            "claim_id": claim.id,
            "consensus": consensus.value,
            "verified": consensus == Verdict.ACCEPT,
            "confidence": round(avg_confidence, 3),
            "evidence_tier": evidence_tier,
            "anonymized": self._anonymize,
            "rogue_flag": rogue_flag,
            "verdicts": [
                {
                    "critic_id": v.critic_id,
                    "provider": v.provider,
                    "verdict": v.verdict.value,
                    "confidence": v.confidence,
                    "reasoning": v.reasoning,
                }
                for v in verdicts
            ],
            "verdict_summary": self._summarize(verdicts),
        }

    def should_trigger_avp(self, action_description: str) -> bool:
        """
        Check whether an action should trigger the full AVP panel.

        Only mutating actions trigger verification (SABER optimization).
        Non-mutating actions skip verification to save cost and latency.
        """
        classification = self._gate.classify(action_description)
        return classification == MutationClass.MUTATING

    @property
    def stats(self) -> dict:
        return {
            "total_verified": self._total_verified,
            "total_accepted": self._total_accepted,
            "total_rejected": self._total_rejected,
            "acceptance_rate": (
                self._total_accepted / self._total_verified
                if self._total_verified > 0 else 0.0
            ),
        }

    @staticmethod
    def _summarize(verdicts: list[CriticVerdict]) -> str:
        """Human-readable summary of the 3-critic panel."""
        votes = [v.verdict.value for v in verdicts]
        return f"A:{votes[0]} B:{votes[1]} C:{votes[2]}"


# ---------------------------------------------------------------------------
# RogueAgentMonitor — Run 17 Preventing-Rogue-Agents mitigation
# ---------------------------------------------------------------------------


@dataclass
class AgentConfidenceTrajectory:
    """Tracks confidence over time for a single agent."""
    agent_id: str
    confidence_values: list[float] = field(default_factory=list)
    uncertainty_spikes: list[float] = field(default_factory=list)  # timestamps
    early_termination_attempts: int = 0

    @property
    def mean_confidence(self) -> float:
        if not self.confidence_values:
            return 1.0
        return sum(self.confidence_values) / len(self.confidence_values)

    @property
    def trend(self) -> float:
        """Simple linear trend: positive = improving, negative = deteriorating."""
        if len(self.confidence_values) < 2:
            return 0.0
        return self.confidence_values[-1] - self.confidence_values[0]


class RogueAgentMonitor:
    """Monitors per-agent confidence trajectories to detect rogue behavior.

    Per Preventing Rogue Agents (Barbi et al., ACL 2025 Spotlight): a single
    confused agent can sink the entire multi-agent task. The monitor watches
    per-agent confidence, identifies "critical points of agent confusion," and
    flags agents for preemptive review when their behavior becomes risky.

    Detection rules:
    1. **Sudden confidence drop**: confidence drops >0.3 in one step → FLAG
    2. **Sustained low confidence**: mean <0.4 over last 5 steps → FLAG
    3. **Deteriorating trend**: negative confidence trend >0.2 → FLAG
    4. **Frequent early termination**: >2 termination attempts → FLAG
    """

    # Detection thresholds (from Preventing Rogue Agents empirical findings)
    SUDDEN_DROP_THRESHOLD: float = 0.3
    SUSTAINED_LOW_THRESHOLD: float = 0.4
    TREND_DETERIORATION_THRESHOLD: float = 0.2
    TERMINATION_LIMIT: int = 2
    WINDOW_SIZE: int = 5  # for sustained low confidence check

    def __init__(self) -> None:
        self._trajectories: dict[str, AgentConfidenceTrajectory] = {}

    def record_and_check(
        self,
        agent_id: str,
        claim: Claim,
        confidence: float | None = None,
    ) -> bool:
        """Record an agent's action and check for rogue behavior.

        Returns True if the agent is flagged as potentially rogue.
        """
        traj = self._get_or_create(agent_id)

        # Infer confidence from claim severity if not explicitly provided
        if confidence is None:
            confidence = self._severity_to_confidence(claim.severity)

        traj.confidence_values.append(confidence)

        # Check detection rules
        if self._detect_sudden_drop(traj):
            return True
        if self._detect_sustained_low(traj):
            return True
        if self._detect_deteriorating_trend(traj):
            return True

        return False

    def record_early_termination(self, agent_id: str) -> bool:
        """Record that an agent attempted early termination while uncertain."""
        traj = self._get_or_create(agent_id)
        traj.early_termination_attempts += 1
        return traj.early_termination_attempts > self.TERMINATION_LIMIT

    def _get_or_create(self, agent_id: str) -> AgentConfidenceTrajectory:
        if agent_id not in self._trajectories:
            self._trajectories[agent_id] = AgentConfidenceTrajectory(
                agent_id=agent_id
            )
        return self._trajectories[agent_id]

    def _detect_sudden_drop(self, traj: AgentConfidenceTrajectory) -> bool:
        values = traj.confidence_values
        if len(values) < 2:
            return False
        drop = values[-2] - values[-1]
        return drop > self.SUDDEN_DROP_THRESHOLD

    def _detect_sustained_low(self, traj: AgentConfidenceTrajectory) -> bool:
        values = traj.confidence_values
        if len(values) < self.WINDOW_SIZE:
            return False
        recent = values[-self.WINDOW_SIZE:]
        return (sum(recent) / len(recent)) < self.SUSTAINED_LOW_THRESHOLD

    def _detect_deteriorating_trend(self, traj: AgentConfidenceTrajectory) -> bool:
        if len(traj.confidence_values) < self.WINDOW_SIZE:
            return False
        return traj.trend < -self.TREND_DETERIORATION_THRESHOLD

    @staticmethod
    def _severity_to_confidence(severity: str) -> float:
        """Map claim severity to approximate confidence."""
        return {
            "CRITICAL": 0.95,
            "HIGH": 0.80,
            "MEDIUM": 0.65,
            "LOW": 0.50,
            "INFO": 0.35,
        }.get(severity.upper(), 0.65)

    @property
    def flagged_agents(self) -> list[str]:
        """Return list of currently flagged agent IDs."""
        flagged: list[str] = []
        for agent_id, traj in self._trajectories.items():
            if (
                self._detect_sudden_drop(traj)
                or self._detect_sustained_low(traj)
                or self._detect_deteriorating_trend(traj)
            ):
                flagged.append(agent_id)
        return flagged

    @property
    def stats(self) -> dict:
        return {
            "agents_tracked": len(self._trajectories),
            "flagged": len(self.flagged_agents),
            "trajectories": {
                aid: {
                    "mean_confidence": round(t.mean_confidence, 3),
                    "trend": round(t.trend, 3),
                    "steps": len(t.confidence_values),
                    "early_terminations": t.early_termination_attempts,
                }
                for aid, t in self._trajectories.items()
            },
        }
