"""
Plugins system for Lyra.

Provides a Plugin protocol (name, version, tools, hooks, initialize, shutdown)
and a PluginManager for dynamically loading, enabling, disabling, and listing
plugins at runtime. Also provides manifest-based discovery, hot reloading,
deferred loading, and a plugin marketplace.
"""

from __future__ import annotations

from .manager import Plugin, PluginManager
from .manifest_discovery import ManifestDiscovery, ManifestPlugin, HotReloader, DeferredLoader
from .marketplace import PluginMarketplace, MarketPlugin

__all__ = [
    "Plugin",
    "PluginManager",
    "ManifestDiscovery",
    "ManifestPlugin",
    "HotReloader",
    "DeferredLoader",
    "PluginMarketplace",
    "MarketPlugin",
]

__version__ = "1.0.0"
