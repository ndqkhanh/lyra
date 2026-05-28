"""
Plugin Manager — discovers, loads, validates, and manages Lyra plugins.

Scans configured plugin directories, validates manifests, resolves
dependencies, and provides lifecycle hooks (load/unload/enable/disable).
"""

from __future__ import annotations

import importlib
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .manifest import PluginKind, PluginManifest


class PluginState(str, Enum):
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginInstance:
    """Runtime state for an installed plugin."""

    manifest: PluginManifest
    path: Path
    state: PluginState = PluginState.DISCOVERED
    error_message: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def is_active(self) -> bool:
        return self.state == PluginState.ENABLED


class PluginManager:
    """Discovers, loads, and manages Lyra plugins.

    Usage::

        pm = PluginManager()
        pm.add_search_path(Path.home() / ".lyra" / "plugins")
        pm.discover()
        pm.load_all()
        pm.enable("my-plugin")
    """

    def __init__(self) -> None:
        self._search_paths: list[Path] = [
            Path.home() / ".lyra" / "plugins",
            Path("/usr/local/share/lyra/plugins"),
        ]
        self._plugins: dict[str, PluginInstance] = {}
        self._hooks: dict[str, list[Callable]] = {
            "on_load": [],
            "on_unload": [],
            "on_enable": [],
            "on_disable": [],
        }

    def add_search_path(self, path: Path) -> None:
        """Add a directory to scan for plugins."""
        if path not in self._search_paths:
            self._search_paths.append(path)

    def discover(self) -> list[str]:
        """Scan search paths for plugin manifests. Returns discovered names."""
        discovered: list[str] = []
        for search_path in self._search_paths:
            if not search_path.exists():
                continue
            for plugin_dir in search_path.iterdir():
                if not plugin_dir.is_dir():
                    continue
                manifest_path = plugin_dir / "plugin.json"
                if not manifest_path.exists():
                    manifest_path = plugin_dir / "plugin.yaml"
                if not manifest_path.exists():
                    continue

                try:
                    manifest = self._load_manifest(manifest_path)
                    instance = PluginInstance(
                        manifest=manifest,
                        path=plugin_dir,
                        state=PluginState.VALIDATED,
                    )
                    self._plugins[manifest.name] = instance
                    discovered.append(manifest.name)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    name = plugin_dir.name
                    self._plugins[name] = PluginInstance(
                        manifest=PluginManifest(name=name, version="0.0.0", kind=PluginKind.SKILL),
                        path=plugin_dir,
                        state=PluginState.ERROR,
                        error_message=str(e),
                    )
        return discovered

    def load(self, name: str) -> bool:
        """Load a single plugin by name."""
        instance = self._plugins.get(name)
        if instance is None or instance.state == PluginState.ERROR:
            return False

        if instance.manifest.entry_point:
            try:
                spec = importlib.util.spec_from_file_location(
                    f"lyra_plugin_{name}",
                    instance.path / instance.manifest.entry_point,
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = module
                    spec.loader.exec_module(module)
            except Exception as e:
                instance.state = PluginState.ERROR
                instance.error_message = str(e)
                return False

        instance.state = PluginState.LOADED
        for hook in self._hooks["on_load"]:
            try:
                hook(instance)
            except Exception:
                pass
        return True

    def load_all(self) -> int:
        """Load all validated plugins. Returns count loaded."""
        count = 0
        for name in list(self._plugins.keys()):
            if self._plugins[name].state == PluginState.VALIDATED:
                if self.load(name):
                    count += 1
        return count

    def enable(self, name: str) -> bool:
        """Enable a loaded plugin."""
        instance = self._plugins.get(name)
        if instance is None or instance.state != PluginState.LOADED:
            return False

        instance.state = PluginState.ENABLED
        for hook in self._hooks["on_enable"]:
            try:
                hook(instance)
            except Exception:
                pass
        return True

    def disable(self, name: str) -> bool:
        """Disable a plugin."""
        instance = self._plugins.get(name)
        if instance is None or instance.state != PluginState.ENABLED:
            return False

        instance.state = PluginState.DISABLED
        for hook in self._hooks["on_disable"]:
            try:
                hook(instance)
            except Exception:
                pass
        return True

    def unload(self, name: str) -> bool:
        """Unload a plugin."""
        instance = self._plugins.get(name)
        if instance is None:
            return False

        for hook in self._hooks["on_unload"]:
            try:
                hook(instance)
            except Exception:
                pass

        del self._plugins[name]
        return True

    def on(self, event: str, callback: Callable) -> None:
        """Register a lifecycle hook callback."""
        if event in self._hooks:
            self._hooks[event].append(callback)

    @property
    def plugins(self) -> list[PluginInstance]:
        return list(self._plugins.values())

    @property
    def active_plugins(self) -> list[PluginInstance]:
        return [p for p in self._plugins.values() if p.is_active]

    @property
    def errored_plugins(self) -> list[PluginInstance]:
        return [p for p in self._plugins.values() if p.state == PluginState.ERROR]

    def get(self, name: str) -> PluginInstance | None:
        return self._plugins.get(name)

    def list_by_kind(self, kind: PluginKind) -> list[PluginInstance]:
        results: list[PluginInstance] = []
        for instance in self._plugins.values():
            manifest_kind = instance.manifest.kind
            if isinstance(manifest_kind, list):
                if kind in manifest_kind:
                    results.append(instance)
            elif manifest_kind == kind:
                results.append(instance)
        return results

    @staticmethod
    def _load_manifest(path: Path) -> PluginManifest:
        if path.suffix == ".yaml":
            try:
                import yaml
                with open(path) as f:
                    data = yaml.safe_load(f)
            except ImportError:
                raise ValueError("PyYAML required for .yaml manifests")
        else:
            data = json.loads(path.read_text())
        return PluginManifest.from_dict(data)


_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager singleton."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
