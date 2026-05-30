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

Hot-reload system provides:
* File system watching with :class:`PluginWatcher`
* Dependency resolution with :class:`DependencyResolver`
* Automatic reload with validation and rollback via :class:`PluginHotReloader`
"""
from __future__ import annotations

from .dependency_resolver import DependencyGraph, DependencyResolver
from .discovery import Plugin, discover_plugins, fire
from .hot_reload import (
    PluginFileState,
    PluginHotReloader,
    PluginSnapshot,
    ReloadEvent,
    ReloadStatus,
)
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
from .watcher import FileChangeEvent, PluginWatcher, WatcherConfig

__all__ = [
    "DependencyGraph",
    "DependencyResolver",
    "FileChangeEvent",
    "HarnessPlugin",
    "HookResult",
    "LoadedPlugin",
    "PLUGIN_MANIFEST_FILES",
    "Plugin",
    "PluginFileState",
    "PluginHook",
    "PluginHotReloader",
    "PluginManifest",
    "PluginManifestError",
    "PluginManifestSpec",
    "PluginMetadata",
    "PluginRegistry",
    "PluginRuntime",
    "PluginSnapshot",
    "PluginValidationError",
    "PluginWatcher",
    "ReloadEvent",
    "ReloadStatus",
    "WatcherConfig",
    "discover_plugins",
    "fire",
    "load_manifest",
    "load_plugin",
    "validate_manifest",
]
