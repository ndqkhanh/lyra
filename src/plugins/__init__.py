"""
Plugins system for Lyra.

Provides a Plugin protocol (name, version, tools, hooks, initialize, shutdown)
and a PluginManager for dynamically loading, enabling, disabling, and listing
plugins at runtime.
"""

from __future__ import annotations

from .manager import Plugin, PluginManager

__all__ = [
    "Plugin",
    "PluginManager",
]

__version__ = "1.0.0"
