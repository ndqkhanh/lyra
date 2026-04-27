"""Wave-F Task 10: harness plugins as first-class extension points.

Two parallel plugin surfaces live here:

* **Programmatic** — :class:`PluginManifest`, :class:`PluginRegistry`,
  :func:`load_plugin` — a Python module that exports a ``manifest``
  attribute. This is the surface Wave-F's first-class registry uses.
* **Declarative** — :class:`PluginManifestSpec`,
  :func:`validate_manifest`, :func:`load_manifest`,
  :class:`PluginRuntime` — a ``.lyra-plugin`` / ``.claude-plugin`` /
  ``plugin.json`` header with a deferred ``entry`` callable. This
  gives parity with Claude Code / Codex plugin ecosystems.

Both surfaces share error semantics: malformed manifests raise
:class:`PluginManifestError` (declarative) or
:class:`PluginValidationError` (programmatic). Downstream code that
doesn't care about the distinction can catch ``ValueError``.
"""
from __future__ import annotations

from .discovery import Plugin, discover_plugins, fire
from .manifest import (
    PLUGIN_MANIFEST_FILES,
    PluginManifestError,
    PluginManifestSpec,
    load_manifest,
    validate_manifest,
)
from .registry import (
    HarnessPlugin,
    HookResult,
    PluginHook,
    PluginManifest,
    PluginMetadata,
    PluginRegistry,
    PluginValidationError,
    load_plugin,
)
from .runtime import LoadedPlugin, PluginRuntime

__all__ = [
    "HarnessPlugin",
    "HookResult",
    "LoadedPlugin",
    "PLUGIN_MANIFEST_FILES",
    "Plugin",
    "PluginHook",
    "PluginManifest",
    "PluginManifestError",
    "PluginManifestSpec",
    "PluginMetadata",
    "PluginRegistry",
    "PluginRuntime",
    "PluginValidationError",
    "discover_plugins",
    "fire",
    "load_manifest",
    "load_plugin",
    "validate_manifest",
]
