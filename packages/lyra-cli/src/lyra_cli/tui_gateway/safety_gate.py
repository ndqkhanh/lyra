"""Safety gate — integrates Parallax COS into the TUI gateway.

Every agent action flows through this gate:
  1. AdversarialValidator — detects prompt injection / exfiltration
  2. InfoFlowController — taint tracking, prevents cross-source leaks
  3. ContainmentEngine — escape prevention, quarantine, capability bounding
  4. AdaptiveGovernor — dynamic privilege based on trust
  5. CognitiveExecutiveGate — mandatory reasoning->execution separation
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from typing import Any

from lyra_parallax import (
    ActionCategory,
    ActionProposal,
    AdaptiveGovernor,
    AdversarialValidator,
    ApprovalDecision,
    CognitiveExecutiveGate,
    ContainmentEngine,
    ExecutionPolicy,
    InfoFlowController,
    RiskLevel,
    TaintSource,
)


@dataclass
class SafetyStatus:
    governance_tier: str
    trust_score: float
    containment_active: bool
    quarantine_active: bool
    tainted_count: int
    blocked_flows: int
    escape_signals: int
    self_modify_attempts: int
    violation_count: int
    action_count: int


class SafetyGate:
    """Thread-safe safety gate wrapping all Parallax components."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._validator = AdversarialValidator()
        self._flow = InfoFlowController()
        self._containment = ContainmentEngine()
        self._governor = AdaptiveGovernor(initial_tier="observer")

        policy = ExecutionPolicy(
            name="lyra-gateway",
            allowed_categories=(
                ActionCategory.READ,
                ActionCategory.WRITE,
                ActionCategory.EXECUTE,
                ActionCategory.NETWORK,
            ),
            denied_categories=(ActionCategory.DELETE, ActionCategory.SELF_MODIFY),
            max_risk_level=RiskLevel.MEDIUM,
            require_human_for=(ActionCategory.SELF_MODIFY,),
            rate_limit_per_minute=60,
        )
        self._gate = CognitiveExecutiveGate(policy=policy)
        self._review_log: list[dict[str, Any]] = []

        # Register flow rules for safe read/write operations
        self._flow.mark_tainted("__init__", TaintSource.USER_INPUT)
        # Add flow rules via internal API for READ and WRITE
        from lyra_parallax.models import InfoFlowRule
        for cat in (ActionCategory.READ, ActionCategory.WRITE):
            self._flow._rules.append(InfoFlowRule(
                source=TaintSource.USER_INPUT, destination_category=cat, allowed=True,
            ))
            self._flow._rules.append(InfoFlowRule(
                source=TaintSource.FILE_SYSTEM, destination_category=cat, allowed=True,
            ))

    def _make_proposal(self, action_text: str, category: ActionCategory) -> ActionProposal:
        return ActionProposal(
            id=uuid.uuid4().hex[:12],
            category=category,
            description=action_text[:200],
            target="gateway-action",
            risk_level=RiskLevel.MEDIUM,
        )

    # ── main entry: validate every proposed action ─────────────────

    def validate_action(
        self,
        action_text: str,
        category: ActionCategory = ActionCategory.EXECUTE,
        taint_source: TaintSource = TaintSource.USER_INPUT,
    ) -> ApprovalDecision:
        """Validate a proposed action through all safety layers."""
        with self._lock:
            proposal = self._make_proposal(action_text, category)

            # Layer 1: adversarial validation
            adv_decision = self._validator.validate(proposal)
            if adv_decision != ApprovalDecision.ALLOW:
                self._review_log.append({
                    "layer": "adversarial",
                    "decision": adv_decision.value,
                    "action": action_text[:200],
                })
                return adv_decision

            # Layer 2: containment — detect escape signals
            self._containment.detect_escape_signal(action_text)
            if self._containment.state.quarantine_active:
                self._review_log.append({
                    "layer": "containment",
                    "decision": "deny",
                    "action": action_text[:200],
                })
                return ApprovalDecision.DENY

            # Layer 2b: capability bounds check
            cap_decision = self._containment.check_capability_bounds(proposal)
            if cap_decision != ApprovalDecision.ALLOW:
                self._review_log.append({
                    "layer": "containment_capability",
                    "decision": cap_decision.value,
                    "action": action_text[:200],
                })
                return cap_decision

            # Layer 2c: network egress check
            net_decision = self._containment.check_network_egress(proposal)
            if net_decision != ApprovalDecision.ALLOW:
                self._review_log.append({
                    "layer": "containment_network",
                    "decision": net_decision.value,
                    "action": action_text[:200],
                })
                return net_decision

            # Layer 3: info flow control
            flow_decision = self._flow.check_flow(taint_source, proposal)
            if flow_decision != ApprovalDecision.ALLOW:
                self._review_log.append({
                    "layer": "flow_control",
                    "decision": flow_decision.value,
                    "action": action_text[:200],
                })
                return flow_decision

            # Layer 4: governance tier
            gov_decision = self._governor.evaluate(proposal)
            if gov_decision != ApprovalDecision.ALLOW:
                self._review_log.append({
                    "layer": "governance",
                    "decision": gov_decision.value,
                    "action": action_text[:200],
                })
                return gov_decision

            # Layer 5: cognitive-executive separation gate
            gate_decision = self._gate.review(proposal)
            self._review_log.append({
                "layer": "gate",
                "decision": gate_decision.value,
                "action": action_text[:200],
            })
            return gate_decision

    # ── trust feedback ────────────────────────────────────────────

    def record_success(self) -> None:
        with self._lock:
            self._governor.record_success()

    def record_violation(self) -> None:
        with self._lock:
            self._governor.record_violation()

    # ── taint tracking ────────────────────────────────────────────

    def mark_tainted(self, data_id: str, source: TaintSource) -> None:
        with self._lock:
            self._flow.mark_tainted(data_id, source)

    # ── status snapshot ───────────────────────────────────────────

    def status(self) -> SafetyStatus:
        with self._lock:
            cs = self._containment.state
            return SafetyStatus(
                governance_tier=self._governor.current_tier.name,
                trust_score=round(self._governor.trust_score, 4),
                containment_active=True,
                quarantine_active=cs.quarantine_active,
                tainted_count=self._flow.tainted_count,
                blocked_flows=len(self._flow.blocked_flows),
                escape_signals=cs.escape_signals,
                self_modify_attempts=cs.self_modification_attempts,
                violation_count=self._governor._violation_count,
                action_count=self._governor._action_count,
            )

    # ── reset for new cycle ───────────────────────────────────────

    def reset_cycle(self) -> None:
        with self._lock:
            self._governor.reset_cycle()

    # ── review log ────────────────────────────────────────────────

    @property
    def review_log(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(self._review_log[-100:])

    @property
    def containment_audit(self) -> tuple[str, ...]:
        with self._lock:
            return self._containment.audit_trail
