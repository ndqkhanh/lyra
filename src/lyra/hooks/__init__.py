"""
Hooks system for Lyra.

This module provides event-driven automation through hooks that fire
at specific lifecycle points.

v2 adds HookAction, expanded HookType values (PRE/POST_MODEL_CALL), the
HookEngine v2 interceptor pipeline, and built-in handlers.
"""

from .handlers import CommandGuard, CostTracker, SecretsScanner
from .hook import (
    Hook,
    HookAction,
    HookContext,
    HookResult,
    HookType,
)
from .hook_engine import HookEngine
from .hook_registry import HookRegistry

__all__ = [
    "Hook",
    "HookAction",
    "HookType",
    "HookContext",
    "HookResult",
    "HookRegistry",
    "HookEngine",
    "SecretsScanner",
    "CommandGuard",
    "CostTracker",
]

__version__ = "2.0.0"
