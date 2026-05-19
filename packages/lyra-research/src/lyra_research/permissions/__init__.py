"""
Permissions Module

Implements bypass permissions system with security gates and audit logging.
"""

from .permission_gate import (
    PermissionGate,
    PermissionRequest,
    PermissionLevel,
)
from .bypass_manager import (
    BypassManager,
    BypassConfig,
)
from .audit_logger import (
    AuditLogger,
    AuditEntry,
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
