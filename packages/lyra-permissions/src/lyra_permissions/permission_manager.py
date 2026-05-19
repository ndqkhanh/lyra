"""
Permission Manager - Central permission registry and decision engine.

Features:
- Risk assessment
- Permission checking
- Policy application
- Context-aware decisions
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

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

    def check_permission(
        self, tool: str, operation: str, context: Optional[Dict[str, Any]] = None
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

        # CRITICAL operations always require confirmation
        if risk_level == PermissionLevel.CRITICAL:
            return PermissionResult(
                decision=PermissionDecision.PROMPT,
                level=risk_level,
                reason="Critical operation requires confirmation",
                allow=False,
            )

        # Check user preferences
        if self.store.is_allowed(tool, operation):
            return PermissionResult(
                decision=PermissionDecision.ALLOW,
                level=risk_level,
                reason="User preference: allowed",
                allow=True,
            )

        if self.store.is_denied(tool, operation):
            return PermissionResult(
                decision=PermissionDecision.DENY,
                level=risk_level,
                reason="User preference: denied",
                allow=False,
            )

        # Apply policy
        decision = self.policy_engine.apply_policy(risk_level)

        return PermissionResult(
            decision=decision,
            level=risk_level,
            reason=f"Policy decision: {decision.value}",
            allow=decision == PermissionDecision.ALLOW,
        )

    def assess_risk(
        self, tool: str, operation: str, context: Optional[Dict[str, Any]] = None
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
