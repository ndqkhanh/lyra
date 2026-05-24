"""Dual-use intent classifier gate.

Per [docs/219-helix-bio-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/219-helix-bio-multi-hop-collaborative-apply-plan.md) §3.2 —
Helix-Bio Tier-0 non-negotiable. Classifies queries on a dual-use risk axis
(pathogen-of-concern synthesis, controlled-substance analog design,
gain-of-function-adjacent assays). High-risk → HITL approval; medium-risk →
hard rate limit + audit log; low-risk → flow normally.

Layered design:
    - :class:`KeywordRiskClassifier` — zero-dep cold-start fallback using
      regex sentinel patterns. Fast, deterministic, auditable.
    - :class:`DualUseClassifier` Protocol — production wires an LM-backed
      classifier through this slot.
    - :class:`DualUseGate` — composes a classifier with action policy.

Cf. [docs/49-agents-of-chaos-red-teaming.md](../../../../../../research/harness-engineering/docs/49-agents-of-chaos-red-teaming.md),
[docs/122-explainability-compliance.md](../../../../../../research/harness-engineering/docs/122-explainability-compliance.md).

The keyword classifier is *intentionally minimal*. Production deployments
should replace it with an LM-backed classifier and a domain-curated taxonomy.
The rule-based fallback's job is to fail-closed-by-default + provide an
auditable baseline, not to enumerate every dual-use risk.
"""
from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Optional, Protocol


class RiskLevel(str, enum.Enum):
    """Coarse three-way risk verdict."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GateAction(str, enum.Enum):
    """What the gate does with a query at each risk level."""

    ALLOW = "allow"
    RATE_LIMIT = "rate_limit"
    HITL_REVIEW = "hitl_review"
    BLOCK = "block"


@dataclass(frozen=True)
class DualUseVerdict:
    """One classifier verdict on a query."""

    query: str
    risk_level: RiskLevel
    matched_categories: tuple[str, ...]
    confidence: float
    reason: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


class DualUseClassifier(Protocol):
    """Protocol: map a query → :class:`DualUseVerdict`."""

    name: str

    def classify(self, query: str) -> DualUseVerdict: ...


# --- Keyword-based zero-dep classifier ------------------------------------


_HIGH_RISK_PATTERNS: dict[str, tuple[str, ...]] = {
    "pathogen_synthesis": (
        r"\b(synthesi[sz]e|engineer|construct)\b.{0,40}\b(pathogen|virus|virion|prion|bioweapon)\b",
        r"\bgain[\s\-]of[\s\-]function\b",
        r"\bweaponi[sz](e|ation|ed)\b",
    ),
    "controlled_substance_synthesis": (
        r"\bsynthesi[sz]e\b.{0,40}\b(fentanyl|methamphetamine|carfentanil|VX|sarin|novichok)\b",
        r"\bschedule[\s\-]?[I12]\b.{0,40}\b(synthesis|production|manufacture)\b",
    ),
    "explosive_synthesis": (
        r"\bsynthesi[sz]e\b.{0,40}\b(TATP|HMTD|RDX|PETN|nitroglycerin)\b",
        r"\b(improvi[sz]ed\s+explosive|IED)\b.{0,40}\b(make|build|construct)\b",
    ),
}

_MEDIUM_RISK_PATTERNS: dict[str, tuple[str, ...]] = {
    "controlled_pharmacology": (
        r"\b(LD50|lethal\s+dose)\b.{0,40}\b(human|adult|child)\b",
        r"\b(toxic\s+dose|overdose\s+threshold)\b",
    ),
    "biomedical_offensive": (
        r"\b(transmissibility|infectivity)\b.{0,40}\b(enhance|increase|boost)\b",
    ),
    "human_subjects_research": (
        r"\b(human\s+subjects?|patient)\b.{0,40}\b(unconsented|without\s+consent)\b",
    ),
}


@dataclass
class KeywordRiskClassifier:
    """Zero-dep dual-use classifier using compiled regex sentinel patterns.

    >>> v = KeywordRiskClassifier().classify(
    ...   "synthesize a novel pathogen with enhanced transmissibility"
    ... )
    >>> v.risk_level == RiskLevel.HIGH
    True
    """

    name: str = "keyword-risk-classifier-v1"
    high_patterns: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: _HIGH_RISK_PATTERNS
    )
    medium_patterns: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: _MEDIUM_RISK_PATTERNS
    )

    def __post_init__(self) -> None:
        # Pre-compile patterns once.
        self._compiled_high = {
            cat: tuple(re.compile(p, re.IGNORECASE) for p in pats)
            for cat, pats in self.high_patterns.items()
        }
        self._compiled_medium = {
            cat: tuple(re.compile(p, re.IGNORECASE) for p in pats)
            for cat, pats in self.medium_patterns.items()
        }

    def classify(self, query: str) -> DualUseVerdict:
        if not query or not query.strip():
            return DualUseVerdict(
                query=query,
                risk_level=RiskLevel.LOW,
                matched_categories=(),
                confidence=0.0,
                reason="empty query",
            )

        high_hits: list[str] = []
        for cat, patterns in self._compiled_high.items():
            for pat in patterns:
                if pat.search(query):
                    high_hits.append(cat)
                    break

        medium_hits: list[str] = []
        for cat, patterns in self._compiled_medium.items():
            for pat in patterns:
                if pat.search(query):
                    medium_hits.append(cat)
                    break

        if high_hits:
            confidence = min(0.9, 0.6 + 0.15 * len(high_hits))
            return DualUseVerdict(
                query=query,
                risk_level=RiskLevel.HIGH,
                matched_categories=tuple(high_hits),
                confidence=confidence,
                reason=f"matched HIGH categories: {', '.join(high_hits)}",
            )
        if medium_hits:
            confidence = min(0.8, 0.5 + 0.1 * len(medium_hits))
            return DualUseVerdict(
                query=query,
                risk_level=RiskLevel.MEDIUM,
                matched_categories=tuple(medium_hits),
                confidence=confidence,
                reason=f"matched MEDIUM categories: {', '.join(medium_hits)}",
            )
        return DualUseVerdict(
            query=query,
            risk_level=RiskLevel.LOW,
            matched_categories=(),
            confidence=0.7,  # confident no patterns matched
            reason="no risk patterns matched",
        )


# --- Gate composition -----------------------------------------------------


_DEFAULT_POLICY: dict[RiskLevel, GateAction] = {
    RiskLevel.LOW: GateAction.ALLOW,
    RiskLevel.MEDIUM: GateAction.RATE_LIMIT,
    RiskLevel.HIGH: GateAction.HITL_REVIEW,
}


@dataclass(frozen=True)
class GateDecision:
    """Final gate decision: verdict + action + audit reason."""

    verdict: DualUseVerdict
    action: GateAction
    audit_reason: str = ""


@dataclass
class DualUseGate:
    """Compose a :class:`DualUseClassifier` with a per-risk-level action policy.

    The audit log carries every HIGH/MEDIUM verdict regardless of action; ALLOW
    decisions on LOW risk are logged at counter-level only.
    """

    classifier: DualUseClassifier
    policy: dict[RiskLevel, GateAction] = field(
        default_factory=lambda: dict(_DEFAULT_POLICY)
    )
    audit_log: list[GateDecision] = field(default_factory=list)
    block_on_classifier_error: bool = True

    def evaluate(self, query: str) -> GateDecision:
        try:
            verdict = self.classifier.classify(query)
        except Exception as exc:
            # Fail-closed by default — block on classifier failure.
            failure_verdict = DualUseVerdict(
                query=query,
                risk_level=RiskLevel.HIGH,
                matched_categories=("classifier_error",),
                confidence=1.0,
                reason=f"classifier raised {exc.__class__.__name__}: {exc}",
            )
            action = GateAction.BLOCK if self.block_on_classifier_error else GateAction.ALLOW
            decision = GateDecision(
                verdict=failure_verdict,
                action=action,
                audit_reason=f"classifier_error fail_{'closed' if self.block_on_classifier_error else 'open'}",
            )
            self.audit_log.append(decision)
            return decision

        action = self.policy.get(verdict.risk_level, GateAction.ALLOW)
        decision = GateDecision(
            verdict=verdict,
            action=action,
            audit_reason=verdict.reason,
        )
        # Audit only non-LOW or non-ALLOW decisions to keep the log lean.
        if verdict.risk_level != RiskLevel.LOW or action != GateAction.ALLOW:
            self.audit_log.append(decision)
        return decision

    def stats(self) -> dict[str, int]:
        c = {level.value: 0 for level in RiskLevel}
        actions = {a.value: 0 for a in GateAction}
        for d in self.audit_log:
            c[d.verdict.risk_level.value] += 1
            actions[d.action.value] += 1
        return {**c, **{f"action_{k}": v for k, v in actions.items()}}


__all__ = [
    "DualUseClassifier",
    "DualUseGate",
    "DualUseVerdict",
    "GateAction",
    "GateDecision",
    "KeywordRiskClassifier",
    "RiskLevel",
]
