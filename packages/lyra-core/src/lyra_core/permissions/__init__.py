"""Lyra permission modes.

Extends ``lyra_harness_core.permissions`` with TDD-aware modes (RED/GREEN/REFACTOR)
and a research / notes-scratchpad mode. Hard deny rules and BYPASS semantics
inherit from lyra_harness_core.

Safety Integration:
    SafetyEnhancedPermissionResolver integrates approval gates, reasoning monitoring,
    adversarial verification, audit logging, and alignment tracking with the
    existing permission system.
"""
from __future__ import annotations

from .injection import GuardResult, INJECTION_PATTERNS, injection_guard
from .modes import LyraMode
from .resolver import Decision, PermissionDecision, resolve_lyra_decision
from .safety_integration import SafetyDecision, SafetyEnhancedPermissionResolver
from .stack import PermissionMode, PermissionStack, StackDecision, StackInput

__all__ = [
    "Decision",
    "GuardResult",
    "INJECTION_PATTERNS",
    "LyraMode",
    "PermissionDecision",
    "PermissionMode",
    "PermissionStack",
    "SafetyDecision",
    "SafetyEnhancedPermissionResolver",
    "StackDecision",
    "StackInput",
    "injection_guard",
    "resolve_lyra_decision",
]
