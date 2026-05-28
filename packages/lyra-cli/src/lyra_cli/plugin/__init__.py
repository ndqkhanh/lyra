"""
Plugin Ecosystem — extensible plugin system for Lyra.

Supports skills, agents, hooks, MCP servers, LSP servers, monitors,
tools, themes, and sound packs as plugin kinds. Includes discovery,
validation, loading, lifecycle hooks, and marketplace registry.
"""

from lyra_cli.plugin.manager import (
    PluginInstance,
    PluginManager,
    PluginState,
    get_plugin_manager,
)
from lyra_cli.plugin.manifest import (
    PluginDependency,
    PluginKind,
    PluginManifest,
    PluginPermission,
)
from lyra_cli.plugin.marketplace import PluginRegistry, RegistryEntry

__all__ = [
    "PluginDependency",
    "PluginInstance",
    "PluginKind",
    "PluginManager",
    "PluginManifest",
    "PluginPermission",
    "PluginRegistry",
    "PluginState",
    "RegistryEntry",
    "get_plugin_manager",
]
