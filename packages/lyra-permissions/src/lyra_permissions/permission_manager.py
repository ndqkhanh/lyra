"""
Permission Manager - Central permission registry and decision engine.

Features:
- Risk assessment
- Permission checking
- Policy application
- Context-aware decisions
- Bypass mode integration
"""

from dataclasses import dataclass
from typing import Any

from lyra_permissions.bypass_mode import AuditLogger, BypassMode, SafetyGuardrails
from lyra_permissions.granular_control import GranularController, TimeBasedController
from lyra_permissions.permission_policy import PolicyEngine
from lyra_permissions.permission_store import PermissionStore
from lyra_permissions.types import (
    PermissionDecision,
    PermissionLevel,
    PermissionPolicy,
)


@dataclass
class PermissionResult:
    """Permission check result."""

    decision: PermissionDecision
    level: PermissionLevel
    reason: str
    allow: bool


class PermissionManager:
    """
    Central permission management system.

    Features:
    - Risk assessment
    - Permission checking
    - Policy application
    """

    def __init__(self, policy: PermissionPolicy = PermissionPolicy.BALANCED):
        """Initialize permission manager."""
        self.policy_engine = PolicyEngine(policy)
        self.store = PermissionStore()
        self.bypass_mode = BypassMode()
        self.audit_logger = AuditLogger()
        self.granular_controller = GranularController()
        self.time_controller = TimeBasedController()

    def check_permission(
        self, tool: str, operation: str, context: dict[str, Any] | None = None
    ) -> PermissionResult:
        """
        Check if operation is allowed.

        Args:
            tool: Tool name
            operation: Operation name
            context: Operation context

        Returns:
            Permission result
        """
        context = context or {}

        # Assess risk level
        risk_level = self.assess_risk(tool, operation, context)

        # CRITICAL operations always require confirmation (even in bypass mode)
        if risk_level == PermissionLevel.CRITICAL or SafetyGuardrails.requires_confirmation(
            tool, operation, context
        ):
            result = PermissionResult(
                decision=PermissionDecision.PROMPT,
                level=risk_level,
                reason="Critical operation requires confirmation",
                allow=False,
            )
            self.audit_logger.log(tool, operation, result.decision, risk_level, context)
            return result

        # Check time-based rules
        time_decision = self.time_controller.check_time_rules()
        if time_decision:
            result = PermissionResult(
                decision=time_decision,
                level=risk_level,
                reason=f"Time-based rule: {time_decision.value}",
                allow=time_decision == PermissionDecision.ALLOW,
            )
            self.audit_logger.log(tool, operation, result.decision, risk_level, context)
            return result

        # Check context rules
        context_decision = self.granular_controller.check_context_rules(context)
        if context_decision:
            result = PermissionResult(
                decision=context_decision,
                level=risk_level,
                reason=f"Context rule: {context_decision.value}",
                allow=context_decision == PermissionDecision.ALLOW,
            )
            self.audit_logger.log(tool, operation, result.decision, risk_level, context)
            return result

        # Check tool-specific permissions
        tool_decision = self.granular_controller.check_tool_permission(tool, operation, risk_level)
        if tool_decision:
            result = PermissionResult(
                decision=tool_decision,
                level=risk_level,
                reason=f"Tool permission: {tool_decision.value}",
                allow=tool_decision == PermissionDecision.ALLOW,
            )
            self.audit_logger.log(tool, operation, result.decision, risk_level, context)
            return result

        # Check bypass mode
        if self.bypass_mode.is_enabled():
            result = PermissionResult(
                decision=PermissionDecision.ALLOW,
                level=risk_level,
                reason="Bypass mode: auto-accepted",
                allow=True,
            )
            self.audit_logger.log(tool, operation, result.decision, risk_level, context)
            return result

        # Check user preferences
        if self.store.is_allowed(tool, operation):
            result = PermissionResult(
                decision=PermissionDecision.ALLOW,
                level=risk_level,
                reason="User preference: allowed",
                allow=True,
            )
            self.audit_logger.log(tool, operation, result.decision, risk_level, context)
            return result

        if self.store.is_denied(tool, operation):
            result = PermissionResult(
                decision=PermissionDecision.DENY,
                level=risk_level,
                reason="User preference: denied",
                allow=False,
            )
            self.audit_logger.log(tool, operation, result.decision, risk_level, context)
            return result

        # Apply policy
        decision = self.policy_engine.apply_policy(risk_level)

        result = PermissionResult(
            decision=decision,
            level=risk_level,
            reason=f"Policy decision: {decision.value}",
            allow=decision == PermissionDecision.ALLOW,
        )
        self.audit_logger.log(tool, operation, result.decision, risk_level, context)
        return result

    def assess_risk(
        self, tool: str, operation: str, context: dict[str, Any] | None = None
    ) -> PermissionLevel:
        """
        Assess risk level of operation.

        Args:
            tool: Tool name
            operation: Operation name
            context: Operation context

        Returns:
            Permission level
        """
        context = context or {}

        # Check for critical operations
        critical_ops = ["delete", "drop", "force_push", "truncate", "destroy"]
        if operation in critical_ops:
            return PermissionLevel.CRITICAL

        # Check for dangerous operations
        dangerous_ops = ["execute", "deploy", "modify", "update", "create"]
        if operation in dangerous_ops:
            return PermissionLevel.DANGEROUS

        # Check for medium risk operations
        medium_ops = ["write", "edit", "save", "commit"]
        if operation in medium_ops:
            return PermissionLevel.MEDIUM

        # Check context for sensitive paths
        if "path" in context:
            path = context["path"]
            sensitive_paths = ["/etc", "/var", "/sys", "~/.ssh", "~/.aws"]
            if any(path.startswith(p) for p in sensitive_paths):
                return PermissionLevel.CRITICAL

        # Default to SAFE for read operations
        return PermissionLevel.SAFE

    def set_policy(self, policy: PermissionPolicy):
        """Set permission policy."""
        self.policy_engine.set_policy(policy)

    def get_policy(self) -> PermissionPolicy:
        """Get current permission policy."""
        return self.policy_engine.policy
