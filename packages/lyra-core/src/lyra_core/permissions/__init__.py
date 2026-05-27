"""Lyra permission modes.

Extends ``lyra_harness_core.permissions`` with TDD-aware modes (RED/GREEN/REFACTOR)
and a research / notes-scratchpad mode. Hard deny rules and BYPASS semantics
inherit from lyra_harness_core.
"""
from __future__ import annotations

from .injection import GuardResult, INJECTION_PATTERNS, injection_guard
from .modes import LyraMode
from .resolver import Decision, PermissionDecision, resolve_lyra_decision
from .stack import PermissionMode, PermissionStack, StackDecision, StackInput

__all__ = [
    "Decision",
    "GuardResult",
    "INJECTION_PATTERNS",
    "LyraMode",
    "PermissionDecision",
    "PermissionMode",
    "PermissionStack",
    "StackDecision",
    "StackInput",
    "injection_guard",
    "resolve_lyra_decision",
]
