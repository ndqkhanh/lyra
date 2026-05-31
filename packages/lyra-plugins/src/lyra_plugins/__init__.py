"""
Lyra Plugin System — marketplace-style discovery, validation, and sandboxed loading.

Provider-agnostic: plugins are validated and loaded at the harness level,
independent of which LLM provider is active. Uses the Tier 1 provider abstraction
to normalize tool calls from plugins.

Key capabilities:
- **Plugin Manifest**: Standardized metadata (name, version, tools, hooks, permissions)
- **Discovery**: Auto-discover from `.lyra/plugins/` directory
- **Validation**: Manifest schema validation before loading
- **Sandboxing**: Plugins run with restricted tool access per their manifest
- **Provider Bridge**: Plugins use ProviderBridge for LLM calls (multi-provider)
"""

from __future__ import annotations

from .discovery import PluginDiscovery
from .manifest import PluginManifest, PluginPermission
from .loader import PluginLoader
from .sandbox import PluginSandbox

__all__ = [
    "PluginDiscovery",
    "PluginLoader",
    "PluginManifest",
    "PluginPermission",
    "PluginSandbox",
]
