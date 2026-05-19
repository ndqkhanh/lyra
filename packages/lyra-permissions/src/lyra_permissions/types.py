"""
Permission types - Shared enums and types.
"""

from enum import Enum


class PermissionLevel(Enum):
    """Permission risk levels."""

    SAFE = "safe"  # Always allow (Read, List, Search)
    MEDIUM = "medium"  # Prompt once per session (Edit, Write)
    DANGEROUS = "dangerous"  # Always prompt (Delete, Execute, Deploy)
    CRITICAL = "critical"  # Require explicit confirmation (Drop DB, Force Push)


class PermissionDecision(Enum):
    """Permission decision types."""

    ALLOW = "allow"
    DENY = "deny"
    PROMPT = "prompt"


class PermissionPolicy(Enum):
    """Permission policy types."""

    STRICT = "strict"  # Prompt for everything except SAFE
    BALANCED = "balanced"  # Prompt for DANGEROUS and CRITICAL (default)
    PERMISSIVE = "permissive"  # Only prompt for CRITICAL
    BYPASS = "bypass"  # Auto-accept all (with audit log)
