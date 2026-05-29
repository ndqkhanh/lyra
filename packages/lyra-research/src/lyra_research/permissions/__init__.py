"""
Permissions Module

Implements bypass permissions system with security gates and audit logging.
"""

from .audit_logger import (
    AuditEntry,
    AuditLogger,
)
from .bypass_manager import (
    BypassConfig,
    BypassManager,
)
from .permission_gate import (
    PermissionGate,
    PermissionLevel,
    PermissionRequest,
)

__all__ = [
    "PermissionGate",
    "PermissionRequest",
    "PermissionLevel",
    "BypassManager",
    "BypassConfig",
    "AuditLogger",
    "AuditEntry",
]
