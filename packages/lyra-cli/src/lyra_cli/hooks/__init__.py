"""Hook system for Lyra - ECC-inspired event-driven automation"""

from .hook_manager import HookManager, HookType, HookContext
from .hook_registry import HookRegistry
from .builtin_hooks import register_builtin_hooks

__all__ = [
    "HookManager",
    "HookType",
    "HookContext",
    "HookRegistry",
    "register_builtin_hooks",
]
