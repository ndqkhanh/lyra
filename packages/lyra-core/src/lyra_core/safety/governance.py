"""Safety governance — formal policy management and compliance mapping.

Adds a formal governance layer on top of the existing 19 safety modules.
Where the current safety modules handle detection and response, this layer
adds policy management, structured override workflows, compliance framework
mapping, and the policy-decision-audit loop.

Integrates with ``ApprovalGate``, ``AuditLogger``, and ``IncidentResponse``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ── Policy Verdict ────────────────────────────────────────────────────────────


class PolicyVerdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    FLAG = "flag"
    ESCALATE = "escalate"
    QUARANTINE = "quarantine"


# ── Policy Rule ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PolicyRule:
    """A single rule within a safety policy."""

    id: str
    name: str
    description: str
    condition: str
    verdict: PolicyVerdict
    priority: int = 50
    enabled: bool = True
    auto_remediation: str = ""
    tags: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()

    def with_enabled(self, enabled: bool) -> PolicyRule:
        return PolicyRule(
            id=self.id, name=self.name, description=self.description,
            condition=self.condition, verdict=self.verdict,
            priority=self.priority, enabled=enabled,
            auto_remediation=self.auto_remediation, tags=self.tags,
            frameworks=self.frameworks,
        )


# ── Safety Policy ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SafetyPolicy:
    """A named collection of rules forming a governance policy."""

    id: str
    name: str
    version: str
    description: str
    rules: tuple[PolicyRule, ...]
    default_verdict: PolicyVerdict = PolicyVerdict.FLAG
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def evaluate(self, context: dict[str, Any]) -> PolicyVerdict:
        """Evaluate this policy against an action context."""
        triggered = self.get_triggered_rules(context)
        if not triggered:
            return self.default_verdict
        # Highest priority (lowest number) wins among triggered rules
        worst = min(triggered, key=lambda r: r.priority)
        return worst.verdict

    def get_triggered_rules(self, context: dict[str, Any]) -> tuple[PolicyRule, ...]:
        """Return rules whose conditions match the given context."""
        triggered: list[PolicyRule] = []
        ctx_str = " ".join(str(v).lower() for v in context.values())
        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.condition.lower() in ctx_str:
                triggered.append(rule)
        return tuple(triggered)

    def with_rule(self, rule: PolicyRule) -> SafetyPolicy:
        """Return a NEW policy with an additional rule (immutable)."""
        existing = [r for r in self.rules if r.id != rule.id]
        return SafetyPolicy(
            id=self.id, name=self.name, version=self.version,
            description=self.description,
            rules=tuple(sorted(existing + [rule], key=lambda r: r.priority)),
            default_verdict=self.default_verdict, enabled=self.enabled,
            created_at=self.created_at, updated_at=time.time(),
        )

    def without_rule(self, rule_id: str) -> SafetyPolicy:
        """Return a NEW policy without the specified rule (immutable)."""
        return SafetyPolicy(
            id=self.id, name=self.name, version=self.version,
            description=self.description,
            rules=tuple(r for r in self.rules if r.id != rule_id),
            default_verdict=self.default_verdict, enabled=self.enabled,
            created_at=self.created_at, updated_at=time.time(),
        )


# ── Policy Engine ─────────────────────────────────────────────────────────────


@dataclass
class PolicyEngine:
    """Central engine that evaluates policies against actions.

    Usage::

        engine = PolicyEngine()
        engine.register_policy(SafetyPolicy(id="p1", name="Code Safety", ...))
        verdict = engine.evaluate("run_code", {"code": "os.system('rm -rf /')"})
    """

    strict_mode: bool = False
    _policies: dict[str, SafetyPolicy] = field(default_factory=dict)

    def register_policy(self, policy: SafetyPolicy) -> None:
        self._policies[policy.id] = policy

    def unregister_policy(self, policy_id: str) -> bool:
        return self._policies.pop(policy_id, None) is not None

    def evaluate(self, action: str, context: dict[str, Any]) -> PolicyVerdict:
        """Evaluate an action against all registered policies."""
        context["action"] = action
        verdicts = self.evaluate_all(action, context)
        return self.get_effective_verdict(verdicts)

    def evaluate_all(self, action: str, context: dict[str, Any]) -> dict[str, PolicyVerdict]:
        """Evaluate against all policies returning per-policy verdicts."""
        context["action"] = action
        result: dict[str, PolicyVerdict] = {}
        for policy in self._policies.values():
            if policy.enabled:
                result[policy.id] = policy.evaluate(context)
        return result

    def get_effective_verdict(self, verdicts: dict[str, PolicyVerdict]) -> PolicyVerdict:
        """Combine multiple policy verdicts into a single effective verdict.

        Priority: DENY > QUARANTINE > ESCALATE > FLAG > ALLOW
        In strict mode, any non-ALLOW blocks.
        """
        if not verdicts:
            return PolicyVerdict.ALLOW

        severity_order = (
            PolicyVerdict.DENY,
            PolicyVerdict.QUARANTINE,
            PolicyVerdict.ESCALATE,
            PolicyVerdict.FLAG,
            PolicyVerdict.ALLOW,
        )

        for sev in severity_order:
            if sev in verdicts.values():
                if self.strict_mode and sev != PolicyVerdict.ALLOW:
                    return PolicyVerdict.DENY
                return sev

        return PolicyVerdict.ALLOW

    def get_policy(self, policy_id: str) -> SafetyPolicy | None:
        return self._policies.get(policy_id)

    def list_policies(self) -> tuple[SafetyPolicy, ...]:
        return tuple(self._policies.values())

    @property
    def policy_count(self) -> int:
        return len(self._policies)


# ── Override Request ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OverrideRequest:
    """A formal request to override a policy decision."""

    id: str
    policy_id: str
    rule_id: str
    requested_by: str
    reason: str
    override_verdict: PolicyVerdict
    status: str = "pending"
    approved_by: str = ""
    expires_at: float | None = None
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None

    def approve(self, approver: str) -> OverrideRequest:
        return OverrideRequest(
            id=self.id, policy_id=self.policy_id, rule_id=self.rule_id,
            requested_by=self.requested_by, reason=self.reason,
            override_verdict=self.override_verdict, status="approved",
            approved_by=approver, expires_at=self.expires_at,
            created_at=self.created_at, resolved_at=time.time(),
        )

    def deny(self, approver: str, denial_reason: str = "") -> OverrideRequest:
        return OverrideRequest(
            id=self.id, policy_id=self.policy_id, rule_id=self.rule_id,
            requested_by=self.requested_by,
            reason=self.reason + f" | Denied: {denial_reason}" if denial_reason else self.reason,
            override_verdict=self.override_verdict, status="denied",
            approved_by=approver, expires_at=self.expires_at,
            created_at=self.created_at, resolved_at=time.time(),
        )


# ── Override Workflow ─────────────────────────────────────────────────────────


@dataclass
class OverrideWorkflow:
    """Manages the lifecycle of policy overrides.

    Usage::

        wf = OverrideWorkflow()
        req = wf.submit(OverrideRequest(...))
        wf.approve(req.id, "security_reviewer")
    """

    max_pending: int = 20
    auto_expire_hours: float = 24.0
    require_second_approver: bool = True
    _requests: dict[str, OverrideRequest] = field(default_factory=dict)

    def submit(self, request: OverrideRequest) -> OverrideRequest:
        """Submit a new override request. Evicts oldest if at capacity."""
        if len(self._requests) >= self.max_pending:
            oldest = min(
                self._requests.values(), key=lambda r: r.created_at
            )
            del self._requests[oldest.id]
        self._requests[request.id] = request
        return request

    def approve(self, request_id: str, approver: str) -> OverrideRequest:
        """Approve a pending override request."""
        req = self._requests.get(request_id)
        if req is None:
            raise KeyError(f"Override request '{request_id}' not found")
        updated = req.approve(approver)
        self._requests[request_id] = updated
        return updated

    def deny(self, request_id: str, approver: str, reason: str = "") -> OverrideRequest:
        """Deny a pending override request."""
        req = self._requests.get(request_id)
        if req is None:
            raise KeyError(f"Override request '{request_id}' not found")
        updated = req.deny(approver, reason)
        self._requests[request_id] = updated
        return updated

    def get_pending(self) -> tuple[OverrideRequest, ...]:
        return tuple(r for r in self._requests.values() if r.status == "pending")

    def get_expired(self) -> tuple[OverrideRequest, ...]:
        now = time.time()
        return tuple(
            r for r in self._requests.values()
            if r.expires_at is not None and r.expires_at < now
        )

    def expire_stale(self) -> int:
        """Expire all stale override requests. Returns count expired."""
        now = time.time()
        expired_count = 0
        for req_id, req in list(self._requests.items()):
            if req.expires_at is not None and req.expires_at < now:
                self._requests[req_id] = OverrideRequest(
                    id=req.id, policy_id=req.policy_id, rule_id=req.rule_id,
                    requested_by=req.requested_by, reason=req.reason,
                    override_verdict=req.override_verdict, status="expired",
                    approved_by=req.approved_by, expires_at=req.expires_at,
                    created_at=req.created_at, resolved_at=now,
                )
                expired_count += 1
        return expired_count

    @property
    def pending_count(self) -> int:
        return len(self.get_pending())


# ── Compliance Frameworks ─────────────────────────────────────────────────────


class ComplianceFramework(str, Enum):
    SOC2 = "soc2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    CCPA = "ccpa"
    CUSTOM = "custom"


# ── Compliance Mapper ─────────────────────────────────────────────────────────


@dataclass
class ComplianceMapper:
    """Maps policies to compliance frameworks and generates reports.

    Usage::

        mapper = ComplianceMapper()
        mapper.map_policy("p1", [ComplianceFramework.SOC2, ComplianceFramework.GDPR])
        report = mapper.generate_report(ComplianceFramework.SOC2)
    """

    _mappings: dict[str, tuple[ComplianceFramework, ...]] = field(default_factory=dict)

    def map_policy(self, policy_id: str,
                   frameworks: tuple[ComplianceFramework, ...]) -> None:
        self._mappings[policy_id] = frameworks

    def get_frameworks(self, policy_id: str) -> tuple[ComplianceFramework, ...]:
        return self._mappings.get(policy_id, ())

    def get_policies_for_framework(self,
                                   framework: ComplianceFramework) -> tuple[str, ...]:
        return tuple(
            pid for pid, fws in self._mappings.items() if framework in fws
        )

    def generate_report(self, framework: ComplianceFramework) -> dict[str, Any]:
        """Generate a compliance report for a framework."""
        mapped = self.get_policies_for_framework(framework)
        return {
            "framework": framework.value,
            "policies_mapped": len(mapped),
            "policy_ids": list(mapped),
            "coverage_pct": min(len(mapped) / max(len(self._mappings), 1) * 100, 100.0),
        }

    def coverage_gap_analysis(self, framework: ComplianceFramework) -> list[str]:
        """Return policy IDs NOT mapped to this framework."""
        mapped = set(self.get_policies_for_framework(framework))
        return [pid for pid in self._mappings if pid not in mapped]

    @property
    def frameworks_covered(self) -> tuple[ComplianceFramework, ...]:
        seen: set[ComplianceFramework] = set()
        for fws in self._mappings.values():
            seen.update(fws)
        return tuple(sorted(seen, key=lambda f: f.value))
