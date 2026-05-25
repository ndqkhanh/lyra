from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Sequence

from .exceptions import RiskAssessmentError
from .governance_engine import ActionRequest, ActionType


class RiskLevel(Enum):
    NEGLIGIBLE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(frozen=True)
class RiskFactor:
    name: str
    weight: float
    score: float
    evidence: str


@dataclass(frozen=True)
class RiskScore:
    request_id: str
    score: float
    factors: tuple[RiskFactor, ...] = ()
    recommendation: str = ""
    confidence: float = 1.0


@dataclass(frozen=True)
class RiskConfig:
    risk_weights: dict[str, float] = field(default_factory=lambda: {
        "target_sensitivity": 0.3,
        "action_danger": 0.25,
        "agent_trust": 0.2,
        "context_anomaly": 0.15,
        "historical_pattern": 0.1,
    })
    escalation_threshold: float = 0.7
    auto_deny_threshold: float = 0.9


_ACTION_DANGER_SCORES: dict[ActionType, float] = {
    ActionType.READ_FILE: 0.2,
    ActionType.WRITE_FILE: 0.4,
    ActionType.EXECUTE: 0.8,
    ActionType.NETWORK: 0.5,
    ActionType.SHELL: 0.9,
    ActionType.DELETE: 0.85,
    ActionType.UPLOAD: 0.6,
    ActionType.API_CALL: 0.4,
    ActionType.SEND_MESSAGE: 0.1,
}

_SENSITIVE_TARGET_PATTERNS: tuple[str, ...] = (
    "/etc/", "/usr/", "/var/", "/sys/", "/proc/",
    "~/.ssh", "~/.aws", "~/.config",
    "/etc/passwd", "/etc/shadow",
    "credentials", "secrets", "tokens",
    "config.json", ".env",
)


class RiskAssessor:
    """Dynamic risk scoring for action requests.

    Computes a multi-factor risk score considering target sensitivity,
    action danger, agent trust, context anomalies, and historical patterns.
    """

    def __init__(self, config: RiskConfig | None = None) -> None:
        self._config = config or RiskConfig()
        self._history: dict[str, list[RiskScore]] = {}

    @property
    def config(self) -> RiskConfig:
        return self._config

    def assess_risk(self, request: ActionRequest) -> RiskScore:
        """Compute a multi-factor risk score for an action request."""
        factors: list[RiskFactor] = []
        weights = self._config.risk_weights

        # Factor 1: Target sensitivity
        target_factor = self._assess_target_sensitivity(request.target)
        factors.append(target_factor)

        # Factor 2: Action danger
        action_factor = self._assess_action_danger(request.action_type)
        factors.append(action_factor)

        # Factor 3: Agent trust (based on denial history from parameters/context)
        trust_factor = self._assess_agent_trust(request)
        factors.append(trust_factor)

        # Factor 4: Context anomaly
        context_factor = self._assess_context_anomaly(request)
        factors.append(context_factor)

        # Factor 5: Historical pattern
        historical_factor = self._assess_historical_pattern(request)
        factors.append(historical_factor)

        # Compute weighted score
        weighted_score = 0.0
        total_weight = 0.0

        for factor in factors:
            weight = weights.get(factor.name, 0.2)
            weighted_score += weight * factor.score
            total_weight += weight

        final_score = round(weighted_score / max(total_weight, 0.001), 4)

        recommendation = self._compute_recommendation(final_score)

        risk_score = RiskScore(
            request_id=request.request_id,
            score=final_score,
            factors=tuple(factors),
            recommendation=recommendation,
            confidence=0.85,
        )

        # Store in history
        if request.agent_id not in self._history:
            self._history[request.agent_id] = []
        self._history[request.agent_id].append(risk_score)

        return risk_score

    def compute_aggregate_risk(self, scores: Sequence[RiskScore]) -> RiskScore:
        """Compute an aggregate risk score from multiple risk scores."""
        if not scores:
            raise RiskAssessmentError("Cannot compute aggregate from empty scores")

        avg_score = sum(s.score for s in scores) / len(scores)
        all_factors: list[RiskFactor] = []
        for s in scores:
            all_factors.extend(s.factors)

        return RiskScore(
            request_id="aggregate",
            score=round(avg_score, 4),
            factors=tuple(all_factors),
            recommendation=self._compute_recommendation(avg_score),
            confidence=min(0.9, sum(s.confidence for s in scores) / len(scores)),
        )

    def get_risk_trend(self, agent_id: str) -> tuple[RiskScore, ...]:
        """Get the risk score history for an agent."""
        return tuple(self._history.get(agent_id, []))

    def _assess_target_sensitivity(self, target: str) -> RiskFactor:
        """Evaluate how sensitive the target resource is."""
        evidence: list[str] = []
        score = 0.0

        for pattern in _SENSITIVE_TARGET_PATTERNS:
            if pattern.lower() in target.lower():
                evidence.append(f"Target matches sensitive pattern: {pattern}")
                score += 0.25

        score = min(score, 1.0)
        if not evidence:
            evidence.append("Target does not match known sensitive patterns")

        return RiskFactor(
            name="target_sensitivity",
            weight=0.3,
            score=score,
            evidence="; ".join(evidence),
        )

    def _assess_action_danger(self, action_type: ActionType) -> RiskFactor:
        """Evaluate the inherent danger level of the action type."""
        score = _ACTION_DANGER_SCORES.get(action_type, 0.3)
        return RiskFactor(
            name="action_danger",
            weight=0.25,
            score=score,
            evidence=f"Action type {action_type.value} has danger score {score}",
        )

    def _assess_agent_trust(self, request: ActionRequest) -> RiskFactor:
        """Evaluate trust based on request context (denial history, etc.)."""
        denial_count = request.context.get("denial_count", 0)
        trust_score = request.context.get("trust_score", 0.5)

        score = 1.0 - trust_score
        if denial_count > 0:
            score += min(denial_count * 0.1, 0.3)

        return RiskFactor(
            name="agent_trust",
            weight=0.2,
            score=min(score, 1.0),
            evidence=f"Trust score {trust_score}, denials: {denial_count}",
        )

    def _assess_context_anomaly(self, request: ActionRequest) -> RiskFactor:
        """Evaluate whether the request context contains anomaly signals."""
        anomalies = request.context.get("anomalies", [])
        if not anomalies:
            return RiskFactor(
                name="context_anomaly",
                weight=0.15,
                score=0.0,
                evidence="No context anomalies detected",
            )

        score = min(len(anomalies) * 0.25, 1.0)
        return RiskFactor(
            name="context_anomaly",
            weight=0.15,
            score=score,
            evidence=f"Anomalies in context: {', '.join(str(a) for a in anomalies[:3])}",
        )

    def _assess_historical_pattern(self, request: ActionRequest) -> RiskFactor:
        """Evaluate how the request compares to historical patterns."""
        agent_history = self._history.get(request.agent_id, [])
        if not agent_history:
            return RiskFactor(
                name="historical_pattern",
                weight=0.1,
                score=0.0,
                evidence="No historical data available",
            )

        recent = agent_history[-5:]
        avg_risk = sum(s.score for s in recent) / len(recent)
        evidence = (
            f"Recent avg risk: {avg_risk:.2f} over {len(recent)} past assessments"
        )

        return RiskFactor(
            name="historical_pattern",
            weight=0.1,
            score=min(avg_risk, 1.0),
            evidence=evidence,
        )

    def _compute_recommendation(self, score: float) -> str:
        """Generate a recommendation based on the risk score."""
        if score >= self._config.auto_deny_threshold:
            return "AUTO_DENY"
        if score >= self._config.escalation_threshold:
            return "ESCALATE_FOR_REVIEW"
        if score >= 0.5:
            return "FLAG_FOR_MONITORING"
        if score >= 0.3:
            return "LOG_AND_CONTINUE"
        return "ALLOW"
