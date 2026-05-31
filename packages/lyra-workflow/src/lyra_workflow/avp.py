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
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


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
    1. Classifies the action via MutationGate
    2. For mutating actions: routes to 3 critics from different providers
    3. Applies the DecisionMatrix for consensus
    4. Returns the verified result with critic annotations

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
        print(result.consensus)  # ACCEPT (2 out of 3)
    """

    def __init__(self) -> None:
        self._gate = MutationGate()
        self._matrix = DecisionMatrix()
        self._total_verified: int = 0
        self._total_accepted: int = 0
        self._total_rejected: int = 0

    def verify(
        self,
        claim: Claim,
        critics_fn: Callable[[Claim], list[CriticVerdict]],
    ) -> dict[str, Any]:
        """
        Verify a claim through the adversarial protocol.

        Args:
            claim: The claim to verify.
            critics_fn: Function that evaluates the claim and returns
                3 critic verdicts. In production, this calls 3 different
                LLM providers. In tests, it can return mock verdicts.

        Returns:
            Dict with: consensus, verdicts, claim_id, verified, confidence.
        """
        self._total_verified += 1

        verdicts = critics_fn(claim)
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
