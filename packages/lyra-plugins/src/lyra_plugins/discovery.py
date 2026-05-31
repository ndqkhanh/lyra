"""Plugin discovery — auto-detect plugins from .lyra/plugins/ directory."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .manifest import PluginManifest

logger = logging.getLogger(__name__)


class PluginDiscovery:
    """Discovers plugins from the filesystem."""

    def __init__(self, plugins_dir: str | Path = ".lyra/plugins") -> None:
        self._dir = Path(plugins_dir)
        self._manifests: dict[str, PluginManifest] = {}

    def discover(self) -> list[PluginManifest]:
        """Scan the plugins directory and return all valid manifests."""
        if not self._dir.exists():
            return []

        discovered: list[PluginManifest] = []
        for manifest_path in self._dir.glob("*/plugin.json"):
            try:
                data = json.loads(manifest_path.read_text())
                manifest = PluginManifest(
                    name=data.get("name", manifest_path.parent.name),
                    version=data.get("version", "0.1.0"),
                    description=data.get("description", ""),
                    author=data.get("author", ""),
                    permissions=[PluginPermission(p) for p in data.get("permissions", [])],
                    tools=data.get("tools", []),
                    hooks=data.get("hooks", []),
                    entry_point=data.get("entry_point", ""),
                )
                errors = manifest.validate()
                if errors:
                    logger.warning("Plugin %s validation failed: %s", manifest.name, errors)
                    continue
                self._manifests[manifest.name] = manifest
                discovered.append(manifest)
            except Exception as e:
                logger.warning("Failed to load plugin from %s: %s", manifest_path, e)

        return discovered

    def get(self, name: str) -> PluginManifest | None:
        return self._manifests.get(name)

    @property
    def count(self) -> int:
        return len(self._manifests)
