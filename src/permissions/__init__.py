"""
Permission system — tool-level access control with ALLOW/DENY/ASK granularity.
"""

from src.permissions.manager import (
    AccessLevel,
    PermissionManager,
    PermissionOverride,
    PermissionPolicy,
    PermissionResult,
)

__version__ = "0.1.0"

__all__ = [
    "AccessLevel",
    "PermissionResult",
    "PermissionOverride",
    "PermissionPolicy",
    "PermissionManager",
]
