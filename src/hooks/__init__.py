"""
Hooks system for Lyra.

This module provides event-driven automation through hooks that fire
at specific lifecycle points.
"""

from .hook import Hook, HookContext, HookResult, HookType
from .hook_engine import HookEngine
from .hook_registry import HookRegistry

__all__ = [
    "Hook",
    "HookType",
    "HookContext",
    "HookResult",
    "HookRegistry",
    "HookEngine",
]

__version__ = "1.0.0"
