"""Shipped hooks.

Phase 1 ships three hooks:
    - tdd-gate (stub contract)
    - secrets-scan
    - destructive-pattern
"""
from __future__ import annotations

from .destructive_pattern import destructive_pattern_hook
from .lifecycle import LifecycleBus, LifecycleEvent, Subscriber
from .secrets_scan import secrets_scan_hook
from .tdd_gate import TDDGateContext, make_tdd_gate_hook

__all__ = [
    "LifecycleBus",
    "LifecycleEvent",
    "Subscriber",
    "TDDGateContext",
    "destructive_pattern_hook",
    "make_tdd_gate_hook",
    "secrets_scan_hook",
]
