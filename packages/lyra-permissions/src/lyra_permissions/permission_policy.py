"""
Permission Policy - Policy definitions and rule-based evaluation.

Features:
- Permission policies (STRICT, BALANCED, PERMISSIVE, BYPASS)
- Rule-based evaluation
- Policy enforcement
"""

from lyra_permissions.types import (
    PermissionDecision,
    PermissionLevel,
    PermissionPolicy,
)


class PolicyEngine:
    """
    Policy-based permission evaluation.

    Features:
    - Policy enforcement
    - Rule-based decisions
    - Policy switching
    """

    def __init__(self, policy: PermissionPolicy = PermissionPolicy.BALANCED):
        """Initialize policy engine."""
        self.policy = policy

    def apply_policy(self, level: PermissionLevel) -> PermissionDecision:
        """
        Apply policy to permission level.

        Args:
            level: Permission level

        Returns:
            Permission decision
        """
        if self.policy == PermissionPolicy.STRICT:
            # Prompt for everything except SAFE
            if level == PermissionLevel.SAFE:
                return PermissionDecision.ALLOW
            return PermissionDecision.PROMPT

        elif self.policy == PermissionPolicy.BALANCED:
            # Prompt for DANGEROUS and CRITICAL
            if level in [PermissionLevel.SAFE, PermissionLevel.MEDIUM]:
                return PermissionDecision.ALLOW
            return PermissionDecision.PROMPT

        elif self.policy == PermissionPolicy.PERMISSIVE:
            # Only prompt for CRITICAL
            if level == PermissionLevel.CRITICAL:
                return PermissionDecision.PROMPT
            return PermissionDecision.ALLOW

        elif self.policy == PermissionPolicy.BYPASS:
            # Auto-accept all (audit logged elsewhere)
            return PermissionDecision.ALLOW

        # Default to PROMPT for unknown policy
        return PermissionDecision.PROMPT

    def set_policy(self, policy: PermissionPolicy):
        """Set permission policy."""
        self.policy = policy

    def get_policy(self) -> PermissionPolicy:
        """Get current policy."""
        return self.policy
