"""Safety-Enhanced Permission Resolver.

Integrates Lyra's safety governance components (ApprovalGate, ReasoningMonitor,
AlignmentMonitor, AuditEngine, AdversarialVerifier) with the existing permissions
engine to provide comprehensive safety checks before action execution.

Architecture:
    PermissionStack → SafetyEnhancedPermissionResolver → Safety Pipeline:
        1. Risk Classification (ApprovalGate)
        2. Reasoning Pattern Monitoring (ReasoningMonitor)
        3. Approval Gate Evaluation (ApprovalGate)
        4. Adversarial Verification (AdversarialVerifier, if HIGH/CRITICAL)
        5. Audit Logging (AuditLogger)
        6. Alignment Tracking (AlignmentMonitor)
        7. Final Decision

The resolver wraps the existing PermissionStack and adds safety checks while
maintaining backward compatibility with the existing permission system.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from lyra_harness_core.messages import ToolCall

from lyra_core.safety.alignment_monitor import AlignmentMonitor, AlignmentSample
from lyra_core.safety.approval_gate import (
    ApprovalGate,
    GateAction,
    GateDecision,
    ReasoningFlag,
    RiskLevel,
)
from lyra_core.safety.audit_engine import AuditLogger, Decision, Verdict
from lyra_core.safety.reasoning_monitor import (
    ReasoningMonitor,
    ReasoningReport,
)

from .modes import LyraMode
from .resolver import Decision as PermissionDecision
from .stack import PermissionStack, StackInput

try:
    from lyra_core.safety.adversarial_verifier import (
        AdversarialVerdict,
        AdversarialVerdictType,
        AdversarialVerifier,
        VerificationRequest,
    )

    HAS_ADVERSARIAL = True
except ImportError:
    HAS_ADVERSARIAL = False
    AdversarialVerifier = None  # type: ignore
    AdversarialVerdict = None  # type: ignore
    AdversarialVerdictType = None  # type: ignore
    VerificationRequest = None  # type: ignore


@dataclass(frozen=True)
class SafetyDecision:
    """Final safety decision after all checks.

    Attributes:
        allowed: Whether the action is allowed to proceed.
        reason: Human-readable explanation of the decision.
        risk_level: Assessed risk level.
        gate_action: Approval gate action (AUTO/NOTIFY/CONFIRM/BLOCK).
        reasoning_report: Report from reasoning monitor (if run).
        adversarial_verdict: Verdict from adversarial verification (if run).
        audit_record_id: ID of the audit log record.
        alignment_sample_id: ID of the alignment tracking sample.
        requires_human_approval: Whether human approval is required.
        metadata: Additional metadata about the decision.
    """

    allowed: bool
    reason: str
    risk_level: RiskLevel
    gate_action: GateAction
    reasoning_report: ReasoningReport | None = None
    adversarial_verdict: Any = None  # AdversarialVerdict | None
    audit_record_id: str = ""
    alignment_sample_id: str = ""
    requires_human_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Risk Level Mapping ─────────────────────────────────────────────────


def _map_tool_risk_to_risk_level(tool_risk: str) -> RiskLevel:
    """Map tool risk string to RiskLevel enum."""
    mapping = {
        "low": RiskLevel.LOW,
        "medium": RiskLevel.MEDIUM,
        "high": RiskLevel.HIGH,
        "destructive": RiskLevel.CRITICAL,
        "critical": RiskLevel.CRITICAL,
        "unknown": RiskLevel.MEDIUM,
    }
    return mapping.get(tool_risk.lower(), RiskLevel.MEDIUM)


def _map_gate_action_to_permission_decision(gate_action: GateAction) -> PermissionDecision:
    """Map GateAction to Permission Decision."""
    mapping = {
        GateAction.AUTO: PermissionDecision.ALLOW,
        GateAction.NOTIFY: PermissionDecision.ALLOW,
        GateAction.CONFIRM: PermissionDecision.ASK,
        GateAction.BLOCK: PermissionDecision.DENY,
    }
    return mapping[gate_action]


def _map_reasoning_flags_to_approval_flags(
    report: ReasoningReport,
) -> tuple[ReasoningFlag, ...]:
    """Map ReasoningReport flags to ApprovalGate ReasoningFlags."""
    flag_mapping = {
        "deception": ReasoningFlag.DECEPTION,
        "self_deception": ReasoningFlag.SELF_DECEPTION,
        "reward_hacking": ReasoningFlag.REWARD_HACKING,
        "goal_misgeneralization": ReasoningFlag.GOAL_MISGENERALIZATION,
        "power_seeking": ReasoningFlag.POWER_SEEKING,
    }

    flags: list[ReasoningFlag] = []
    for flag in report.flags:
        approval_flag = flag_mapping.get(flag.pattern_type.value)
        if approval_flag:
            flags.append(approval_flag)

    return tuple(flags)


def _map_adversarial_verdict_to_audit_verdict(
    verdict: Any,  # AdversarialVerdict | None
) -> Verdict:
    """Map AdversarialVerdict to Audit Verdict."""
    if not HAS_ADVERSARIAL or verdict is None:
        return Verdict.NOT_PERFORMED

    # Count votes
    approve_count = sum(
        1 for vote in verdict.votes if vote.verdict == AdversarialVerdictType.APPROVE
    )
    deny_count = sum(
        1 for vote in verdict.votes if vote.verdict == AdversarialVerdictType.DENY
    )

    if approve_count == 3:
        return Verdict.UNANIMOUS_APPROVE
    elif deny_count == 3:
        return Verdict.UNANIMOUS_DENY
    elif approve_count == 2:
        return Verdict.MAJORITY_APPROVE
    elif deny_count == 2:
        return Verdict.MAJORITY_DENY
    else:
        return Verdict.SPLIT


# ── Safety-Enhanced Permission Resolver ────────────────────────────────


@dataclass
class SafetyEnhancedPermissionResolver:
    """Permission resolver with integrated safety governance.

    Wraps the existing PermissionStack and adds comprehensive safety checks:
        1. Risk classification via ApprovalGate
        2. Reasoning pattern monitoring via ReasoningMonitor
        3. Approval gate evaluation
        4. Adversarial verification for HIGH/CRITICAL actions
        5. Audit logging via AuditLogger
        6. Alignment tracking via AlignmentMonitor

    Maintains backward compatibility with the existing permission system while
    adding safety governance on top.

    Attributes:
        permission_stack: Existing permission stack for base checks.
        approval_gate: Approval gate for risk classification and routing.
        reasoning_monitor: Monitor for unsafe reasoning patterns.
        audit_logger: Cryptographic audit trail logger.
        alignment_monitor: Alignment drift detector.
        adversarial_verifier: Cross-model adversarial verifier (optional).
        enable_adversarial: Whether to run adversarial verification.
        enable_reasoning_monitor: Whether to run reasoning pattern monitoring.
        enable_alignment_tracking: Whether to track alignment drift.
    """

    permission_stack: PermissionStack
    approval_gate: ApprovalGate
    reasoning_monitor: ReasoningMonitor
    audit_logger: AuditLogger
    alignment_monitor: AlignmentMonitor
    adversarial_verifier: Any = None  # AdversarialVerifier | None
    enable_adversarial: bool = True
    enable_reasoning_monitor: bool = True
    enable_alignment_tracking: bool = True
    _human_approval_handler: Callable[[SafetyDecision], SafetyDecision] | None = None

    def set_human_approval_handler(
        self, handler: Callable[[SafetyDecision], SafetyDecision]
    ) -> None:
        """Register a callback for human approval flows.

        Args:
            handler: Callback that receives a SafetyDecision requiring approval
                and returns the final decision after human review.
        """
        self._human_approval_handler = handler

    async def resolve_permission_async(
        self,
        call: ToolCall,
        *,
        mode: LyraMode = LyraMode.DEFAULT,
        tool_writes: bool = False,
        tool_risk: str = "low",
        reasoning_text: str = "",
        context: str = "",
    ) -> SafetyDecision:
        """Resolve permission with full safety pipeline (async).

        Args:
            call: Tool call to evaluate.
            mode: Current Lyra permission mode.
            tool_writes: Whether the tool performs writes.
            tool_risk: Risk level of the tool (low/medium/high/destructive).
            reasoning_text: Agent's reasoning chain for this action.
            context: Additional context about the action.

        Returns:
            SafetyDecision with the final verdict and all safety check results.
        """
        start_time = time.time()

        # Step 1: Run base permission stack checks
        stack_input = StackInput(
            tool_name=call.name,
            args=call.args,
        )
        stack_decision = self.permission_stack.check(stack_input)

        if stack_decision.block:
            # Base permission check failed - log and return
            audit_record = self.audit_logger.log(
                action_description=f"{call.name}({call.args})",
                risk_level=RiskLevel.CRITICAL,
                reasoning_flags=(),
                adversarial_verdict=Verdict.NOT_PERFORMED,
                final_decision=Decision.DENIED,
                metadata={
                    "guard": stack_decision.guard,
                    "reason": stack_decision.reason,
                    "mode": mode.value,
                },
            )

            return SafetyDecision(
                allowed=False,
                reason=f"Blocked by {stack_decision.guard}: {stack_decision.reason}",
                risk_level=RiskLevel.CRITICAL,
                gate_action=GateAction.BLOCK,
                audit_record_id=audit_record.id,
                metadata={"stack_decision": stack_decision},
            )

        # Step 2: Classify risk via ApprovalGate
        action_description = f"{call.name}({call.args})"
        risk_classification = self.approval_gate.risk_classifier(
            action_description, call.args
        )

        # Step 3: Monitor reasoning patterns (if enabled and reasoning provided)
        reasoning_report: ReasoningReport | None = None
        reasoning_flags: tuple[ReasoningFlag, ...] = ()

        if self.enable_reasoning_monitor and reasoning_text:
            reasoning_report = self.reasoning_monitor.analyze(reasoning_text)
            reasoning_flags = _map_reasoning_flags_to_approval_flags(reasoning_report)

        # Step 4: Evaluate approval gate
        require_adversarial = (
            risk_classification.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
            and self.enable_adversarial
            and self.adversarial_verifier is not None
        )

        gate_decision = self.approval_gate.evaluate(
            action_description=action_description,
            parameters=call.args,
            reasoning_flags=reasoning_flags,
            require_adversarial=require_adversarial,
        )

        # Step 5: Run adversarial verification if needed
        adversarial_verdict: Any = None
        if require_adversarial and HAS_ADVERSARIAL:
            verification_request = VerificationRequest(
                action_description=action_description,
                parameters=call.args,
                risk_classification=gate_decision.risk,
                gate_decision=gate_decision,
                context=context,
            )
            adversarial_verdict = await self.adversarial_verifier.verify(
                verification_request
            )

            # Override gate decision if adversarial verification denies
            if adversarial_verdict.final_verdict == AdversarialVerdictType.DENY:
                gate_decision = GateDecision(
                    action=GateAction.BLOCK,
                    risk=gate_decision.risk,
                    gate_id=gate_decision.gate_id,
                    override_reason="Adversarial verification denied action",
                )
            elif adversarial_verdict.requires_escalation:
                # Escalate to human if adversarial verification is uncertain
                gate_decision = GateDecision(
                    action=GateAction.CONFIRM,
                    risk=gate_decision.risk,
                    gate_id=gate_decision.gate_id,
                    override_reason="Adversarial verification requires escalation",
                )

        # Step 6: Determine final decision
        allowed = gate_decision.action in (GateAction.AUTO, GateAction.NOTIFY)
        requires_human_approval = gate_decision.action == GateAction.CONFIRM

        # Map to audit decision
        if gate_decision.action == GateAction.BLOCK:
            audit_decision = Decision.DENIED
        elif requires_human_approval:
            audit_decision = Decision.ESCALATED
        else:
            audit_decision = Decision.APPROVED

        # Step 7: Log to audit trail
        audit_record = self.audit_logger.log(
            action_description=action_description,
            risk_level=gate_decision.risk.level,
            reasoning_flags=reasoning_flags,
            adversarial_verdict=_map_adversarial_verdict_to_audit_verdict(
                adversarial_verdict
            ),
            final_decision=audit_decision,
            metadata={
                "tool_name": call.name,
                "mode": mode.value,
                "tool_writes": tool_writes,
                "tool_risk": tool_risk,
                "gate_action": gate_decision.action.name,
                "latency_ms": (time.time() - start_time) * 1000,
            },
        )

        # Step 8: Track alignment (if enabled)
        alignment_sample: AlignmentSample | None = None
        if self.enable_alignment_tracking:
            # Infer alignment vector from action metadata
            alignment_vector = self.alignment_monitor.infer_vector_from_action(
                action_type=call.name,
                success=allowed,
                tests_passed=True,  # Unknown at this point
                files_modified=1 if tool_writes else 0,
                errors_encountered=1 if not allowed else 0,
            )
            alignment_sample = self.alignment_monitor.record_action_vector(
                action_vector=alignment_vector,
                action_signature=action_description,
            )

        # Step 9: Build final safety decision
        reason = self._build_decision_reason(
            gate_decision, reasoning_report, adversarial_verdict
        )

        safety_decision = SafetyDecision(
            allowed=allowed,
            reason=reason,
            risk_level=gate_decision.risk.level,
            gate_action=gate_decision.action,
            reasoning_report=reasoning_report,
            adversarial_verdict=adversarial_verdict,
            audit_record_id=audit_record.id,
            alignment_sample_id=alignment_sample.sample_id if alignment_sample else "",
            requires_human_approval=requires_human_approval,
            metadata={
                "gate_decision": gate_decision,
                "stack_decision": stack_decision,
                "latency_ms": (time.time() - start_time) * 1000,
            },
        )

        # Step 10: Handle human approval if needed
        if requires_human_approval and self._human_approval_handler:
            safety_decision = self._human_approval_handler(safety_decision)

        return safety_decision

    def resolve_permission(
        self,
        call: ToolCall,
        *,
        mode: LyraMode = LyraMode.DEFAULT,
        tool_writes: bool = False,
        tool_risk: str = "low",
        reasoning_text: str = "",
        context: str = "",
    ) -> SafetyDecision:
        """Resolve permission with full safety pipeline (sync wrapper).

        Args:
            call: Tool call to evaluate.
            mode: Current Lyra permission mode.
            tool_writes: Whether the tool performs writes.
            tool_risk: Risk level of the tool (low/medium/high/destructive).
            reasoning_text: Agent's reasoning chain for this action.
            context: Additional context about the action.

        Returns:
            SafetyDecision with the final verdict and all safety check results.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, create one
            return asyncio.run(
                self.resolve_permission_async(
                    call,
                    mode=mode,
                    tool_writes=tool_writes,
                    tool_risk=tool_risk,
                    reasoning_text=reasoning_text,
                    context=context,
                )
            )
        else:
            # Event loop already running, use it
            return loop.run_until_complete(
                self.resolve_permission_async(
                    call,
                    mode=mode,
                    tool_writes=tool_writes,
                    tool_risk=tool_risk,
                    reasoning_text=reasoning_text,
                    context=context,
                )
            )

    @staticmethod
    def _build_decision_reason(
        gate_decision: GateDecision,
        reasoning_report: ReasoningReport | None,
        adversarial_verdict: Any,  # AdversarialVerdict | None
    ) -> str:
        """Build human-readable reason for the decision."""
        parts = [
            f"Risk: {gate_decision.risk.level.value} ({gate_decision.risk.surface.value})"
        ]

        if gate_decision.action == GateAction.BLOCK:
            parts.append("Action blocked by approval gate")
        elif gate_decision.action == GateAction.CONFIRM:
            parts.append("Human approval required")
        elif gate_decision.action == GateAction.NOTIFY:
            parts.append("Action allowed with notification")
        else:
            parts.append("Action auto-approved")

        if reasoning_report and reasoning_report.flags:
            parts.append(
                f"Reasoning flags: {len(reasoning_report.flags)} detected "
                f"({reasoning_report.critical_count} critical)"
            )

        if adversarial_verdict and HAS_ADVERSARIAL:
            parts.append(
                f"Adversarial: {adversarial_verdict.final_verdict.value} "
                f"(consensus: {adversarial_verdict.consensus_level:.2f})"
            )

        if gate_decision.override_reason:
            parts.append(f"Override: {gate_decision.override_reason}")

        return " | ".join(parts)

    def get_alignment_drift_report(self) -> Any:
        """Get current alignment drift report."""
        return self.alignment_monitor.check_drift()

    def verify_audit_chain(self) -> tuple[bool, list[str]]:
        """Verify integrity of the audit chain."""
        return self.audit_logger.verify_chain()


__all__ = [
    "SafetyDecision",
    "SafetyEnhancedPermissionResolver",
]
