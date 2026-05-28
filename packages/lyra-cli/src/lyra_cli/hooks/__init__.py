"""Hook system for Lyra - ECC-inspired event-driven automation"""

from .builtin_hooks import register_builtin_hooks
from .hook_manager import HookContext, HookManager, HookType
from .hook_registry import HookRegistry

__all__ = [
    "HookManager",
    "HookType",
    "HookContext",
    "HookRegistry",
    "register_builtin_hooks",
]
