"""
Lyra Permissions - Permission management and bypass mode.

This package provides:
- Permission levels and policies
- Permission manager
- Permission store
- Audit logging
"""

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
]
