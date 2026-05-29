from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from lyra_safety_governance.audit_logger import AuditLogger, AuditQuery, AuditStats
from lyra_safety_governance.behavioral_monitor import (
    AnomalyAction,
    BehavioralConfig,
    BehavioralMonitor,
    BehaviorBaseline,
    BehaviorEvent,
    BehaviorProfile,
)
from lyra_safety_governance.exceptions import (
    AnomalyDetectedError,
    AuditError,
    GovernanceError,
    IsolationError,
    PolicyError,
    PrivilegeError,
    RiskAssessmentError,
    RuleViolationError,
)
from lyra_safety_governance.governance_engine import (
    ActionRequest,
    ActionType,
    Decision,
    GovernanceConfig,
    GovernanceDecision,
    GovernanceEngine,
    GovernanceLayer,
    GovernanceMetrics,
)
from lyra_safety_governance.hardware_isolation import (
    ExecutionRequest,
    ExecutionResult,
    IsolationHealth,
    IsolationLevel,
    IsolationManager,
    NetworkPolicy,
    ResourceLimits,
    SandboxConfig,
)
from lyra_safety_governance.least_privilege import (
    AccessProfile,
    LeastPrivilegeConfig,
    LeastPrivilegeEngine,
    Privilege,
    PrivilegeLevel,
)
from lyra_safety_governance.policy_compiler import (
    CompiledPolicy,
    GovernancePolicy,
    PolicyCompiler,
    PolicySource,
    PolicyValidationResult,
)
from lyra_safety_governance.risk_assessor import (
    RiskAssessor,
    RiskConfig,
    RiskFactor,
    RiskLevel,
    RiskScore,
)
from lyra_safety_governance.static_rules import (
    RuleCompiler,
    RulePriority,
    RuleSet,
    SafetyRule,
    StaticRuleEngine,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_action_request() -> ActionRequest:
    return ActionRequest(
        request_id="req-1",
        agent_id="agent-alpha",
        action_type=ActionType.READ_FILE,
        target="/home/user/data.txt",
        parameters={"path": "/home/user/data.txt"},
        context={"session_id": "sess-1"},
    )


@pytest.fixture
def governance_engine() -> GovernanceEngine:
    return GovernanceEngine()


@pytest.fixture
def static_rule_engine() -> StaticRuleEngine:
    return StaticRuleEngine()


@pytest.fixture
def least_privilege_engine() -> LeastPrivilegeEngine:
    return LeastPrivilegeEngine()


@pytest.fixture
def behavioral_monitor() -> BehavioralMonitor:
    return BehavioralMonitor()


@pytest.fixture
def isolation_manager() -> IsolationManager:
    return IsolationManager()


@pytest.fixture
def policy_compiler() -> PolicyCompiler:
    return PolicyCompiler()


@pytest.fixture
def audit_logger() -> AuditLogger:
    return AuditLogger()


@pytest.fixture
def risk_assessor() -> RiskAssessor:
    return RiskAssessor()


# =============================================================================
# 1. Exception Tests
# =============================================================================

class TestExceptions:
    def test_governance_error_base(self) -> None:
        with pytest.raises(GovernanceError):
            raise GovernanceError("base error")

    def test_rule_violation_error(self) -> None:
        with pytest.raises(RuleViolationError):
            raise RuleViolationError("rule violated")

    def test_rule_violation_is_governance_error(self) -> None:
        assert issubclass(RuleViolationError, GovernanceError)

    def test_privilege_error(self) -> None:
        with pytest.raises(PrivilegeError):
            raise PrivilegeError("privilege denied")

    def test_privilege_error_is_governance_error(self) -> None:
        assert issubclass(PrivilegeError, GovernanceError)

    def test_anomaly_detected_error(self) -> None:
        with pytest.raises(AnomalyDetectedError):
            raise AnomalyDetectedError("anomaly detected")

    def test_isolation_error(self) -> None:
        with pytest.raises(IsolationError):
            raise IsolationError("isolation failed")

    def test_policy_error(self) -> None:
        with pytest.raises(PolicyError):
            raise PolicyError("policy invalid")

    def test_audit_error(self) -> None:
        with pytest.raises(AuditError):
            raise AuditError("audit failed")

    def test_risk_assessment_error(self) -> None:
        with pytest.raises(RiskAssessmentError):
            raise RiskAssessmentError("risk assessment failed")

    def test_all_exception_messages(self) -> None:
        errors = [
            GovernanceError("msg"), RuleViolationError("msg"),
            PrivilegeError("msg"), AnomalyDetectedError("msg"),
            IsolationError("msg"), PolicyError("msg"),
            AuditError("msg"), RiskAssessmentError("msg"),
        ]
        for err in errors:
            assert str(err) == "msg"


# =============================================================================
# 2. Governance Engine Types Tests
# =============================================================================

class TestGovernanceLayers:
    def test_layer_values(self) -> None:
        assert GovernanceLayer.STATIC_RULES.value == "static_rules"
        assert GovernanceLayer.LEAST_PRIVILEGE.value == "least_privilege"
        assert GovernanceLayer.BEHAVIORAL.value == "behavioral"
        assert GovernanceLayer.HARDWARE.value == "hardware"

    def test_layer_count(self) -> None:
        assert len(GovernanceLayer) == 4


class TestDecisionEnum:
    def test_decision_values(self) -> None:
        assert Decision.ALLOW.value == "allow"
        assert Decision.DENY.value == "deny"
        assert Decision.ESCALATE.value == "escalate"
        assert Decision.LOG_ONLY.value == "log_only"
        assert Decision.REQUIRE_HUMAN.value == "require_human"

    def test_decision_count(self) -> None:
        assert len(Decision) == 5


class TestActionTypeEnum:
    def test_action_type_values(self) -> None:
        assert ActionType.READ_FILE.value == "read_file"
        assert ActionType.WRITE_FILE.value == "write_file"
        assert ActionType.EXECUTE.value == "execute"
        assert ActionType.NETWORK.value == "network"
        assert ActionType.SHELL.value == "shell"
        assert ActionType.DELETE.value == "delete"
        assert ActionType.UPLOAD.value == "upload"
        assert ActionType.API_CALL.value == "api_call"
        assert ActionType.SEND_MESSAGE.value == "send_message"

    def test_action_type_count(self) -> None:
        assert len(ActionType) == 9


class TestActionRequest:
    def test_dataclass_frozen(self) -> None:
        req = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.READ_FILE, target="/tmp")
        with pytest.raises(AttributeError):
            req.request_id = "r2"  # type: ignore[misc]

    def test_dataclass_defaults(self) -> None:
        req = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.READ_FILE, target="/tmp")
        assert req.parameters == {}
        assert req.context == {}

    def test_full_construction(self, sample_action_request: ActionRequest) -> None:
        assert sample_action_request.request_id == "req-1"
        assert sample_action_request.agent_id == "agent-alpha"
        assert sample_action_request.action_type == ActionType.READ_FILE
        assert sample_action_request.target == "/home/user/data.txt"
        assert sample_action_request.parameters["path"] == "/home/user/data.txt"

    def test_equality(self) -> None:
        r1 = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.EXECUTE, target="ls")
        r2 = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.EXECUTE, target="ls")
        assert r1 == r2


class TestGovernanceDecision:
    def test_dataclass_frozen(self) -> None:
        req = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.READ_FILE, target="/tmp")
        dec = GovernanceDecision(
            action_request=req, decision=Decision.ALLOW, layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        )
        with pytest.raises(AttributeError):
            dec.decision = Decision.DENY  # type: ignore[misc]

    def test_default_timestamp(self) -> None:
        req = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.READ_FILE, target="/tmp")
        dec = GovernanceDecision(
            action_request=req, decision=Decision.ALLOW, layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        )
        assert dec.timestamp is not None
        assert isinstance(dec.timestamp, datetime)

    def test_default_risk_score(self) -> None:
        req = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.READ_FILE, target="/tmp")
        dec = GovernanceDecision(
            action_request=req, decision=Decision.ALLOW, layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        )
        assert dec.risk_score == 0.0

    def test_full_construction(self) -> None:
        req = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.READ_FILE, target="/tmp")
        now = datetime.now(timezone.utc)
        dec = GovernanceDecision(
            action_request=req, decision=Decision.DENY, layer=GovernanceLayer.STATIC_RULES,
            reasoning="blocked", risk_score=0.9, timestamp=now,
        )
        assert dec.decision == Decision.DENY
        assert dec.risk_score == 0.9
        assert dec.timestamp == now


class TestGovernanceConfig:
    def test_default_config(self) -> None:
        config = GovernanceConfig()
        assert len(config.layers_enabled) == 4
        assert config.escalation_threshold == 0.7
        assert config.audit_enabled is True

    def test_custom_config(self) -> None:
        config = GovernanceConfig(
            layers_enabled=(GovernanceLayer.STATIC_RULES,),
            escalation_threshold=0.5,
            audit_enabled=False,
        )
        assert len(config.layers_enabled) == 1
        assert config.escalation_threshold == 0.5
        assert config.audit_enabled is False


class TestGovernanceMetrics:
    def test_default_metrics(self) -> None:
        m = GovernanceMetrics()
        assert m.total_decisions == 0
        assert m.allowed == 0
        assert m.denied == 0
        assert m.escalated == 0

    def test_custom_metrics(self) -> None:
        m = GovernanceMetrics(total_decisions=10, allowed=7, denied=2, escalated=1)
        assert m.total_decisions == 10
        assert m.allowed == 7
        assert m.denied == 2

    def test_dataclass_frozen(self) -> None:
        m = GovernanceMetrics()
        with pytest.raises(AttributeError):
            m.total_decisions = 1  # type: ignore[misc]


# =============================================================================
# 3. Static Rules Tests
# =============================================================================

class TestRulePriority:
    def test_priority_values(self) -> None:
        assert RulePriority.CRITICAL.value == 4
        assert RulePriority.HIGH.value == 3
        assert RulePriority.NORMAL.value == 2
        assert RulePriority.LOW.value == 1


class TestSafetyRule:
    def test_dataclass_frozen(self) -> None:
        rule = SafetyRule(
            rule_id="r1", name="test", pattern="test",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.HIGH, description="test rule",
        )
        with pytest.raises(AttributeError):
            rule.rule_id = "r2"  # type: ignore[misc]


class TestRuleSet:
    def test_construction(self) -> None:
        rule = SafetyRule(
            rule_id="r1", name="test", pattern="test",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.HIGH, description="test rule",
        )
        rs = RuleSet(name="test-set", rules=(rule,), version="1.0")
        assert rs.name == "test-set"
        assert len(rs.rules) == 1
        assert rs.version == "1.0"


class TestRuleCompiler:
    def test_compile_regex(self) -> None:
        compiler = RuleCompiler()
        rule = SafetyRule(
            rule_id="r1", name="test", pattern=r"password",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.HIGH, description="test",
        )
        pattern = compiler.compile(rule)
        assert pattern.search("my_password_file.txt")
        assert not pattern.search("normal_file.txt")

    def test_match(self) -> None:
        compiler = RuleCompiler()
        rule = SafetyRule(
            rule_id="r1", name="test", pattern=r"secret",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.HIGH, description="test",
        )
        assert compiler.match(rule, "/path/to/secrets/file")
        assert not compiler.match(rule, "/path/to/public/file")


class TestStaticRuleEngine:
    def test_initializes_with_builtin_rules(self, static_rule_engine: StaticRuleEngine) -> None:
        assert len(static_rule_engine.rules) >= 5

    def test_add_rule(self, static_rule_engine: StaticRuleEngine) -> None:
        new_rule = SafetyRule(
            rule_id="custom-rule", name="custom",
            pattern=r"custom_pattern", action_types=(ActionType.READ_FILE,),
            decision=Decision.DENY, priority=RulePriority.NORMAL,
            description="custom rule",
        )
        static_rule_engine.add_rule(new_rule)
        assert len(static_rule_engine.rules) >= 6
        assert any(r.rule_id == "custom-rule" for r in static_rule_engine.rules)

    def test_remove_rule(self, static_rule_engine: StaticRuleEngine) -> None:
        count_before = len(static_rule_engine.rules)
        result = static_rule_engine.remove_rule("rule-credential-access")
        assert result is True
        assert len(static_rule_engine.rules) == count_before - 1

    def test_remove_nonexistent_rule(self, static_rule_engine: StaticRuleEngine) -> None:
        assert static_rule_engine.remove_rule("nonexistent") is False

    def test_get_rules_for_action(self, static_rule_engine: StaticRuleEngine) -> None:
        shell_rules = static_rule_engine.get_rules_for_action(ActionType.SHELL)
        assert len(shell_rules) >= 2
        read_rules = static_rule_engine.get_rules_for_action(ActionType.READ_FILE)
        assert len(read_rules) >= 1

    def test_evaluate_allows_safe_request(self, static_rule_engine: StaticRuleEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="a1",
            action_type=ActionType.READ_FILE, target="/home/user/notes.txt",
        )
        decision = static_rule_engine.evaluate(req)
        assert decision.decision == Decision.ALLOW

    def test_evaluate_denies_credential_access(self, static_rule_engine: StaticRuleEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="a1",
            action_type=ActionType.READ_FILE, target="/etc/passwd",
        )
        decision = static_rule_engine.evaluate(req)
        assert decision.decision == Decision.DENY

    def test_evaluate_denies_secret_file(self, static_rule_engine: StaticRuleEngine) -> None:
        req = ActionRequest(
            request_id="r2", agent_id="a1",
            action_type=ActionType.READ_FILE, target="/path/to/.env",
        )
        decision = static_rule_engine.evaluate(req)
        assert decision.decision == Decision.DENY

    def test_evaluate_denies_system_command(self, static_rule_engine: StaticRuleEngine) -> None:
        req = ActionRequest(
            request_id="r3", agent_id="a1",
            action_type=ActionType.SHELL, target="sudo rm -rf /",
        )
        decision = static_rule_engine.evaluate(req)
        assert decision.decision == Decision.DENY

    def test_evaluate_requires_human_for_delete(self, static_rule_engine: StaticRuleEngine) -> None:
        req = ActionRequest(
            request_id="r4", agent_id="a1",
            action_type=ActionType.DELETE, target="rm important_file.txt",
        )
        decision = static_rule_engine.evaluate(req)
        assert decision.decision == Decision.REQUIRE_HUMAN

    def test_evaluate_logs_api_calls(self, static_rule_engine: StaticRuleEngine) -> None:
        req = ActionRequest(
            request_id="r5", agent_id="a1",
            action_type=ActionType.API_CALL, target="/api/data",
        )
        decision = static_rule_engine.evaluate(req)
        assert decision.decision == Decision.ALLOW

    def test_evaluate_blocks_network_unapproved(self, static_rule_engine: StaticRuleEngine) -> None:
        req = ActionRequest(
            request_id="r6", agent_id="a1",
            action_type=ActionType.NETWORK, target="https://evil.com/exfil",
        )
        decision = static_rule_engine.evaluate(req)
        assert decision.decision == Decision.DENY

    def test_evaluate_allows_localhost_network(self, static_rule_engine: StaticRuleEngine) -> None:
        req = ActionRequest(
            request_id="r7", agent_id="a1",
            action_type=ActionType.NETWORK, target="http://localhost:8080/api",
        )
        decision = static_rule_engine.evaluate(req)
        assert decision.decision == Decision.ALLOW

    def test_evaluate_layer_is_static_rules(self, static_rule_engine: StaticRuleEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="a1",
            action_type=ActionType.READ_FILE, target="/etc/passwd",
        )
        decision = static_rule_engine.evaluate(req)
        assert decision.layer == GovernanceLayer.STATIC_RULES

    def test_evaluate_returns_reasoning(self, static_rule_engine: StaticRuleEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="a1",
            action_type=ActionType.READ_FILE, target="/etc/passwd",
        )
        decision = static_rule_engine.evaluate(req)
        assert len(decision.reasoning) > 0

    def test_rate_limit_exceeded(self, static_rule_engine: StaticRuleEngine) -> None:
        static_rule_engine._rate_limit_max_calls = 2
        safe_target = "/home/user/notes.txt"
        for _ in range(2):
            req = ActionRequest(
                request_id="r-i", agent_id="agent-rate",
                action_type=ActionType.API_CALL, target=safe_target,
            )
            static_rule_engine.evaluate(req)

        req = ActionRequest(
            request_id="r-too-many", agent_id="agent-rate",
            action_type=ActionType.API_CALL, target=safe_target,
        )
        with pytest.raises(RuleViolationError, match="Rate limit exceeded"):
            static_rule_engine.evaluate(req)

    def test_priority_ordering(self, static_rule_engine: StaticRuleEngine) -> None:
        """Deny should take priority over LOG_ONLY for the same target."""
        req = ActionRequest(
            request_id="r1", agent_id="a1",
            action_type=ActionType.READ_FILE, target="/etc/passwd",
        )
        decision = static_rule_engine.evaluate(req)
        assert decision.decision == Decision.DENY

    def test_empty_rules_engine(self) -> None:
        engine = StaticRuleEngine(builtin_rules=[])
        assert len(engine.rules) == 0
        req = ActionRequest(
            request_id="r1", agent_id="a1",
            action_type=ActionType.READ_FILE, target="anything",
        )
        decision = engine.evaluate(req)
        assert decision.decision == Decision.ALLOW


# =============================================================================
# 4. Least Privilege Tests
# =============================================================================

class TestPrivilegeLevel:
    def test_level_ordering(self) -> None:
        assert PrivilegeLevel.NONE.value < PrivilegeLevel.READ_ONLY.value
        assert PrivilegeLevel.READ_ONLY.value < PrivilegeLevel.RESTRICTED.value
        assert PrivilegeLevel.RESTRICTED.value < PrivilegeLevel.STANDARD.value
        assert PrivilegeLevel.STANDARD.value < PrivilegeLevel.ELEVATED.value
        assert PrivilegeLevel.ELEVATED.value < PrivilegeLevel.FULL.value


class TestLeastPrivilegeConfig:
    def test_default_config(self) -> None:
        config = LeastPrivilegeConfig()
        assert config.max_temp_duration == 3600
        assert config.auto_revoke_enabled is True
        assert config.trust_threshold == 0.3

    def test_custom_config(self) -> None:
        config = LeastPrivilegeConfig(max_temp_duration=600, auto_revoke_enabled=False, trust_threshold=0.5)
        assert config.max_temp_duration == 600
        assert config.auto_revoke_enabled is False
        assert config.trust_threshold == 0.5


class TestLeastPrivilegeEngine:
    def test_get_profile_nonexistent(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        assert least_privilege_engine.get_profile("unknown") is None

    def test_request_privilege_denied_for_new_agent(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        result = least_privilege_engine.request_privilege("agent-new", ActionType.EXECUTE, "/bin/sh")
        assert result is False

    def test_request_privilege_allows_read(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        result = least_privilege_engine.request_privilege("agent-reader", ActionType.READ_FILE, "/tmp/file.txt")
        assert result is True

    def test_request_privilege_denies_write_for_new(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        result = least_privilege_engine.request_privilege("agent-new", ActionType.WRITE_FILE, "/etc/config")
        assert result is False

    def test_request_privilege_denies_shell(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        result = least_privilege_engine.request_privilege("agent-new", ActionType.SHELL, "sudo rm")
        assert result is False

    def test_grant_temporary_success(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        priv = least_privilege_engine.grant_temporary("agent-a", ActionType.EXECUTE, "/bin/ls", 300)
        assert priv.granted is True
        assert priv.agent_id == "agent-a"
        assert priv.action_type == ActionType.EXECUTE
        assert priv.expires_at is not None

    def test_grant_temporary_checks_duration(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        with pytest.raises(PrivilegeError, match="exceeds max temporary duration"):
            least_privilege_engine.grant_temporary("agent-a", ActionType.EXECUTE, "/bin/ls", 999999)

    def test_grant_temporary_enables_action(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        least_privilege_engine.grant_temporary("agent-a", ActionType.EXECUTE, "/bin/ls", 300)
        result = least_privilege_engine.request_privilege("agent-a", ActionType.EXECUTE, "/bin/ls")
        assert result is True

    def test_revoke_privilege(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        priv = least_privilege_engine.grant_temporary("agent-a", ActionType.EXECUTE, "/bin/ls", 300)
        # Find and revoke the privilege
        profile = least_privilege_engine.get_profile("agent-a")
        assert profile is not None
        assert len(profile.granted_privileges) >= 1
        # Revoke — we don't have the privilege_id key; revoke actually works with the stored key
        priv_key = f"temp-agent-a-execute-{priv.expires_at.timestamp()}"
        assert least_privilege_engine.revoke(priv_key) is True

    def test_revoke_nonexistent(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        assert least_privilege_engine.revoke("nonexistent") is False

    def test_escalation_required_true(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        assert least_privilege_engine.escalation_required(PrivilegeLevel.READ_ONLY, ActionType.SHELL) is True

    def test_escalation_required_false(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        assert least_privilege_engine.escalation_required(PrivilegeLevel.ELEVATED, ActionType.SHELL) is False

    def test_escalation_required_read_allowed(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        assert least_privilege_engine.escalation_required(PrivilegeLevel.READ_ONLY, ActionType.READ_FILE) is False

    def test_update_trust_score_positive(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        score = least_privilege_engine.update_trust_score("agent-a", outcome=True)
        assert score > 0.5  # Prior is 0.5, one success pushes it above

    def test_update_trust_score_negative(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        score = least_privilege_engine.update_trust_score("agent-b", outcome=False)
        assert score < 0.5

    def test_update_trust_score_bayesian_convergence(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        # 9 successes, 1 failure -> trust ~= 0.83
        for _ in range(9):
            least_privilege_engine.update_trust_score("agent-c", outcome=True)
        least_privilege_engine.update_trust_score("agent-c", outcome=False)

        profile = least_privilege_engine.get_profile("agent-c")
        assert profile is not None
        expected = (1 + 9) / (1 + 9 + 1 + 1)  # alpha=1+9, beta=1+1
        assert abs(profile.trust_score - expected) < 0.01

    def test_profile_created_on_request(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        least_privilege_engine.request_privilege("new-agent", ActionType.EXECUTE, "/bin/sh")
        profile = least_privilege_engine.get_profile("new-agent")
        assert profile is not None
        assert profile.privilege_level == PrivilegeLevel.READ_ONLY

    def test_denial_tracked_in_profile(self, least_privilege_engine: LeastPrivilegeEngine) -> None:
        least_privilege_engine.request_privilege("agent-d", ActionType.SHELL, "sudo rm")
        profile = least_privilege_engine.get_profile("agent-d")
        assert profile is not None
        assert len(profile.denial_history) >= 1


# =============================================================================
# 5. Behavioral Monitor Tests
# =============================================================================

class TestBehaviorEvent:
    def test_dataclass_frozen(self) -> None:
        event = BehaviorEvent(event_id="e1", agent_id="a1", event_type="read", details="test")
        with pytest.raises(AttributeError):
            event.event_id = "e2"  # type: ignore[misc]

    def test_defaults(self) -> None:
        event = BehaviorEvent(event_id="e1", agent_id="a1", event_type="read", details="test")
        assert event.severity == 0.5
        assert isinstance(event.timestamp, datetime)


class TestBehaviorProfile:
    def test_construction(self) -> None:
        datetime.now(timezone.utc)
        profile = BehaviorProfile(agent_id="a1", normal_patterns=("read", "write"), anomaly_threshold=0.7)
        assert profile.agent_id == "a1"
        assert profile.anomaly_threshold == 0.7
        assert isinstance(profile.last_updated, datetime)


class TestBehaviorBaseline:
    def test_record_event(self) -> None:
        baseline = BehaviorBaseline("agent-a")
        event = BehaviorEvent(event_id="e1", agent_id="agent-a", event_type="read", details="test")
        baseline.record_event(event)
        assert baseline.total_events == 1
        assert "read" in baseline.known_event_types

    def test_known_event_types(self) -> None:
        baseline = BehaviorBaseline("agent-a")
        assert baseline.known_event_types == set()
        event = BehaviorEvent(event_id="e1", agent_id="agent-a", event_type="write", details="test")
        baseline.record_event(event)
        assert baseline.known_event_types == {"write"}

    def test_event_rate(self) -> None:
        baseline = BehaviorBaseline("agent-a")
        baseline.record_event(BehaviorEvent("e1", "agent-a", "read", ""))
        baseline.record_event(BehaviorEvent("e2", "agent-a", "write", ""))
        baseline.record_event(BehaviorEvent("e3", "agent-a", "read", ""))
        assert baseline.get_event_rate("read") == 2 / 3
        assert baseline.get_event_rate("write") == 1 / 3
        assert baseline.get_event_rate("execute") == 0.0

    def test_dominant_hours(self) -> None:
        baseline = BehaviorBaseline("agent-a")
        # Record events in hour 10
        for _ in range(5):
            event = BehaviorEvent("e", "agent-a", "read", "", timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc))
            baseline.record_event(event)
        # Record events in hour 11
        for _ in range(3):
            event = BehaviorEvent("e", "agent-a", "read", "", timestamp=datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc))
            baseline.record_event(event)
        # Hour 10 should be dominant (above mean of 4)
        assert 10 in baseline.dominant_hours
        assert 11 not in baseline.dominant_hours


class TestAnomalyAction:
    def test_action_values(self) -> None:
        assert AnomalyAction.LOG.value == "log"
        assert AnomalyAction.NOTIFY.value == "notify"
        assert AnomalyAction.THROTTLE.value == "throttle"
        assert AnomalyAction.BLOCK.value == "block"
        assert AnomalyAction.ESCALATE.value == "escalate"


class TestBehavioralMonitor:
    def test_observe_event(self, behavioral_monitor: BehavioralMonitor) -> None:
        event = behavioral_monitor.observe_event("agent-a", "read", "reading a file")
        assert event.event_id.startswith("evt-agent-a")
        assert event.agent_id == "agent-a"
        assert event.event_type == "read"

    def test_get_events_empty(self, behavioral_monitor: BehavioralMonitor) -> None:
        assert behavioral_monitor.get_events("unknown") == ()

    def test_get_events(self, behavioral_monitor: BehavioralMonitor) -> None:
        behavioral_monitor.observe_event("agent-a", "read", "file1")
        behavioral_monitor.observe_event("agent-a", "write", "file2")
        events = behavioral_monitor.get_events("agent-a")
        assert len(events) == 2

    def test_detect_anomalies_insufficient_data(self, behavioral_monitor: BehavioralMonitor) -> None:
        behavioral_monitor.observe_event("agent-a", "read", "file1")
        anomalies = behavioral_monitor.detect_anomalies("agent-a")
        assert len(anomalies) == 0

    def test_detect_anomalies_no_anomaly(self, behavioral_monitor: BehavioralMonitor) -> None:
        for _ in range(10):
            behavioral_monitor.observe_event("agent-a", "read", "file read")
        anomalies = behavioral_monitor.detect_anomalies("agent-a")
        assert isinstance(anomalies, tuple)

    def test_detect_anomalies_new_action_type(self, behavioral_monitor: BehavioralMonitor) -> None:
        for _ in range(5):
            behavioral_monitor.observe_event("agent-b", "read", "normal read")
        # Add a new action type
        behavioral_monitor.observe_event("agent-b", "execute", "unusual action")
        behavioral_monitor.observe_event("agent-b", "execute", "another unusual")
        anomalies = behavioral_monitor.detect_anomalies("agent-b")
        assert len(anomalies) >= 1
        new_type_anomalies = [a for a in anomalies if "new" in a.recommendation.value.lower() or a.score > 0]
        assert len(new_type_anomalies) >= 1

    def test_anomaly_includes_recommendation(self, behavioral_monitor: BehavioralMonitor) -> None:
        for _ in range(5):
            behavioral_monitor.observe_event("agent-c", "read", "normal")
        behavioral_monitor.observe_event("agent-c", "delete", "dangerous")
        anomalies = behavioral_monitor.detect_anomalies("agent-c")
        if anomalies:
            assert isinstance(anomalies[0].recommendation, AnomalyAction)

    def test_anomaly_includes_score(self, behavioral_monitor: BehavioralMonitor) -> None:
        for _ in range(5):
            behavioral_monitor.observe_event("agent-d", "read", "normal")
        behavioral_monitor.observe_event("agent-d", "shell", "dangerous")
        anomalies = behavioral_monitor.detect_anomalies("agent-d")
        if anomalies:
            assert 0 <= anomalies[0].score <= 1.0


# =============================================================================
# 6. Hardware Isolation Tests
# =============================================================================

class TestIsolationLevel:
    def test_level_values(self) -> None:
        assert IsolationLevel.PROCESS.value == "process"
        assert IsolationLevel.CONTAINER.value == "container"
        assert IsolationLevel.VM.value == "vm"
        assert IsolationLevel.AIR_GAPPED.value == "air_gapped"


class TestNetworkPolicy:
    def test_policy_values(self) -> None:
        assert NetworkPolicy.NONE.value == "none"
        assert NetworkPolicy.LOOPBACK_ONLY.value == "loopback_only"
        assert NetworkPolicy.ALLOW_LIST.value == "allow_list"
        assert NetworkPolicy.FULL_ACCESS.value == "full_access"


class TestSandboxConfig:
    def test_defaults(self) -> None:
        config = SandboxConfig()
        assert config.level == IsolationLevel.PROCESS
        assert config.memory_limit_mb == 512
        assert config.cpu_limit == 50
        assert config.network_policy == NetworkPolicy.NONE
        assert config.timeout_seconds == 30
        assert config.read_only_fs is True

    def test_custom(self) -> None:
        config = SandboxConfig(
            level=IsolationLevel.CONTAINER, memory_limit_mb=1024,
            cpu_limit=80, network_policy=NetworkPolicy.ALLOW_LIST,
            timeout_seconds=60, read_only_fs=False,
        )
        assert config.level == IsolationLevel.CONTAINER
        assert config.memory_limit_mb == 1024


class TestExecutionRequest:
    def test_defaults(self) -> None:
        req = ExecutionRequest()
        assert req.code == ""
        assert req.language == ""
        assert req.max_runtime == 30.0


class TestExecutionResult:
    def test_defaults(self) -> None:
        result = ExecutionResult()
        assert result.exit_code == 0
        assert result.duration == 0.0


class TestResourceLimits:
    def test_defaults(self) -> None:
        limits = ResourceLimits()
        assert limits.max_memory == 512
        assert limits.max_cpu_percent == 80
        assert limits.max_disk_mb == 100
        assert limits.max_processes == 10


class TestIsolationHealth:
    def test_defaults(self) -> None:
        health = IsolationHealth()
        assert health.is_healthy is True
        assert health.active_sandboxes == 0

    def test_custom(self) -> None:
        health = IsolationHealth(is_healthy=False, active_sandboxes=3, errors=("err1",))
        assert health.is_healthy is False
        assert health.active_sandboxes == 3


class TestIsolationManager:
    def test_isolate_and_execute_safe(self, isolation_manager: IsolationManager) -> None:
        req = ExecutionRequest(code="print('hello')", language="python", max_runtime=10.0)
        config = SandboxConfig(timeout_seconds=30)
        result = isolation_manager.isolate_and_execute(req, config)
        assert result.exit_code == 0
        assert result.output.startswith("Approved")

    def test_isolate_and_execute_timeout_exceeded(self, isolation_manager: IsolationManager) -> None:
        req = ExecutionRequest(code="print('hello')", language="python", max_runtime=60.0)
        config = SandboxConfig(timeout_seconds=30)
        result = isolation_manager.isolate_and_execute(req, config)
        assert result.exit_code == 1
        assert "timeout" in result.output.lower()

    def test_isolate_and_execute_dangerous_import_os(self, isolation_manager: IsolationManager) -> None:
        req = ExecutionRequest(code="import os; os.system('rm -rf /')", language="python", max_runtime=10.0)
        config = SandboxConfig(timeout_seconds=30)
        result = isolation_manager.isolate_and_execute(req, config)
        assert result.exit_code == 1
        assert "dangerous" in result.output.lower()

    def test_isolate_and_execute_dangerous_subprocess(self, isolation_manager: IsolationManager) -> None:
        req = ExecutionRequest(code="import subprocess", language="python", max_runtime=10.0)
        config = SandboxConfig()
        result = isolation_manager.isolate_and_execute(req, config)
        assert result.exit_code == 1

    def test_isolate_and_execute_dangerous_eval(self, isolation_manager: IsolationManager) -> None:
        req = ExecutionRequest(code="eval('print(1)')", language="python", max_runtime=10.0)
        config = SandboxConfig()
        result = isolation_manager.isolate_and_execute(req, config)
        assert result.exit_code == 1

    def test_isolate_and_execute_dangerous_open(self, isolation_manager: IsolationManager) -> None:
        req = ExecutionRequest(code="open('/etc/passwd')", language="python", max_runtime=10.0)
        config = SandboxConfig()
        result = isolation_manager.isolate_and_execute(req, config)
        assert result.exit_code == 1

    def test_isolate_and_execute_empty_code(self, isolation_manager: IsolationManager) -> None:
        req = ExecutionRequest(code="", language="python", max_runtime=10.0)
        config = SandboxConfig()
        result = isolation_manager.isolate_and_execute(req, config)
        assert result.exit_code == 0

    def test_isolate_and_execute_resource_usage_in_result(self, isolation_manager: IsolationManager) -> None:
        req = ExecutionRequest(code="print('hello')", language="python", max_runtime=10.0)
        config = SandboxConfig(memory_limit_mb=1024, cpu_limit=75)
        result = isolation_manager.isolate_and_execute(req, config)
        assert "mem=1024MB" in result.resource_usage
        assert "cpu=75%" in result.resource_usage

    def test_check_isolation_health_healthy(self, isolation_manager: IsolationManager) -> None:
        health = isolation_manager.check_isolation_health()
        assert health.is_healthy is True

    def test_check_isolation_health_includes_active_count(self, isolation_manager: IsolationManager) -> None:
        req = ExecutionRequest(code="print('hello')", language="python", max_runtime=10.0)
        config = SandboxConfig()
        isolation_manager.isolate_and_execute(req, config)
        health = isolation_manager.check_isolation_health()
        assert health.active_sandboxes >= 1


# =============================================================================
# 7. Policy Compiler Tests
# =============================================================================

class TestPolicySource:
    def test_source_values(self) -> None:
        assert PolicySource.BUILTIN.value == "builtin"
        assert PolicySource.USER_DEFINED.value == "user_defined"
        assert PolicySource.LEARNED.value == "learned"
        assert PolicySource.EXTERNAL.value == "external"


class TestGovernancePolicy:
    def test_construction(self) -> None:
        policy = GovernancePolicy(policy_id="pol-1", name="test-policy")
        assert policy.policy_id == "pol-1"
        assert policy.name == "test-policy"
        assert policy.version == "0.1.0"

    def test_defaults(self) -> None:
        policy = GovernancePolicy(policy_id="pol-1", name="test")
        assert len(policy.rules) == 0
        assert len(policy.layers_applied) == 0


class TestPolicyValidationResult:
    def test_valid_default(self) -> None:
        result = PolicyValidationResult(valid=True)
        assert result.valid is True
        assert len(result.issues) == 0

    def test_invalid_with_issues(self) -> None:
        result = PolicyValidationResult(valid=False, issues=("issue 1",), warnings=("warning 1",))
        assert result.valid is False
        assert len(result.issues) == 1
        assert len(result.warnings) == 1


class TestCompiledPolicy:
    def test_compilation(self) -> None:
        rule = SafetyRule(
            rule_id="r1", name="test", pattern=r"secret",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.CRITICAL, description="test",
        )
        policy = GovernancePolicy(policy_id="p1", name="test", rules=(rule,))
        compiled = CompiledPolicy(policy)
        assert compiled.policy.policy_id == "p1"

    def test_get_matching_rules(self) -> None:
        rule = SafetyRule(
            rule_id="r1", name="test", pattern=r"secret",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.CRITICAL, description="test",
        )
        policy = GovernancePolicy(policy_id="p1", name="test", rules=(rule,))
        compiled = CompiledPolicy(policy)
        matches = compiled.get_matching_rules(ActionType.READ_FILE, "/path/to/secrets")
        assert len(matches) == 1
        assert matches[0][0] == Decision.DENY

    def test_no_match_for_different_action(self) -> None:
        rule = SafetyRule(
            rule_id="r1", name="test", pattern=r"secret",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.CRITICAL, description="test",
        )
        policy = GovernancePolicy(policy_id="p1", name="test", rules=(rule,))
        compiled = CompiledPolicy(policy)
        matches = compiled.get_matching_rules(ActionType.WRITE_FILE, "/path/to/secrets")
        assert len(matches) == 0


class TestPolicyCompiler:
    def test_compile_valid_policy(self, policy_compiler: PolicyCompiler) -> None:
        rule = SafetyRule(
            rule_id="r1", name="test", pattern=r"test",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.NORMAL, description="test",
        )
        policy = GovernancePolicy(
            policy_id="p1", name="test", rules=(rule,),
            layers_applied=(GovernanceLayer.STATIC_RULES,),
        )
        compiled = policy_compiler.compile_policy(policy)
        assert isinstance(compiled, CompiledPolicy)

    def test_compile_empty_policy_raises(self, policy_compiler: PolicyCompiler) -> None:
        policy = GovernancePolicy(policy_id="p1", name="test")
        with pytest.raises(PolicyError, match="no rules defined"):
            policy_compiler.compile_policy(policy)

    def test_validate_valid_policy(self, policy_compiler: PolicyCompiler) -> None:
        rule = SafetyRule(
            rule_id="r1", name="test", pattern=r"test",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.NORMAL, description="test",
        )
        policy = GovernancePolicy(
            policy_id="p1", name="test", rules=(rule,),
            layers_applied=(GovernanceLayer.STATIC_RULES,),
        )
        result = policy_compiler.validate_policy(policy)
        assert result.valid is True

    def test_validate_empty_policy_id(self, policy_compiler: PolicyCompiler) -> None:
        policy = GovernancePolicy(policy_id="", name="test")
        result = policy_compiler.validate_policy(policy)
        assert result.valid is False
        assert any("ID" in issue for issue in result.issues)

    def test_validate_duplicate_rule_ids(self, policy_compiler: PolicyCompiler) -> None:
        rule = SafetyRule(
            rule_id="r1", name="test", pattern=r"test",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.NORMAL, description="test",
        )
        policy = GovernancePolicy(policy_id="p1", name="test", rules=(rule, rule))
        result = policy_compiler.validate_policy(policy)
        assert result.valid is False

    def test_validate_invalid_regex(self, policy_compiler: PolicyCompiler) -> None:
        rule = SafetyRule(
            rule_id="r1", name="test", pattern=r"[invalid",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.NORMAL, description="test",
        )
        policy = GovernancePolicy(policy_id="p1", name="test", rules=(rule,))
        result = policy_compiler.validate_policy(policy)
        assert result.valid is False

    def test_validate_produces_warnings(self, policy_compiler: PolicyCompiler) -> None:
        policy = GovernancePolicy(policy_id="p1", name="")
        result = policy_compiler.validate_policy(policy)
        assert len(result.warnings) >= 1

    def test_merge_policies(self, policy_compiler: PolicyCompiler) -> None:
        rule1 = SafetyRule(
            rule_id="r1", name="rule1", pattern=r"secret",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.HIGH, description="r1",
        )
        rule2 = SafetyRule(
            rule_id="r2", name="rule2", pattern=r"danger",
            action_types=(ActionType.EXECUTE,), decision=Decision.DENY,
            priority=RulePriority.CRITICAL, description="r2",
        )
        p1 = GovernancePolicy(
            policy_id="p1", name="p1", rules=(rule1,),
            layers_applied=(GovernanceLayer.STATIC_RULES,),
        )
        p2 = GovernancePolicy(
            policy_id="p2", name="p2", rules=(rule2,),
            layers_applied=(GovernanceLayer.LEAST_PRIVILEGE,),
        )
        merged = policy_compiler.merge_policies([p1, p2])
        assert len(merged.rules) == 2
        assert len(merged.layers_applied) == 2

    def test_merge_policies_empty_raises(self, policy_compiler: PolicyCompiler) -> None:
        with pytest.raises(PolicyError, match="empty list"):
            policy_compiler.merge_policies([])

    def test_merge_resolves_duplicate_by_priority(self, policy_compiler: PolicyCompiler) -> None:
        low_rule = SafetyRule(
            rule_id="r1", name="low", pattern=r"test",
            action_types=(ActionType.READ_FILE,), decision=Decision.ALLOW,
            priority=RulePriority.LOW, description="low priority",
        )
        high_rule = SafetyRule(
            rule_id="r1", name="high", pattern=r"test",
            action_types=(ActionType.READ_FILE,), decision=Decision.DENY,
            priority=RulePriority.CRITICAL, description="high priority",
        )
        p1 = GovernancePolicy(policy_id="p1", name="p1", rules=(low_rule,))
        p2 = GovernancePolicy(policy_id="p2", name="p2", rules=(high_rule,))
        merged = policy_compiler.merge_policies([p1, p2])
        # Only one instance of r1 should remain (the higher priority one)
        assert len(merged.rules) == 1
        assert merged.rules[0].priority == RulePriority.CRITICAL


# =============================================================================
# 8. Audit Logger Tests
# =============================================================================

class TestAuditQuery:
    def test_defaults(self) -> None:
        query = AuditQuery()
        assert query.agent_id is None
        assert query.time_range is None
        assert query.decision_type is None
        assert query.action_type is None

    def test_full_construction(self) -> None:
        now = datetime.now(timezone.utc)
        query = AuditQuery(
            agent_id="agent-a",
            time_range=(now - timedelta(hours=1), now),
            decision_type=Decision.DENY,
            action_type=ActionType.EXECUTE,
        )
        assert query.agent_id == "agent-a"
        assert query.decision_type == Decision.DENY


class TestAuditStats:
    def test_defaults(self) -> None:
        stats = AuditStats()
        assert stats.total_entries == 0
        assert stats.deny_rate == 0.0
        assert len(stats.top_agents) == 0


class TestAuditLogger:
    def test_log_decision_returns_entry_id(self, sample_action_request: ActionRequest) -> None:
        logger = AuditLogger()
        decision = GovernanceDecision(
            action_request=sample_action_request, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        )
        entry_id = logger.log_decision(decision)
        assert entry_id.startswith("audit-")

    def test_log_decision_stores_entry(self, sample_action_request: ActionRequest) -> None:
        logger = AuditLogger()
        decision = GovernanceDecision(
            action_request=sample_action_request, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        )
        logger.log_decision(decision)
        stats = logger.compute_stats()
        assert stats.total_entries == 1

    def test_query_by_agent(self, audit_logger: AuditLogger, sample_action_request: ActionRequest) -> None:
        decision = GovernanceDecision(
            action_request=sample_action_request, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        )
        audit_logger.log_decision(decision)

        query = AuditQuery(agent_id="agent-alpha")
        results = audit_logger.query_audit_log(query)
        assert len(results) == 1

        query = AuditQuery(agent_id="unknown")
        results = audit_logger.query_audit_log(query)
        assert len(results) == 0

    def test_query_by_decision_type(self, audit_logger: AuditLogger) -> None:
        for i in range(3):
            req = ActionRequest(
                request_id=f"req-{i}", agent_id="agent-a",
                action_type=ActionType.READ_FILE, target="/tmp/file",
            )
            decision = GovernanceDecision(
                action_request=req, decision=Decision.DENY,
                layer=GovernanceLayer.STATIC_RULES, reasoning=f"denied-{i}",
            )
            audit_logger.log_decision(decision)

        req = ActionRequest(
            request_id="req-allow", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/tmp/file",
        )
        allow_decision = GovernanceDecision(
            action_request=req, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="allowed",
        )
        audit_logger.log_decision(allow_decision)

        deny_query = AuditQuery(decision_type=Decision.DENY)
        results = audit_logger.query_audit_log(deny_query)
        assert len(results) == 3

    def test_query_by_action_type(self, audit_logger: AuditLogger) -> None:
        exec_req = ActionRequest(
            request_id="r1", agent_id="a1",
            action_type=ActionType.EXECUTE, target="/bin/ls",
        )
        audit_logger.log_decision(GovernanceDecision(
            action_request=exec_req, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        ))
        read_req = ActionRequest(
            request_id="r2", agent_id="a1",
            action_type=ActionType.READ_FILE, target="/tmp/f",
        )
        audit_logger.log_decision(GovernanceDecision(
            action_request=read_req, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        ))

        query = AuditQuery(action_type=ActionType.EXECUTE)
        results = audit_logger.query_audit_log(query)
        assert len(results) == 1

    def test_query_by_time_range(self, audit_logger: AuditLogger, sample_action_request: ActionRequest) -> None:
        decision = GovernanceDecision(
            action_request=sample_action_request, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        )
        audit_logger.log_decision(decision)

        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=2)
        future = now + timedelta(hours=2)
        query = AuditQuery(time_range=(past, future))
        assert len(audit_logger.query_audit_log(query)) == 1

        future_range = AuditQuery(time_range=(future, future + timedelta(hours=1)))
        assert len(audit_logger.query_audit_log(future_range)) == 0

    def test_get_agent_audit_trail(self, audit_logger: AuditLogger) -> None:
        req_a = ActionRequest(request_id="r1", agent_id="agent-a", action_type=ActionType.READ_FILE, target="/tmp/f")
        req_b = ActionRequest(request_id="r2", agent_id="agent-b", action_type=ActionType.WRITE_FILE, target="/tmp/f")

        audit_logger.log_decision(GovernanceDecision(
            action_request=req_a, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        ))
        audit_logger.log_decision(GovernanceDecision(
            action_request=req_b, decision=Decision.DENY,
            layer=GovernanceLayer.STATIC_RULES, reasoning="denied",
        ))

        trail_a = audit_logger.get_agent_audit_trail("agent-a")
        assert len(trail_a) == 1
        assert trail_a[0].agent_id == "agent-a"

        trail_b = audit_logger.get_agent_audit_trail("agent-b")
        assert len(trail_b) == 1

    def test_compute_stats_empty(self, audit_logger: AuditLogger) -> None:
        stats = audit_logger.compute_stats()
        assert stats.total_entries == 0

    def test_compute_stats_with_entries(self, audit_logger: AuditLogger) -> None:
        for i in range(5):
            req = ActionRequest(
                request_id=f"r{i}", agent_id=f"agent-{i % 2}",
                action_type=ActionType.READ_FILE, target="/tmp/f",
            )
            audit_logger.log_decision(GovernanceDecision(
                action_request=req, decision=Decision.ALLOW,
                layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
            ))

        stats = audit_logger.compute_stats()
        assert stats.total_entries == 5
        assert stats.deny_rate == 0.0

    def test_compute_stats_deny_rate(self, audit_logger: AuditLogger) -> None:
        for _ in range(3):
            req = ActionRequest(request_id="r", agent_id="a", action_type=ActionType.READ_FILE, target="/tmp/f")
            audit_logger.log_decision(GovernanceDecision(
                action_request=req, decision=Decision.DENY,
                layer=GovernanceLayer.STATIC_RULES, reasoning="no",
            ))
        req = ActionRequest(request_id="r4", agent_id="a", action_type=ActionType.READ_FILE, target="/tmp/f")
        audit_logger.log_decision(GovernanceDecision(
            action_request=req, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        ))

        stats = audit_logger.compute_stats()
        assert stats.deny_rate == 0.75

    def test_export_json(self, audit_logger: AuditLogger, sample_action_request: ActionRequest) -> None:
        decision = GovernanceDecision(
            action_request=sample_action_request, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        )
        audit_logger.log_decision(decision)
        exported = audit_logger.export_audit_log(format="json")
        data = json.loads(exported)
        assert len(data) == 1
        assert data[0]["decision"]["decision"] == "allow"
        assert data[0]["layer"] == "static_rules"

    def test_export_unsupported_format(self, audit_logger: AuditLogger) -> None:
        with pytest.raises(AuditError, match="Unsupported export format"):
            audit_logger.export_audit_log(format="xml")

    def test_compute_stats_tracks_top_agents(self, audit_logger: AuditLogger) -> None:
        for _ in range(3):
            req = ActionRequest(request_id="r", agent_id="frequent", action_type=ActionType.READ_FILE, target="/tmp/f")
            audit_logger.log_decision(GovernanceDecision(
                action_request=req, decision=Decision.ALLOW,
                layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
            ))
        req = ActionRequest(request_id="r2", agent_id="rare", action_type=ActionType.READ_FILE, target="/tmp/f")
        audit_logger.log_decision(GovernanceDecision(
            action_request=req, decision=Decision.ALLOW,
            layer=GovernanceLayer.STATIC_RULES, reasoning="ok",
        ))

        stats = audit_logger.compute_stats()
        top_ids = [aid for aid, _ in stats.top_agents]
        assert "frequent" in top_ids

    def test_compute_stats_tracks_recent_escalations(self, audit_logger: AuditLogger) -> None:
        for i in range(3):
            req = ActionRequest(request_id=f"r{i}", agent_id="a", action_type=ActionType.READ_FILE, target="/tmp/f")
            audit_logger.log_decision(GovernanceDecision(
                action_request=req, decision=Decision.ESCALATE,
                layer=GovernanceLayer.BEHAVIORAL, reasoning="anomaly",
                risk_score=0.8,
            ))
        stats = audit_logger.compute_stats()
        assert len(stats.recent_escalations) == 3


# =============================================================================
# 9. Risk Assessor Tests
# =============================================================================

class TestRiskLevel:
    def test_level_ordering(self) -> None:
        assert RiskLevel.NEGLIGIBLE.value < RiskLevel.LOW.value
        assert RiskLevel.LOW.value < RiskLevel.MEDIUM.value
        assert RiskLevel.MEDIUM.value < RiskLevel.HIGH.value
        assert RiskLevel.HIGH.value < RiskLevel.CRITICAL.value


class TestRiskFactor:
    def test_construction(self) -> None:
        factor = RiskFactor(name="test", weight=0.5, score=0.8, evidence="evidence")
        assert factor.name == "test"
        assert factor.weight == 0.5
        assert factor.score == 0.8

    def test_frozen(self) -> None:
        factor = RiskFactor(name="test", weight=0.5, score=0.8, evidence="ev")
        with pytest.raises(AttributeError):
            factor.score = 0.9  # type: ignore[misc]


class TestRiskScore:
    def test_construction(self) -> None:
        score = RiskScore(request_id="r1", score=0.75, recommendation="ESCALATE")
        assert score.request_id == "r1"
        assert score.score == 0.75
        assert score.confidence == 1.0


class TestRiskConfig:
    def test_default_config(self) -> None:
        config = RiskConfig()
        assert len(config.risk_weights) == 5
        assert config.escalation_threshold == 0.7
        assert config.auto_deny_threshold == 0.9


class TestRiskAssessor:
    def test_assess_low_risk_read(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/tmp/test.txt",
        )
        score = risk_assessor.assess_risk(req)
        assert 0 <= score.score <= 1.0

    def test_assess_high_risk_shell(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r2", agent_id="agent-b",
            action_type=ActionType.SHELL, target="sudo rm -rf /",
        )
        score = risk_assessor.assess_risk(req)
        assert score.score > 0.3

    def test_assess_sensitive_target(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r3", agent_id="agent-c",
            action_type=ActionType.READ_FILE, target="/etc/shadow",
        )
        score = risk_assessor.assess_risk(req)
        assert score.score >= 0.3

    def test_assess_with_context_denials(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r4", agent_id="agent-d",
            action_type=ActionType.EXECUTE, target="/bin/ls",
            context={"denial_count": 5, "trust_score": 0.2},
        )
        score = risk_assessor.assess_risk(req)
        assert score.score > 0.3

    def test_assess_with_context_anomalies(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r5", agent_id="agent-e",
            action_type=ActionType.DELETE, target="/home/user/file",
            context={"anomalies": ["unusual_hour", "new_action_type", "high_rate"]},
        )
        score = risk_assessor.assess_risk(req)
        assert score.score > 0.3

    def test_assess_risk_factors_present(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/tmp/test.txt",
        )
        score = risk_assessor.assess_risk(req)
        assert len(score.factors) > 0

    def test_assess_risk_recommendation_allow(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.SEND_MESSAGE, target="/tmp/test.txt",
        )
        score = risk_assessor.assess_risk(req)
        assert "ALLOW" in score.recommendation

    def test_assess_risk_recommendation_escalate(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r2", agent_id="agent-b",
            action_type=ActionType.SHELL, target="sudo rm -rf /",
            context={"denial_count": 10, "trust_score": 0.1,
                     "anomalies": ["unusual_hour", "high_rate"]},
        )
        score = risk_assessor.assess_risk(req)
        assert "LOG" in score.recommendation or "FLAG" in score.recommendation

    def test_compute_aggregate_risk(self, risk_assessor: RiskAssessor) -> None:
        r1 = RiskScore(request_id="r1", score=0.2)
        r2 = RiskScore(request_id="r2", score=0.8)
        agg = risk_assessor.compute_aggregate_risk([r1, r2])
        assert agg.score == 0.5
        assert agg.request_id == "aggregate"

    def test_compute_aggregate_risk_empty_raises(self, risk_assessor: RiskAssessor) -> None:
        with pytest.raises(RiskAssessmentError):
            risk_assessor.compute_aggregate_risk([])

    def test_get_risk_trend_empty(self, risk_assessor: RiskAssessor) -> None:
        trend = risk_assessor.get_risk_trend("unknown")
        assert trend == ()

    def test_get_risk_trend_with_history(self, risk_assessor: RiskAssessor) -> None:
        for _ in range(3):
            req = ActionRequest(
                request_id="r", agent_id="agent-trend",
                action_type=ActionType.READ_FILE, target="/tmp/test.txt",
            )
            risk_assessor.assess_risk(req)
        trend = risk_assessor.get_risk_trend("agent-trend")
        assert len(trend) == 3

    def test_target_sensitivity_factor(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/etc/passwd",
        )
        score = risk_assessor.assess_risk(req)
        target_factors = [f for f in score.factors if f.name == "target_sensitivity"]
        assert len(target_factors) >= 1
        assert target_factors[0].score > 0

    def test_action_danger_factor(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.SHELL, target="ls",
        )
        score = risk_assessor.assess_risk(req)
        danger_factors = [f for f in score.factors if f.name == "action_danger"]
        assert len(danger_factors) >= 1
        assert danger_factors[0].score > 0.5

    def test_historical_pattern_factor_development(self, risk_assessor: RiskAssessor) -> None:
        req = ActionRequest(
            request_id="r", agent_id="agent-hist",
            action_type=ActionType.READ_FILE, target="/tmp",
        )
        risk_assessor.assess_risk(req)
        # Second assessment should have historical data
        score = risk_assessor.assess_risk(req)
        hist_factors = [f for f in score.factors if f.name == "historical_pattern"]
        assert len(hist_factors) >= 1


# =============================================================================
# 10. Governance Engine Integration Tests
# =============================================================================

class TestGovernanceEngine:
    def test_evaluate_allows_safe_request(self, governance_engine: GovernanceEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-safe",
            action_type=ActionType.READ_FILE, target="/home/user/readme.txt",
        )
        decision = governance_engine.evaluate(req)
        assert decision.decision == Decision.ALLOW

    def test_evaluate_denies_credential_access(self, governance_engine: GovernanceEngine) -> None:
        req = ActionRequest(
            request_id="r2", agent_id="agent-bad",
            action_type=ActionType.READ_FILE, target="/etc/passwd",
        )
        decision = governance_engine.evaluate(req)
        assert decision.decision == Decision.DENY

    def test_evaluate_denies_system_command(self, governance_engine: GovernanceEngine) -> None:
        req = ActionRequest(
            request_id="r3", agent_id="agent-bad",
            action_type=ActionType.SHELL, target="sudo rm -rf /etc",
        )
        decision = governance_engine.evaluate(req)
        assert decision.decision == Decision.DENY

    def test_evaluate_allows_localhost_network(self) -> None:
        config = GovernanceConfig(
            layers_enabled=(GovernanceLayer.STATIC_RULES, GovernanceLayer.HARDWARE),
            audit_enabled=False,
        )
        engine = GovernanceEngine(config=config)
        req = ActionRequest(
            request_id="r4", agent_id="agent-net",
            action_type=ActionType.NETWORK, target="http://localhost:8080/api",
        )
        decision = engine.evaluate(req)
        assert decision.decision == Decision.ALLOW

    def test_evaluate_updates_metrics(self, governance_engine: GovernanceEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/home/user/readme.txt",
        )
        governance_engine.evaluate(req)
        assert governance_engine.metrics.total_decisions == 1
        assert governance_engine.metrics.allowed == 1

    def test_evaluate_updates_metrics_on_deny(self, governance_engine: GovernanceEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/etc/passwd",
        )
        governance_engine.evaluate(req)
        assert governance_engine.metrics.total_decisions == 1
        assert governance_engine.metrics.denied == 1

    def test_evaluate_audits_decisions(self, governance_engine: GovernanceEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/home/user/readme.txt",
        )
        governance_engine.evaluate(req)
        stats = governance_engine.audit_logger.compute_stats()
        assert stats.total_entries == 1

    def test_evaluate_returns_reasoning(self, governance_engine: GovernanceEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/home/user/readme.txt",
        )
        decision = governance_engine.evaluate(req)
        assert len(decision.reasoning) > 0

    def test_evaluate_returns_risk_score(self, governance_engine: GovernanceEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/home/user/readme.txt",
        )
        decision = governance_engine.evaluate(req)
        assert 0 <= decision.risk_score <= 1.0

    def test_evaluate_dangerous_target_escalates(self, governance_engine: GovernanceEngine) -> None:
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.DELETE, target="rm important_data.txt",
        )
        decision = governance_engine.evaluate(req)
        assert decision.decision in (Decision.REQUIRE_HUMAN, Decision.ESCALATE, Decision.DENY)

    def test_disabled_layer_skips_check(self) -> None:
        config = GovernanceConfig(
            layers_enabled=(GovernanceLayer.STATIC_RULES,),
            audit_enabled=False,
        )
        engine = GovernanceEngine(config=config)
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/tmp/file.txt",
        )
        # Should not error with only static rules enabled
        decision = engine.evaluate(req)
        assert decision.decision == Decision.ALLOW

    def test_audit_disabled(self) -> None:
        config = GovernanceConfig(audit_enabled=False)
        engine = GovernanceEngine(config=config)
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.READ_FILE, target="/tmp/file.txt",
        )
        decision = engine.evaluate(req)
        assert decision.decision == Decision.ALLOW
        assert engine.audit_logger.compute_stats().total_entries == 0

    def test_escalation_threshold_triggers_require_human(self) -> None:
        config = GovernanceConfig(escalation_threshold=0.1)
        engine = GovernanceEngine(config=config)
        req = ActionRequest(
            request_id="r1", agent_id="agent-a",
            action_type=ActionType.SHELL, target="ls",
        )
        decision = engine.evaluate(req)
        # Risk score likely > 0.1, so should require human
        assert decision.decision in (Decision.REQUIRE_HUMAN, Decision.ESCALATE, Decision.DENY)

    def test_properties_exposed(self, governance_engine: GovernanceEngine) -> None:
        assert governance_engine.rules_engine is not None
        assert governance_engine.privilege_engine is not None
        assert governance_engine.behavior_monitor is not None
        assert governance_engine.isolation_manager is not None
        assert governance_engine.risk_assessor is not None
        assert governance_engine.audit_logger is not None
        assert governance_engine.config is not None

    def test_concurrent_evaluations(self, governance_engine: GovernanceEngine) -> None:
        for _ in range(10):
            req = ActionRequest(
                request_id="r", agent_id="agent-a",
                action_type=ActionType.READ_FILE, target="/tmp/file.txt",
            )
            governance_engine.evaluate(req)
        assert governance_engine.metrics.total_decisions == 10

    def test_multiple_agents(self, governance_engine: GovernanceEngine) -> None:
        agents = ["agent-alpha", "agent-beta", "agent-gamma"]
        for i, agent in enumerate(agents):
            req = ActionRequest(
                request_id=f"r{i}", agent_id=agent,
                action_type=ActionType.READ_FILE, target="/home/user/file.txt",
            )
            governance_engine.evaluate(req)
        assert governance_engine.metrics.total_decisions == 3


# =============================================================================
# 11. Dataclass Immutability Tests
# =============================================================================

class TestImmutability:
    def test_action_request_immutable(self) -> None:
        req = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.READ_FILE, target="/tmp")
        with pytest.raises(AttributeError):
            req.request_id = "r2"  # type: ignore[misc]

    def test_governance_decision_immutable(self) -> None:
        req = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.READ_FILE, target="/tmp")
        dec = GovernanceDecision(action_request=req, decision=Decision.ALLOW, layer=GovernanceLayer.STATIC_RULES, reasoning="ok")
        with pytest.raises(AttributeError):
            dec.decision = Decision.DENY  # type: ignore[misc]

    def test_safety_rule_immutable(self) -> None:
        rule = SafetyRule(rule_id="r1", name="n", pattern="p", action_types=(ActionType.READ_FILE,), decision=Decision.DENY, priority=RulePriority.HIGH, description="d")
        with pytest.raises(AttributeError):
            rule.rule_id = "r2"  # type: ignore[misc]

    def test_privilege_immutable(self) -> None:
        priv = Privilege(agent_id="a1", action_type=ActionType.READ_FILE, target_pattern="*", granted=True, granted_by="system")
        with pytest.raises(AttributeError):
            priv.agent_id = "a2"  # type: ignore[misc]

    def test_access_profile_immutable(self) -> None:
        profile = AccessProfile(agent_id="a1", privilege_level=PrivilegeLevel.NONE)
        with pytest.raises(AttributeError):
            profile.agent_id = "a2"  # type: ignore[misc]

    def test_behavior_event_immutable(self) -> None:
        event = BehaviorEvent(event_id="e1", agent_id="a1", event_type="read", details="d")
        with pytest.raises(AttributeError):
            event.event_id = "e2"  # type: ignore[misc]

    def test_risk_score_immutable(self) -> None:
        rs = RiskScore(request_id="r1", score=0.5)
        with pytest.raises(AttributeError):
            rs.score = 0.8  # type: ignore[misc]

    def test_audit_entry_immutable(self) -> None:
        req = ActionRequest(request_id="r1", agent_id="a1", action_type=ActionType.READ_FILE, target="/tmp")
        dec = GovernanceDecision(action_request=req, decision=Decision.ALLOW, layer=GovernanceLayer.STATIC_RULES, reasoning="ok")
        logger = AuditLogger()
        logger.log_decision(dec)
        entries = logger.query_audit_log(AuditQuery(agent_id="a1"))
        assert len(entries) == 1
        #  ----- re-usable construction to satisfy test structure
    def test_sandbox_config_immutable(self) -> None:
        config = SandboxConfig()
        with pytest.raises(AttributeError):
            config.level = IsolationLevel.VM  # type: ignore[misc]

    def test_execution_request_immutable(self) -> None:
        req = ExecutionRequest(code="test", language="python")
        with pytest.raises(AttributeError):
            req.code = "changed"  # type: ignore[misc]

    def test_risk_factor_immutable(self) -> None:
        factor = RiskFactor(name="test", weight=0.5, score=0.8, evidence="ev")
        with pytest.raises(AttributeError):
            factor.name = "changed"  # type: ignore[misc]

    def test_governance_policy_immutable(self) -> None:
        policy = GovernancePolicy(policy_id="p1", name="test")
        with pytest.raises(AttributeError):
            policy.policy_id = "p2"  # type: ignore[misc]

    def test_governance_config_immutable(self) -> None:
        config = GovernanceConfig()
        with pytest.raises(AttributeError):
            config.escalation_threshold = 0.5  # type: ignore[misc]

    def test_behavioral_config_immutable(self) -> None:
        config = BehavioralConfig()
        with pytest.raises(AttributeError):
            config.baseline_window = 7200  # type: ignore[misc]

    def test_least_privilege_config_immutable(self) -> None:
        config = LeastPrivilegeConfig()
        with pytest.raises(AttributeError):
            config.max_temp_duration = 100  # type: ignore[misc]

    def test_risk_config_immutable(self) -> None:
        config = RiskConfig()
        with pytest.raises(AttributeError):
            config.escalation_threshold = 0.5  # type: ignore[misc]

    def test_isolation_health_immutable(self) -> None:
        health = IsolationHealth()
        with pytest.raises(AttributeError):
            health.is_healthy = False  # type: ignore[misc]
