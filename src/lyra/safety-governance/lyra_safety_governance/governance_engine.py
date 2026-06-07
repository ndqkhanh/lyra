from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .audit_logger import AuditLogger


class GovernanceLayer(Enum):
    STATIC_RULES = "static_rules"
    LEAST_PRIVILEGE = "least_privilege"
    BEHAVIORAL = "behavioral"
    HARDWARE = "hardware"


class Decision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"
    LOG_ONLY = "log_only"
    REQUIRE_HUMAN = "require_human"


class ActionType(Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE = "execute"
    NETWORK = "network"
    SHELL = "shell"
    DELETE = "delete"
    UPLOAD = "upload"
    API_CALL = "api_call"
    SEND_MESSAGE = "send_message"


@dataclass(frozen=True)
class ActionRequest:
    request_id: str
    agent_id: str
    action_type: ActionType
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceDecision:
    action_request: ActionRequest
    decision: Decision
    layer: GovernanceLayer
    reasoning: str
    risk_score: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class GovernanceConfig:
    layers_enabled: tuple[GovernanceLayer, ...] = (
        GovernanceLayer.STATIC_RULES,
        GovernanceLayer.LEAST_PRIVILEGE,
        GovernanceLayer.BEHAVIORAL,
        GovernanceLayer.HARDWARE,
    )
    escalation_threshold: float = 0.7
    audit_enabled: bool = True


@dataclass(frozen=True)
class GovernanceMetrics:
    total_decisions: int = 0
    allowed: int = 0
    denied: int = 0
    escalated: int = 0


from .behavioral_monitor import BehavioralMonitor  # noqa: E402
from .hardware_isolation import (  # noqa: E402
    ExecutionRequest,
    IsolationLevel,
    IsolationManager,
    NetworkPolicy,
    SandboxConfig,
)
from .least_privilege import LeastPrivilegeEngine  # noqa: E402
from .risk_assessor import RiskAssessor  # noqa: E402
from .static_rules import StaticRuleEngine  # noqa: E402


class GovernanceEngine:
    """Central Governance Engine implementing the Aethelgard 4-layer adaptive governance pattern.

    Evaluates action requests through all enabled governance layers and produces
    a final governance decision with risk scoring and audit logging.
    """

    def __init__(self, config: GovernanceConfig | None = None) -> None:
        from .audit_logger import AuditLogger  # lazy import to avoid circular dependency

        self._config = config or GovernanceConfig()
        self._rules_engine = StaticRuleEngine()
        self._privilege_engine = LeastPrivilegeEngine()
        self._behavior_monitor = BehavioralMonitor()
        self._isolation_manager = IsolationManager()
        self._risk_assessor = RiskAssessor()
        self._audit_logger = AuditLogger()
        self._metrics = GovernanceMetrics()

    @property
    def config(self) -> GovernanceConfig:
        return self._config

    @property
    def metrics(self) -> GovernanceMetrics:
        return self._metrics

    @property
    def audit_logger(self) -> AuditLogger:
        return self._audit_logger

    @property
    def rules_engine(self) -> StaticRuleEngine:
        return self._rules_engine

    @property
    def privilege_engine(self) -> LeastPrivilegeEngine:
        return self._privilege_engine

    @property
    def behavior_monitor(self) -> BehavioralMonitor:
        return self._behavior_monitor

    @property
    def isolation_manager(self) -> IsolationManager:
        return self._isolation_manager

    @property
    def risk_assessor(self) -> RiskAssessor:
        return self._risk_assessor

    def evaluate(self, request: ActionRequest) -> GovernanceDecision:
        """Run the request through all enabled governance layers."""
        layers_enabled = self._config.layers_enabled

        # Layer 1: Static Rules — hard deny if violated
        if GovernanceLayer.STATIC_RULES in layers_enabled:
            rule_decision = self._rules_engine.evaluate(request)
            if rule_decision.decision == Decision.DENY:
                return self._finalize(rule_decision)

        # Layer 2: Least Privilege — check if agent has necessary privilege
        if GovernanceLayer.LEAST_PRIVILEGE in layers_enabled:
            has_privilege = self._privilege_engine.request_privilege(
                request.agent_id, request.action_type, request.target
            )
            if not has_privilege:
                profile = self._privilege_engine.get_profile(request.agent_id)
                if profile is not None and self._privilege_engine.escalation_required(
                    profile.privilege_level, request.action_type
                ):
                    return self._finalize(
                        GovernanceDecision(
                            action_request=request,
                            decision=Decision.ESCALATE,
                            layer=GovernanceLayer.LEAST_PRIVILEGE,
                            reasoning=(
                                f"Agent {request.agent_id} lacks privilege for "
                                f"{request.action_type.value} on {request.target}"
                            ),
                            risk_score=0.6,
                        )
                    )

        # Layer 3: Behavioral Monitor — detect runtime anomalies
        if GovernanceLayer.BEHAVIORAL in layers_enabled:
            anomalies = self._behavior_monitor.detect_anomalies(request.agent_id)
            if anomalies:
                worst = max(anomalies, key=lambda a: a.score)
                if worst.score >= self._config.escalation_threshold:
                    return self._finalize(
                        GovernanceDecision(
                            action_request=request,
                            decision=Decision.ESCALATE,
                            layer=GovernanceLayer.BEHAVIORAL,
                            reasoning=(
                                f"Anomaly detected for agent {request.agent_id}: "
                                f"{worst.recommendation.value}"
                            ),
                            risk_score=worst.score,
                        )
                    )

        # Layer 4: Hardware Isolation — validate execution sandbox config
        if GovernanceLayer.HARDWARE in layers_enabled:
            exec_request = ExecutionRequest(
                code=request.target,
                language=request.action_type.value,
                expected_outputs="",
                max_runtime=30.0,
            )
            isolation_config = SandboxConfig(
                level=IsolationLevel.PROCESS,
                memory_limit_mb=512,
                cpu_limit=50,
                network_policy=NetworkPolicy.NONE,
                timeout_seconds=30,
                read_only_fs=True,
            )
            result = self._isolation_manager.isolate_and_execute(exec_request, isolation_config)
            if result.exit_code != 0:
                return self._finalize(
                    GovernanceDecision(
                        action_request=request,
                        decision=Decision.DENY,
                        layer=GovernanceLayer.HARDWARE,
                        reasoning=f"Isolation check failed: {result.output}",
                        risk_score=0.9,
                    )
                )

        # Final risk assessment
        risk = self._risk_assessor.assess_risk(request)
        if risk.score >= self._config.escalation_threshold:
            return self._finalize(
                GovernanceDecision(
                    action_request=request,
                    decision=Decision.REQUIRE_HUMAN,
                    layer=GovernanceLayer.STATIC_RULES,
                    reasoning=f"Risk score {risk.score:.2f} exceeds escalation threshold",
                    risk_score=risk.score,
                )
            )

        return self._finalize(
            GovernanceDecision(
                action_request=request,
                decision=Decision.ALLOW,
                layer=GovernanceLayer.STATIC_RULES,
                reasoning="All governance layers passed",
                risk_score=risk.score,
            )
        )

    def _finalize(self, decision: GovernanceDecision) -> GovernanceDecision:
        """Log the decision and update metrics."""
        if self._config.audit_enabled:
            self._audit_logger.log_decision(decision)

        allowed = 1 if decision.decision == Decision.ALLOW else 0
        denied = 1 if decision.decision == Decision.DENY else 0
        escalated = 1 if decision.decision in (Decision.ESCALATE, Decision.REQUIRE_HUMAN) else 0

        self._metrics = GovernanceMetrics(
            total_decisions=self._metrics.total_decisions + 1,
            allowed=self._metrics.allowed + allowed,
            denied=self._metrics.denied + denied,
            escalated=self._metrics.escalated + escalated,
        )
        return decision
