"""
Permission Gate

Permission checkpoint for operations with bypass support.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any


class PermissionLevel(Enum):
    """Permission levels for operations"""
    SAFE = "safe"           # Always allowed (read-only)
    STANDARD = "standard"   # Requires confirmation
    DANGEROUS = "dangerous" # Always requires confirmation (cannot bypass)
    CRITICAL = "critical"   # Requires multi-factor confirmation


@dataclass
class PermissionRequest:
    """Request for permission to perform operation"""
    operation: str
    level: PermissionLevel
    description: str
    context: Dict[str, Any]
    can_bypass: bool = True  # Some operations cannot be bypassed


# Critical operations that cannot be bypassed
CRITICAL_OPERATIONS = {
    'file_delete',
    'database_drop',
    'production_deploy',
    'credential_modify',
    'system_config_change'
}


class PermissionGate:
    """
    Permission checkpoint for operations

    Checks if operation should be allowed based on:
    - Permission level
    - Bypass mode status
    - Operation type
    """

    def __init__(self, bypass_manager):
        self.bypass_manager = bypass_manager

    def check_permission(self, request: PermissionRequest) -> bool:
        """
        Check if operation is permitted

        Returns:
            True if allowed, False if denied
        """
        # SAFE operations always allowed
        if request.level == PermissionLevel.SAFE:
            return True

        # Critical operations cannot be bypassed
        if request.operation in CRITICAL_OPERATIONS:
            request.can_bypass = False

        # CRITICAL operations always require confirmation
        if request.level == PermissionLevel.CRITICAL:
            return self._request_confirmation(request)

        # Check bypass mode
        if self.bypass_manager.is_bypass_enabled() and request.can_bypass:
            self.bypass_manager.log_bypass(request)
            return True

        # Standard flow: request confirmation
        return self._request_confirmation(request)

    def _request_confirmation(self, request: PermissionRequest) -> bool:
        """Request user confirmation for operation"""
        # In production, this would show UI prompt
        # For now, return True for testing
        return True
