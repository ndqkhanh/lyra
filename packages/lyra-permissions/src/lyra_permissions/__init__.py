"""
Lyra Permissions - Permission management and bypass mode.

This package provides:
- Permission levels and policies
- Permission manager
- Permission store
- Bypass mode
- Audit logging
- Granular control
- CLI interface
"""

from lyra_permissions.bypass_mode import AuditLogger, BypassMode, SafetyGuardrails
from lyra_permissions.cli import PermissionCLI
from lyra_permissions.granular_control import (
    GranularController,
    PermissionProfile,
    TimeBasedController,
    ToolPermission,
)
from lyra_permissions.permission_manager import PermissionManager, PermissionResult
from lyra_permissions.permission_policy import PolicyEngine
from lyra_permissions.permission_store import PermissionStore
from lyra_permissions.types import (
    PermissionDecision,
    PermissionLevel,
    PermissionPolicy,
)

__version__ = "0.1.0"

__all__ = [
    # Types
    "PermissionLevel",
    "PermissionDecision",
    "PermissionPolicy",
    # Permission Manager
    "PermissionManager",
    "PermissionResult",
    # Permission Policy
    "PolicyEngine",
    # Permission Store
    "PermissionStore",
    # Bypass Mode
    "BypassMode",
    "AuditLogger",
    "SafetyGuardrails",
    # Granular Control
    "GranularController",
    "PermissionProfile",
    "TimeBasedController",
    "ToolPermission",
    # CLI
    "PermissionCLI",
]
