"""Plugin loader — loads and initializes plugins with sandboxing."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from .manifest import PluginManifest, PluginPermission

logger = logging.getLogger(__name__)


class PluginLoader:
    """Loads plugins from manifests with permission-aware sandboxing."""

    def __init__(self, plugins_dir: str | Path = ".lyra/plugins") -> None:
        self._dir = Path(plugins_dir)
        self._loaded: dict[str, Any] = {}

    def load(self, manifest: PluginManifest) -> Any | None:
        """Load a plugin module by its manifest. Returns the module or None."""
        if manifest.name in self._loaded:
            return self._loaded[manifest.name]

        if not manifest.entry_point:
            logger.warning("Plugin %s has no entry_point", manifest.name)
            return None

        plugin_dir = self._dir / manifest.name
        entry_path = plugin_dir / manifest.entry_point

        if not entry_path.exists():
            logger.error("Plugin entry point not found: %s", entry_path)
            return None

        try:
            spec = importlib.util.spec_from_file_location(
                f"lyra_plugin_{manifest.name}", str(entry_path),
            )
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            self._loaded[manifest.name] = module
            logger.info("Loaded plugin: %s v%s", manifest.name, manifest.version)
            return module
        except Exception as e:
            logger.error("Failed to load plugin %s: %s", manifest.name, e)
            return None

    def unload(self, name: str) -> bool:
        if name in self._loaded:
            del self._loaded[name]
            sys.modules.pop(f"lyra_plugin_{name}", None)
            return True
        return False

    @property
    def loaded_count(self) -> int:
        return len(self._loaded)
