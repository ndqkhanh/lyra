"""
Hooks Module

Hook integration for Lyra lifecycle events.
"""

from .permission_hooks import PermissionHooks
from .sound_hooks import SoundHooks

__all__ = [
    "PermissionHooks",
    "SoundHooks",
]
