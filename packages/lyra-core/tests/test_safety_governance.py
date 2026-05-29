"""Tests for Phase 8: Safety Governance Layer."""

from __future__ import annotations

import time

import pytest
from lyra_core.safety import (
    ComplianceFramework,
    ComplianceMapper,
    OverrideRequest,
    OverrideWorkflow,
    PolicyEngine,
    PolicyRule,
    PolicyVerdict,
    SafetyPolicy,
)

# ═══════════════════════════════════════════════════════════════════════════════
# PolicyVerdict
# ═══════════════════════════════════════════════════════════════════════════════


class TestPolicyVerdict:
    def test_verdict_values(self):
        assert PolicyVerdict.ALLOW.value == "allow"
        assert PolicyVerdict.DENY.value == "deny"
        assert PolicyVerdict.FLAG.value == "flag"
        assert PolicyVerdict.ESCALATE.value == "escalate"
        assert PolicyVerdict.QUARANTINE.value == "quarantine"

    def test_verdict_is_str_enum(self):
        assert isinstance(PolicyVerdict.ALLOW, str)
        assert PolicyVerdict.ALLOW == "allow"


# ═══════════════════════════════════════════════════════════════════════════════
# PolicyRule
# ═══════════════════════════════════════════════════════════════════════════════


class TestPolicyRule:
    def test_create_rule(self):
        rule = PolicyRule(
            id="r1", name="No Exec", description="Block code execution",
            condition="os.system", verdict=PolicyVerdict.DENY,
        )
        assert rule.id == "r1"
        assert rule.name == "No Exec"
        assert rule.condition == "os.system"
        assert rule.verdict == PolicyVerdict.DENY
        assert rule.priority == 50
        assert rule.enabled is True

    def test_create_with_custom_priority(self):
        rule = PolicyRule(
            id="r2", name="High Priority", description="Important rule",
            condition="rm -rf", verdict=PolicyVerdict.DENY, priority=10,
        )
        assert rule.priority == 10

    def test_create_with_tags_and_frameworks(self):
        rule = PolicyRule(
            id="r3", name="GDPR Rule", description="Data protection",
            condition="pii", verdict=PolicyVerdict.FLAG,
            tags=("privacy", "data"), frameworks=("GDPR", "CCPA"),
        )
        assert rule.tags == ("privacy", "data")
        assert rule.frameworks == ("GDPR", "CCPA")

    def test_default_auto_remediation_empty(self):
        rule = PolicyRule(
            id="r4", name="Simple", description="Simple rule",
            condition="test", verdict=PolicyVerdict.FLAG,
        )
        assert rule.auto_remediation == ""

    def test_with_enabled_returns_new_copy(self):
        rule = PolicyRule(
            id="r5", name="Toggle", description="Toggle rule",
            condition="toggle", verdict=PolicyVerdict.FLAG, enabled=True,
        )
        disabled = rule.with_enabled(False)
        assert rule.enabled is True
        assert disabled.enabled is False
        assert disabled.id == rule.id
        assert disabled.name == rule.name

    def test_with_enabled_toggle_back(self):
        rule = PolicyRule(
            id="r6", name="Toggle2", description="Toggle rule 2",
            condition="toggle", verdict=PolicyVerdict.FLAG, enabled=False,
        )
        enabled = rule.with_enabled(True)
        assert enabled.enabled is True
        assert rule.enabled is False

    def test_rule_is_frozen(self):
        rule = PolicyRule(
            id="r7", name="Frozen", description="Test frozen",
            condition="test", verdict=PolicyVerdict.ALLOW,
        )
        with pytest.raises(Exception):  # noqa: B017
            rule.enabled = False  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# SafetyPolicy
# ═══════════════════════════════════════════════════════════════════════════════


class TestSafetyPolicy:
    @pytest.fixture
    def deny_exec_rule(self):
        return PolicyRule(
            id="r1", name="No Exec", description="Block code execution",
            condition="os.system", verdict=PolicyVerdict.DENY, priority=10,
        )

    @pytest.fixture
    def flag_pii_rule(self):
        return PolicyRule(
            id="r2", name="Flag PII", description="Flag PII access",
            condition="credit_card", verdict=PolicyVerdict.FLAG, priority=20,
        )

    @pytest.fixture
    def allow_safe_rule(self):
        return PolicyRule(
            id="r3", name="Allow Safe", description="Allow safe ops",
            condition="safe_operation", verdict=PolicyVerdict.ALLOW, priority=30,
        )

    @pytest.fixture
    def policy(self, deny_exec_rule, flag_pii_rule, allow_safe_rule):
        return SafetyPolicy(
            id="p1", name="Code Safety", version="1.0",
            description="Standard code safety policy",
            rules=(deny_exec_rule, flag_pii_rule, allow_safe_rule),
        )

    def test_create_policy(self, policy):
        assert policy.id == "p1"
        assert policy.name == "Code Safety"
        assert policy.version == "1.0"
        assert len(policy.rules) == 3
        assert policy.enabled is True

    def test_default_verdict_is_flag(self):
        policy = SafetyPolicy(
            id="p2", name="Empty", version="1.0",
            description="Policy with no rules", rules=(),
        )
        assert policy.default_verdict == PolicyVerdict.FLAG

    def test_evaluate_no_match_returns_default(self, policy):
        verdict = policy.evaluate({"action": "read_file", "code": "hello"})
        assert verdict == PolicyVerdict.FLAG

    def test_evaluate_matches_highest_priority(self, policy):
        ctx = {"action": "run", "code": "os.system('ls')"}
        verdict = policy.evaluate(ctx)
        assert verdict == PolicyVerdict.DENY

    def test_evaluate_with_disabled_rule(self, deny_exec_rule, flag_pii_rule):
        disabled_exec = deny_exec_rule.with_enabled(False)
        policy = SafetyPolicy(
            id="p3", name="Test", version="1.0",
            description="Test disabled rule",
            rules=(disabled_exec, flag_pii_rule),
        )
        ctx = {"action": "run", "code": "os.system('ls')"}
        verdict = policy.evaluate(ctx)
        assert verdict == PolicyVerdict.FLAG

    def test_get_triggered_rules(self, policy):
        ctx = {"action": "run", "code": "contains credit_card data"}
        triggered = policy.get_triggered_rules(ctx)
        assert len(triggered) == 1
        assert triggered[0].id == "r2"

    def test_get_triggered_rules_multiple(self, policy):
        ctx = {"action": "run", "code": "os.system with credit_card leak"}
        triggered = policy.get_triggered_rules(ctx)
        assert len(triggered) == 2

    def test_get_triggered_rules_respects_disabled(self, deny_exec_rule):
        disabled = deny_exec_rule.with_enabled(False)
        policy = SafetyPolicy(
            id="p4", name="Test", version="1.0",
            description="Test",
            rules=(disabled,),
        )
        ctx = {"action": "run", "code": "os.system('ls')"}
        triggered = policy.get_triggered_rules(ctx)
        assert len(triggered) == 0

    def test_case_insensitive_matching(self, policy):
        ctx = {"action": "run", "code": "OS.SYSTEM('ls')"}
        triggered = policy.get_triggered_rules(ctx)
        assert len(triggered) == 1
        assert triggered[0].id == "r1"

    def test_with_rule_adds_new_rule(self, policy):
        new_rule = PolicyRule(
            id="r4", name="Quarantine", description="Quarantine suspect",
            condition="suspicious", verdict=PolicyVerdict.QUARANTINE, priority=15,
        )
        updated = policy.with_rule(new_rule)
        assert len(updated.rules) == 4
        assert updated.rules[1].id == "r4"  # Sorted by priority: r1(10), r4(15), r2(20), r3(30)

    def test_with_rule_replaces_existing(self, policy):
        replacement = PolicyRule(
            id="r1", name="No Exec v2", description="Block code execution v2",
            condition="os.system", verdict=PolicyVerdict.QUARANTINE, priority=5,
        )
        updated = policy.with_rule(replacement)
        assert len(updated.rules) == 3
        assert updated.rules[0].id == "r1"
        assert updated.rules[0].verdict == PolicyVerdict.QUARANTINE
        assert updated.rules[0].priority == 5

    def test_without_rule_removes_rule(self, policy):
        updated = policy.without_rule("r1")
        assert len(updated.rules) == 2
        assert all(r.id != "r1" for r in updated.rules)

    def test_without_rule_missing_id(self, policy):
        updated = policy.without_rule("nonexistent")
        assert len(updated.rules) == 3

    def test_policy_is_frozen(self, policy):
        with pytest.raises(Exception):  # noqa: B017
            policy.enabled = False  # type: ignore[misc]

    def test_rules_unpack_from_triggered(self, policy):
        ctx = {"action": "run", "code": "safe_operation only"}
        triggered = policy.get_triggered_rules(ctx)
        assert len(triggered) == 1
        assert triggered[0].verdict == PolicyVerdict.ALLOW

    def test_sorting_by_priority_in_triggered(self):
        r_high = PolicyRule(
            id="h", name="High", description="High priority",
            condition="critical", verdict=PolicyVerdict.DENY, priority=1,
        )
        r_low = PolicyRule(
            id="l", name="Low", description="Low priority",
            condition="critical", verdict=PolicyVerdict.FLAG, priority=99,
        )
        policy = SafetyPolicy(
            id="ps", name="Sort", version="1.0",
            description="Priority sort test", rules=(r_low, r_high),
        )
        ctx = {"action": "test", "data": "critical issue"}
        # Both triggered, evaluate picks lowest priority number
        verdict = policy.evaluate(ctx)
        assert verdict == PolicyVerdict.DENY


# ═══════════════════════════════════════════════════════════════════════════════
# PolicyEngine
# ═══════════════════════════════════════════════════════════════════════════════


class TestPolicyEngine:
    @pytest.fixture
    def engine(self):
        eng = PolicyEngine()
        policy = SafetyPolicy(
            id="p1", name="Code Safety", version="1.0",
            description="Standard safety policy",
            rules=(
                PolicyRule(
                    id="r1", name="No Exec", description="Block exec",
                    condition="os.system", verdict=PolicyVerdict.DENY, priority=10,
                ),
                PolicyRule(
                    id="r2", name="Flag PII", description="Flag PII",
                    condition="credit_card", verdict=PolicyVerdict.FLAG, priority=20,
                ),
            ),
        )
        eng.register_policy(policy)
        return eng

    def test_register_policy(self, engine):
        assert engine.policy_count == 1

    def test_register_multiple_policies(self, engine):
        p2 = SafetyPolicy(
            id="p2", name="GDPR", version="1.0",
            description="GDPR compliance", rules=(),
        )
        engine.register_policy(p2)
        assert engine.policy_count == 2

    def test_unregister_policy(self, engine):
        assert engine.unregister_policy("p1") is True
        assert engine.policy_count == 0

    def test_unregister_missing_policy(self, engine):
        assert engine.unregister_policy("nonexistent") is False

    def test_evaluate_allow_when_no_match(self, engine):
        verdict = engine.evaluate("read", {"code": "hello world"})
        assert verdict == PolicyVerdict.FLAG

    def test_evaluate_deny_on_match(self, engine):
        verdict = engine.evaluate("run", {"code": "os.system('rm -rf /')"})
        assert verdict == PolicyVerdict.DENY

    def test_evaluate_all_returns_per_policy(self, engine):
        p2 = SafetyPolicy(
            id="p2", name="Secondary", version="1.0",
            description="Secondary policy", rules=(),
        )
        engine.register_policy(p2)
        results = engine.evaluate_all("run", {"code": "os.system('ls')"})
        assert "p1" in results
        assert "p2" in results
        assert results["p1"] == PolicyVerdict.DENY
        assert results["p2"] == PolicyVerdict.FLAG

    def test_get_effective_verdict_deny_wins(self, engine):
        verdicts = {"p1": PolicyVerdict.FLAG, "p2": PolicyVerdict.DENY}
        assert engine.get_effective_verdict(verdicts) == PolicyVerdict.DENY

    def test_get_effective_verdict_quarantine_over_escalate(self):
        engine = PolicyEngine()
        verdicts = {"p1": PolicyVerdict.ESCALATE, "p2": PolicyVerdict.QUARANTINE}
        assert engine.get_effective_verdict(verdicts) == PolicyVerdict.QUARANTINE

    def test_get_effective_verdict_empty_returns_allow(self):
        engine = PolicyEngine()
        assert engine.get_effective_verdict({}) == PolicyVerdict.ALLOW

    def test_get_effective_verdict_escalate_over_flag(self):
        engine = PolicyEngine()
        verdicts = {"p1": PolicyVerdict.FLAG, "p2": PolicyVerdict.ESCALATE}
        assert engine.get_effective_verdict(verdicts) == PolicyVerdict.ESCALATE

    def test_strict_mode_any_non_allow_becomes_deny(self):
        engine = PolicyEngine(strict_mode=True)
        verdicts = {"p1": PolicyVerdict.FLAG, "p2": PolicyVerdict.ALLOW}
        assert engine.get_effective_verdict(verdicts) == PolicyVerdict.DENY

    def test_strict_mode_all_allow(self):
        engine = PolicyEngine(strict_mode=True)
        verdicts = {"p1": PolicyVerdict.ALLOW}
        assert engine.get_effective_verdict(verdicts) == PolicyVerdict.ALLOW

    def test_get_policy(self, engine):
        policy = engine.get_policy("p1")
        assert policy is not None
        assert policy.name == "Code Safety"

    def test_get_policy_missing(self, engine):
        assert engine.get_policy("nonexistent") is None

    def test_list_policies(self, engine):
        policies = engine.list_policies()
        assert len(policies) == 1
        assert policies[0].id == "p1"

    def test_disabled_policy_not_evaluated(self, engine):
        assert engine.get_policy("p1").enabled is True
        # Register a disabled policy
        disabled = SafetyPolicy(
            id="p2", name="Disabled", version="1.0",
            description="Disabled policy", rules=(),
            enabled=False,
        )
        engine.register_policy(disabled)
        results = engine.evaluate_all("run", {"code": "safe"})
        assert "p2" not in results


# ═══════════════════════════════════════════════════════════════════════════════
# OverrideRequest
# ═══════════════════════════════════════════════════════════════════════════════


class TestOverrideRequest:
    @pytest.fixture
    def override_req(self):
        return OverrideRequest(
            id="or1", policy_id="p1", rule_id="r1",
            requested_by="alice", reason="Emergency hotfix",
            override_verdict=PolicyVerdict.ALLOW,
        )

    def test_create_request(self, override_req):
        assert override_req.id == "or1"
        assert override_req.policy_id == "p1"
        assert override_req.status == "pending"
        assert override_req.approved_by == ""

    def test_approve(self, override_req):
        approved = override_req.approve("bob")
        assert approved.status == "approved"
        assert approved.approved_by == "bob"
        assert approved.resolved_at is not None
        assert override_req.status == "pending"  # Original unchanged

    def test_deny(self, override_req):
        denied = override_req.deny("bob", "Too risky")
        assert denied.status == "denied"
        assert denied.approved_by == "bob"
        assert "Too risky" in denied.reason

    def test_deny_without_reason(self, override_req):
        denied = override_req.deny("bob")
        assert denied.status == "denied"
        assert "Denied:" not in denied.reason

    def test_expires_at_default_none(self, override_req):
        assert override_req.expires_at is None

    def test_with_expires_at(self):
        expiry = time.time() + 3600
        req = OverrideRequest(
            id="or2", policy_id="p2", rule_id="r2",
            requested_by="carol", reason="Maintenance window",
            override_verdict=PolicyVerdict.ALLOW, expires_at=expiry,
        )
        assert req.expires_at == expiry

    def test_request_is_frozen(self):
        req = OverrideRequest(
            id="or3", policy_id="p3", rule_id="r3",
            requested_by="dave", reason="Test",
            override_verdict=PolicyVerdict.ALLOW,
        )
        with pytest.raises(Exception):  # noqa: B017
            req.status = "approved"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# OverrideWorkflow
# ═══════════════════════════════════════════════════════════════════════════════


class TestOverrideWorkflow:
    @pytest.fixture
    def workflow(self):
        return OverrideWorkflow()

    @pytest.fixture
    def pending_request(self):
        return OverrideRequest(
            id="or1", policy_id="p1", rule_id="r1",
            requested_by="alice", reason="Emergency fix",
            override_verdict=PolicyVerdict.ALLOW,
        )

    def test_submit(self, workflow, pending_request):
        result = workflow.submit(pending_request)
        assert result.id == "or1"
        assert workflow.pending_count == 1

    def test_approve(self, workflow, pending_request):
        workflow.submit(pending_request)
        approved = workflow.approve("or1", "bob")
        assert approved.status == "approved"
        assert workflow.pending_count == 0

    def test_approve_missing_raises(self, workflow):
        with pytest.raises(KeyError, match="not found"):
            workflow.approve("nonexistent", "bob")

    def test_deny(self, workflow, pending_request):
        workflow.submit(pending_request)
        denied = workflow.deny("or1", "bob", "Not allowed")
        assert denied.status == "denied"
        assert workflow.pending_count == 0

    def test_deny_missing_raises(self, workflow):
        with pytest.raises(KeyError, match="not found"):
            workflow.deny("nonexistent", "bob")

    def test_get_pending(self, workflow, pending_request):
        workflow.submit(pending_request)
        pending = workflow.get_pending()
        assert len(pending) == 1

    def test_get_pending_excludes_approved(self, workflow, pending_request):
        workflow.submit(pending_request)
        workflow.approve("or1", "bob")
        assert len(workflow.get_pending()) == 0

    def test_get_expired(self, workflow):
        past = time.time() - 3600
        expired_req = OverrideRequest(
            id="or_exp", policy_id="p1", rule_id="r1",
            requested_by="alice", reason="Old request",
            override_verdict=PolicyVerdict.ALLOW, expires_at=past,
        )
        workflow.submit(expired_req)
        expired = workflow.get_expired()
        assert len(expired) == 1
        assert expired[0].id == "or_exp"

    def test_expire_stale(self, workflow):
        past = time.time() - 3600
        expired_req = OverrideRequest(
            id="or_exp", policy_id="p1", rule_id="r1",
            requested_by="alice", reason="Old request",
            override_verdict=PolicyVerdict.ALLOW, expires_at=past,
        )
        workflow.submit(expired_req)
        count = workflow.expire_stale()
        assert count == 1
        assert workflow._requests["or_exp"].status == "expired"

    def test_expire_stale_ignores_future(self, workflow):
        future = time.time() + 86400
        future_req = OverrideRequest(
            id="or_future", policy_id="p1", rule_id="r1",
            requested_by="alice", reason="Future request",
            override_verdict=PolicyVerdict.ALLOW, expires_at=future,
        )
        workflow.submit(future_req)
        count = workflow.expire_stale()
        assert count == 0

    def test_max_capacity_evicts_oldest(self):
        wf = OverrideWorkflow(max_pending=3)
        for i in range(3):
            wf.submit(OverrideRequest(
                id=f"or{i}", policy_id="p1", rule_id="r1",
                requested_by="user", reason=f"Request {i}",
                override_verdict=PolicyVerdict.ALLOW,
            ))
        assert wf.pending_count == 3
        # Add one more — oldest (or0) should be evicted
        wf.submit(OverrideRequest(
            id="or3", policy_id="p1", rule_id="r1",
            requested_by="user", reason="Request 3",
            override_verdict=PolicyVerdict.ALLOW,
        ))
        assert wf.pending_count == 3
        assert "or0" not in wf._requests

    def test_default_max_pending_is_20(self):
        wf = OverrideWorkflow()
        assert wf.max_pending == 20

    def test_default_require_second_approver(self):
        wf = OverrideWorkflow()
        assert wf.require_second_approver is True


# ═══════════════════════════════════════════════════════════════════════════════
# ComplianceFramework
# ═══════════════════════════════════════════════════════════════════════════════


class TestComplianceFramework:
    def test_framework_values(self):
        assert ComplianceFramework.SOC2.value == "soc2"
        assert ComplianceFramework.GDPR.value == "gdpr"
        assert ComplianceFramework.HIPAA.value == "hipaa"
        assert ComplianceFramework.PCI_DSS.value == "pci_dss"
        assert ComplianceFramework.ISO_27001.value == "iso_27001"
        assert ComplianceFramework.CCPA.value == "ccpa"
        assert ComplianceFramework.CUSTOM.value == "custom"

    def test_framework_is_str_enum(self):
        assert isinstance(ComplianceFramework.SOC2, str)


# ═══════════════════════════════════════════════════════════════════════════════
# ComplianceMapper
# ═══════════════════════════════════════════════════════════════════════════════


class TestComplianceMapper:
    @pytest.fixture
    def mapper(self):
        m = ComplianceMapper()
        m.map_policy("p1", (ComplianceFramework.SOC2, ComplianceFramework.GDPR))
        m.map_policy("p2", (ComplianceFramework.GDPR,))
        m.map_policy("p3", (ComplianceFramework.HIPAA, ComplianceFramework.PCI_DSS))
        return m

    def test_map_policy(self, mapper):
        frameworks = mapper.get_frameworks("p1")
        assert ComplianceFramework.SOC2 in frameworks
        assert ComplianceFramework.GDPR in frameworks

    def test_get_frameworks_missing(self, mapper):
        assert mapper.get_frameworks("nonexistent") == ()

    def test_get_policies_for_framework(self, mapper):
        gdpr_policies = mapper.get_policies_for_framework(ComplianceFramework.GDPR)
        assert set(gdpr_policies) == {"p1", "p2"}

    def test_get_policies_for_framework_none(self, mapper):
        iso_policies = mapper.get_policies_for_framework(ComplianceFramework.ISO_27001)
        assert iso_policies == ()

    def test_generate_report(self, mapper):
        report = mapper.generate_report(ComplianceFramework.GDPR)
        assert report["framework"] == "gdpr"
        assert report["policies_mapped"] == 2
        assert report["coverage_pct"] == pytest.approx(100.0 * 2 / 3)

    def test_generate_report_empty(self):
        mapper = ComplianceMapper()
        report = mapper.generate_report(ComplianceFramework.SOC2)
        assert report["policies_mapped"] == 0
        assert report["coverage_pct"] == 0.0

    def test_coverage_gap_analysis(self, mapper):
        gaps = mapper.coverage_gap_analysis(ComplianceFramework.HIPAA)
        assert "p1" in gaps
        assert "p2" in gaps
        assert "p3" not in gaps

    def test_coverage_gap_analysis_no_gaps(self, mapper):
        mapper.map_policy("p1", (ComplianceFramework.GDPR, ComplianceFramework.HIPAA))
        mapper.map_policy("p2", (ComplianceFramework.GDPR, ComplianceFramework.HIPAA))
        mapper.map_policy("p3", (ComplianceFramework.GDPR, ComplianceFramework.HIPAA))
        gaps = mapper.coverage_gap_analysis(ComplianceFramework.HIPAA)
        assert gaps == []

    def test_frameworks_covered(self, mapper):
        covered = mapper.frameworks_covered
        assert ComplianceFramework.SOC2 in covered
        assert ComplianceFramework.GDPR in covered
        assert ComplianceFramework.HIPAA in covered
        assert ComplianceFramework.PCI_DSS in covered
        assert len(covered) == 4

    def test_frameworks_covered_empty(self):
        mapper = ComplianceMapper()
        assert mapper.frameworks_covered == ()

    def test_overwrite_mapping(self, mapper):
        mapper.map_policy("p1", (ComplianceFramework.CCPA,))
        frameworks = mapper.get_frameworks("p1")
        assert frameworks == (ComplianceFramework.CCPA,)
