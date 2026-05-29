"""
Permission Hooks

Hook integration for permission system with bypass support.
"""

from typing import Any

from ..permissions.bypass_manager import BypassManager
from ..permissions.permission_gate import PermissionGate, PermissionLevel, PermissionRequest


class PermissionHooks:
    """
    Hook integration for permission system

    Provides hooks for:
    - Pre-operation permission check
    - Post-operation audit logging
    - Bypass mode toggle
    """

    def __init__(self, bypass_manager: BypassManager = None):
        self.bypass_manager = bypass_manager or BypassManager()
        self.permission_gate = PermissionGate(self.bypass_manager)

    def pre_operation_hook(self, operation: str, level: PermissionLevel,
                          description: str, context: dict[str, Any]) -> bool:
        """
        Hook called before operation execution

        Args:
            operation: Operation name
            level: Permission level
            description: Operation description
            context: Operation context

        Returns:
            True if operation should proceed
        """
        request = PermissionRequest(
            operation=operation,
            level=level,
            description=description,
            context=context
        )

        return self.permission_gate.check_permission(request)

    def post_operation_hook(self, operation: str, success: bool, result: Any):
        """
        Hook called after operation execution

        Args:
            operation: Operation name
            success: Whether operation succeeded
            result: Operation result
        """
        # Log operation result
        # In production, this could log to audit trail or metrics
        pass

    def toggle_bypass_hook(self) -> bool:
        """
        Hook for toggling bypass mode (e.g., via keyboard shortcut)

        Returns:
            New bypass state (True = enabled)
        """
        return self.bypass_manager.toggle_bypass()

    def get_bypass_status(self) -> bool:
        """
        Get current bypass status

        Returns:
            True if bypass is enabled
        """
        return self.bypass_manager.is_bypass_enabled()
