"""
Manifest-based plugin discovery, hot reloading, and deferred loading.

Provides ManifestDiscovery for discovering plugins from manifest files
(e.g. pyproject.toml, plugin.yaml), HotReloader for swapping plugins
without restarting the host process, and DeferredLoader for loading plugin
capabilities on first use rather than at startup.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from lyra.plugins.manager import Plugin, PluginManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ManifestPlugin model
# ---------------------------------------------------------------------------


@dataclass
class ManifestPlugin:
    """A plugin discovered from a manifest file.

    Attributes:
        name: Plugin name.
        version: Plugin version string.
        path: Filesystem path to the plugin entry point.
        manifest_path: Path to the manifest file that declared this plugin.
        capabilities: List of capability strings this plugin provides.
        metadata: Arbitrary additional metadata from the manifest.
    """

    name: str
    version: str
    path: str
    manifest_path: str
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ManifestDiscovery
# ---------------------------------------------------------------------------


class ManifestDiscovery:
    """Discovers plugins from manifest files (pyproject.toml, plugin.yaml, etc.).

    Scans configured search paths for manifest files and extracts plugin
    metadata. Supports multiple manifest formats.
    """

    # Known manifest filenames, ordered by preference
    MANIFEST_NAMES = ["plugin.yaml", "plugin.yml", "plugin.json", "pyproject.toml"]

    def __init__(self, search_paths: list[str] | None = None):
        """Initialize ManifestDiscovery.

        Args:
            search_paths: Directories to search for manifests. Defaults to
                a "plugins" subdirectory relative to the package root.
        """
        self._search_paths = search_paths or self._default_paths()
        self._discovered: dict[str, ManifestPlugin] = {}

    @staticmethod
    def _default_paths() -> list[str]:
        """Return default search paths."""
        candidates = []
        # Check common plugin directories
        for parent in (Path.cwd(), Path(__file__).resolve().parent):
            plugins_dir = parent / "plugins"
            if plugins_dir.is_dir():
                candidates.append(str(plugins_dir))
        return candidates or [str(Path.cwd() / "plugins")]

    def discover(self) -> list[ManifestPlugin]:
        """Scan all search paths and discover plugins from manifests.

        Returns:
            List of discovered ManifestPlugin instances.
        """
        discovered: dict[str, ManifestPlugin] = {}

        for search_path in self._search_paths:
            base = Path(search_path)
            if not base.is_dir():
                continue

            # Look for manifest files in immediate subdirectories
            for child in sorted(base.iterdir()):
                if not child.is_dir():
                    continue
                plugin = self._scan_directory(child)
                if plugin is not None:
                    discovered[plugin.name] = plugin

            # Also check the search path itself for standalone manifests
            plugin = self._scan_directory(base)
            if plugin is not None:
                discovered[plugin.name] = plugin

        self._discovered = discovered
        return list(discovered.values())

    def discover_from_file(self, path: str) -> ManifestPlugin | None:
        """Read a single manifest file and return plugin metadata.

        Args:
            path: Path to a manifest file.

        Returns:
            ManifestPlugin if the file contains valid plugin metadata,
            or None if parsing fails.
        """
        p = Path(path)
        if not p.exists():
            logger.warning("Manifest file not found: %s", path)
            return None

        data = self._read_manifest(p)
        if data is None:
            return None

        name = data.get("name", p.parent.stem)
        plugin = ManifestPlugin(
            name=name,
            version=str(data.get("version", "0.1.0")),
            path=str(data.get("entry", p.parent / "plugin.py")),
            manifest_path=str(p),
            capabilities=data.get("capabilities", []),
            metadata={k: v for k, v in data.items() if k not in ("name", "version", "entry", "capabilities")},
        )
        self._discovered[plugin.name] = plugin
        return plugin

    def get_plugin(self, name: str) -> ManifestPlugin | None:
        """Get a previously discovered plugin by name.

        Args:
            name: Plugin name.

        Returns:
            ManifestPlugin if found, None otherwise.
        """
        return self._discovered.get(name)

    def list_plugins(self) -> list[ManifestPlugin]:
        """Return all discovered plugins."""
        return list(self._discovered.values())

    def _scan_directory(self, directory: Path) -> ManifestPlugin | None:
        """Scan a single directory for manifest files."""
        for manifest_name in self.MANIFEST_NAMES:
            manifest_path = directory / manifest_name
            if manifest_path.exists():
                return self.discover_from_file(str(manifest_path))
        return None

    def _read_manifest(self, path: Path) -> dict[str, Any] | None:
        """Read and parse a manifest file.

        Supports YAML (.yaml, .yml), JSON (.json), and TOML (pyproject.toml).
        """
        suffix = path.suffix.lower()
        try:
            if suffix in (".yaml", ".yml"):
                import yaml  # type: ignore[import-untyped]
                raw = path.read_text(encoding="utf-8")
                data: dict[str, Any] = yaml.safe_load(raw) or {}
                # If pyproject.toml, extract [tool.lyra.plugins]
                return data.get("plugin") or data

            elif suffix == ".json":
                import json
                return json.loads(path.read_text(encoding="utf-8"))

            elif suffix == ".toml" or path.name == "pyproject.toml":
                return self._parse_pyproject_toml(path)

            else:
                logger.warning("Unsupported manifest format: %s", suffix)
                return None

        except Exception as exc:
            logger.warning("Failed to read manifest %s: %s", path, exc)
            return None

    @staticmethod
    def _parse_pyproject_toml(path: Path) -> dict[str, Any] | None:
        """Extract plugin metadata from pyproject.toml [tool.lyra.plugins.*]."""
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[import-not-found]
            except ImportError:
                logger.warning("No TOML parser available")
                return None

        raw = path.read_text(encoding="utf-8")
        try:
            data = tomllib.loads(raw)
        except Exception:
            return None

        # Look for [tool.lyra.plugins.<name>] sections
        tool = data.get("tool", {})
        lyra_section = tool.get("lyra", {})
        plugins = lyra_section.get("plugins", {})
        if not plugins:
            return None

        # Return the first plugin entry (caller iterates per-directory)
        for name, config in plugins.items():
            if isinstance(config, dict):
                config["name"] = name
                return config
        return None


# ---------------------------------------------------------------------------
# HotReloader
# ---------------------------------------------------------------------------


@dataclass
class _WatchedPlugin:
    name: str
    path: str
    mtime: float
    manifest_path: str | None = None


class HotReloader:
    """Monitors plugin files for changes and reloads them without restart.

    Polls the filesystem mtime of plugin source files and triggers
    reloads when changes are detected.
    """

    def __init__(self, plugin_manager: PluginManager, poll_interval: float = 2.0):
        """Initialize HotReloader.

        Args:
            plugin_manager: The PluginManager to reload plugins in.
            poll_interval: Seconds between filesystem polls.
        """
        self._manager = plugin_manager
        self._poll_interval = poll_interval
        self._watched: dict[str, _WatchedPlugin] = {}
        self._last_poll: float = 0.0

    def watch(self, plugin_name: str) -> bool:
        """Start watching a loaded plugin for changes.

        Args:
            plugin_name: Name of an already-loaded plugin.

        Returns:
            True if the plugin is now being watched.
        """
        plugin = self._manager.get(plugin_name)
        if plugin is None:
            logger.warning("Cannot watch unknown plugin: %s", plugin_name)
            return False

        # Try to find the plugin source file
        try:
            import inspect
            mod = inspect.getmodule(plugin)
            if mod and mod.__file__:
                path = mod.__file__
            else:
                path = f"plugins/{plugin_name}.py"
        except Exception:
            path = f"plugins/{plugin_name}.py"

        p = Path(path)
        mtime = p.stat().st_mtime if p.exists() else 0.0

        self._watched[plugin_name] = _WatchedPlugin(
            name=plugin_name,
            path=str(p),
            mtime=mtime,
        )
        logger.info("Now watching plugin %r at %s", plugin_name, path)
        return True

    def unwatch(self, plugin_name: str) -> bool:
        """Stop watching a plugin.

        Args:
            plugin_name: Name of the watched plugin.

        Returns:
            True if the plugin was being watched.
        """
        return self._watched.pop(plugin_name, None) is not None

    def poll(self) -> list[str]:
        """Check all watched plugins for file changes.

        Should be called periodically (e.g. from an async event loop).

        Returns:
            List of plugin names that were reloaded this poll.
        """
        now = time.time()
        if now - self._last_poll < self._poll_interval:
            return []
        self._last_poll = now

        reloaded: list[str] = []
        for name, watched in list(self._watched.items()):
            current_mtime = self._file_mtime(watched.path)
            if current_mtime is not None and current_mtime > watched.mtime:
                logger.info("Detected change in plugin %r, reloading...", name)
                if self.reload(name):
                    watched.mtime = current_mtime
                    reloaded.append(name)
        return reloaded

    def reload(self, plugin_name: str) -> bool:
        """Manually reload a single plugin.

        Shuts down the old instance and re-loads from the original path.

        Args:
            plugin_name: Name of the plugin to reload.

        Returns:
            True if the reload succeeded.
        """
        watched = self._watched.get(plugin_name)
        if watched is None:
            logger.warning("Cannot reload unwatched plugin: %s", plugin_name)
            return False

        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(
                self._manager.shutdown(plugin_name)
            )
        except Exception as exc:
            logger.warning("Shutdown during reload failed: %s", exc)

        # Re-discover and load the plugin
        discovery = ManifestDiscovery(search_paths=[str(Path(watched.path).parent)])
        manifest = discovery.discover_from_file(watched.path)
        if manifest:
            try:
                self._manager.load_plugin(manifest.path)
                logger.info("Reloaded plugin %r", plugin_name)
                return True
            except Exception as exc:
                logger.error("Failed to reload plugin %r: %s", plugin_name, exc)
                return False
        return False

    def list_watched(self) -> list[str]:
        """Return names of all currently watched plugins."""
        return list(self._watched.keys())

    @staticmethod
    def _file_mtime(path: str) -> float | None:
        try:
            return Path(path).stat().st_mtime
        except OSError:
            return None


# ---------------------------------------------------------------------------
# DeferredLoader
# ---------------------------------------------------------------------------


class DeferredLoader:
    """Loads plugin capabilities on first use rather than at startup.

    Registers lazy loaders that materialise plugin instances only when
    their tools or hooks are first requested.
    """

    def __init__(self, plugin_manager: PluginManager):
        """Initialize DeferredLoader.

        Args:
            plugin_manager: The PluginManager to defer loading into.
        """
        self._manager = plugin_manager
        self._loaders: dict[str, Callable[[], Plugin]] = {}
        self._loaded: set[str] = set()

    def register(self, plugin_name: str, loader: Callable[[], Plugin]) -> None:
        """Register a deferred plugin loader.

        The plugin will not be loaded until ``get()`` is called.

        Args:
            plugin_name: Logical plugin name.
            loader: Zero-argument callable that returns a Plugin instance.
        """
        self._loaders[plugin_name] = loader
        logger.debug("Registered deferred loader for %r", plugin_name)

    def get(self, plugin_name: str) -> Plugin | None:
        """Get a plugin, loading it on first access.

        Args:
            plugin_name: Plugin name.

        Returns:
            Plugin instance, or None if no loader is registered.
        """
        # Already loaded via PluginManager
        existing = self._manager.get(plugin_name)
        if existing is not None:
            self._loaded.add(plugin_name)
            return existing

        # Not yet loaded — check for a deferred loader
        loader = self._loaders.get(plugin_name)
        if loader is None:
            return None

        try:
            plugin = loader()
            # The PluginManager.load_plugin path is bypassed; inject directly
            self._manager._plugins[plugin_name] = plugin  # type: ignore[attr-defined]
            self._loaded.add(plugin_name)
            logger.info("Deferred load of plugin %r", plugin_name)
            return plugin
        except Exception as exc:
            logger.error("Failed deferred load of %r: %s", plugin_name, exc)
            return None

    def load_all(self) -> int:
        """Force-load all registered deferred plugins.

        Returns:
            Number of plugins loaded.
        """
        count = 0
        for name in list(self._loaders.keys()):
            if not self.is_loaded(name):
                if self.get(name) is not None:
                    count += 1
        return count

    def is_loaded(self, plugin_name: str) -> bool:
        """Check whether a plugin has been materialised.

        Args:
            plugin_name: Plugin name.

        Returns:
            True if the plugin instance exists in the manager.
        """
        return plugin_name in self._loaded or self._manager.get(plugin_name) is not None

    def registered_names(self) -> list[str]:
        """Return names of all registered deferred plugins."""
        return list(self._loaders.keys())


__all__ = [
    "ManifestPlugin",
    "ManifestDiscovery",
    "HotReloader",
    "DeferredLoader",
]
