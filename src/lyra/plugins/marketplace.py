"""
Plugin marketplace — searchable registry and installation management.

Provides PluginMarketplace for browsing, searching, installing, and
uninstalling plugins from remote or local registries.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lyra.plugins.manifest_discovery import ManifestDiscovery, ManifestPlugin
from lyra.plugins.manager import PluginManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MarketPlugin model
# ---------------------------------------------------------------------------


@dataclass
class MarketPlugin:
    """A plugin listing in the marketplace.

    Attributes:
        name: Plugin name.
        version: Latest available version.
        description: Human-readable description.
        author: Plugin author.
        tags: Categorisation tags.
        downloads: Download count.
        rating: User rating (0.0 to 5.0).
        homepage: Optional project URL.
        source_url: Optional source repository URL.
    """

    name: str
    version: str
    description: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0
    homepage: str = ""
    source_url: str = ""


# ---------------------------------------------------------------------------
# PluginMarketplace
# ---------------------------------------------------------------------------


class PluginMarketplace:
    """Searchable plugin marketplace with install/uninstall lifecycle.

    Supports both remote registries (HTTP/JSON) and local registry files.
    Installed plugins are tracked in a local registry and loaded via
    ManifestDiscovery + PluginManager.
    """

    def __init__(
        self,
        plugin_manager: PluginManager,
        install_dir: str | None = None,
        registry_url: str | None = None,
    ):
        """Initialize PluginMarketplace.

        Args:
            plugin_manager: The PluginManager to install plugins into.
            install_dir: Directory where plugins are installed locally.
                Defaults to ``plugins/`` relative to CWD.
            registry_url: Optional URL of a remote plugin registry.
        """
        self._manager = plugin_manager
        self._install_dir = Path(install_dir or (Path.cwd() / "plugins"))
        self._install_dir.mkdir(parents=True, exist_ok=True)
        self._registry_url = registry_url
        self._local_registry: dict[str, MarketPlugin] = {}
        self._discovery = ManifestDiscovery(search_paths=[str(self._install_dir)])

    # ---- registry management ------------------------------------------------

    def load_registry(self, path: str) -> int:
        """Load a local registry file (JSON list of MarketPlugin entries).

        Args:
            path: Path to a JSON registry file.

        Returns:
            Number of plugins loaded.
        """
        p = Path(path)
        if not p.exists():
            logger.warning("Registry file not found: %s", path)
            return 0
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            entries = data if isinstance(data, list) else data.get("plugins", [])
            count = 0
            for entry in entries:
                plugin = MarketPlugin(
                    name=entry.get("name", ""),
                    version=entry.get("version", "0.1.0"),
                    description=entry.get("description", ""),
                    author=entry.get("author", ""),
                    tags=entry.get("tags", []),
                    downloads=entry.get("downloads", 0),
                    rating=entry.get("rating", 0.0),
                    homepage=entry.get("homepage", ""),
                    source_url=entry.get("source_url", ""),
                )
                if plugin.name:
                    self._local_registry[plugin.name] = plugin
                    count += 1
            logger.info("Loaded %d plugins from registry %s", count, path)
            return count
        except Exception as exc:
            logger.error("Failed to load registry %s: %s", path, exc)
            return 0

    # ---- search -------------------------------------------------------------

    def search(self, query: str = "", limit: int = 20) -> list[MarketPlugin]:
        """Search the marketplace for plugins.

        Matches against name, description, author, and tags.

        Args:
            query: Search string (case-insensitive). Empty returns all.
            limit: Maximum results.

        Returns:
            List of matching MarketPlugin entries.
        """
        q = query.lower().strip()
        results: list[MarketPlugin] = []

        for plugin in self._local_registry.values():
            if not q:
                results.append(plugin)
            elif (
                q in plugin.name.lower()
                or q in plugin.description.lower()
                or q in plugin.author.lower()
                or any(q in tag.lower() for tag in plugin.tags)
            ):
                results.append(plugin)

        # Sort by rating descending, then downloads descending
        results.sort(key=lambda p: (-p.rating, -p.downloads))
        return results[:limit]

    def get_details(self, name: str) -> MarketPlugin | None:
        """Get full details for a marketplace plugin.

        Args:
            name: Plugin name.

        Returns:
            MarketPlugin entry or None.
        """
        return self._local_registry.get(name)

    # ---- install / uninstall ------------------------------------------------

    def install(self, name: str, version: str | None = None) -> ManifestPlugin | None:
        """Install a plugin from the marketplace.

        For a remote registry, this would download the plugin. For a local
        registry, copies the plugin directory to the install location.

        Args:
            name: Plugin name to install.
            version: Optional specific version (defaults to latest).

        Returns:
            ManifestPlugin if installation succeeded, None otherwise.
        """
        entry = self._local_registry.get(name)
        if entry is None:
            logger.error("Plugin %r not found in marketplace", name)
            return None

        if version and entry.version != version:
            logger.error(
                "Version %s not available for %r (latest: %s)",
                version,
                name,
                entry.version,
            )
            return None

        # Check if already installed
        installed_path = self._install_dir / name
        manifest_candidate = installed_path / "plugin.yaml"
        if manifest_candidate.exists():
            # Already installed — rediscover
            discovered = self._discovery.discover_from_file(str(manifest_candidate))
            if discovered:
                return discovered

        # Create a minimal plugin directory with manifest
        installed_path.mkdir(parents=True, exist_ok=True)
        manifest = {
            "name": name,
            "version": version or entry.version,
            "description": entry.description,
            "entry": f"{name}.py",
            "capabilities": entry.tags,
        }
        manifest_file = installed_path / "plugin.yaml"
        try:
            import yaml  # type: ignore[import-untyped]
            manifest_file.write_text(yaml.dump(manifest), encoding="utf-8")
        except ImportError:
            manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Create a stub plugin file
        plugin_file = installed_path / f"{name}.py"
        if not plugin_file.exists():
            plugin_file.write_text(
                self._stub_plugin_template(name, version or entry.version),
                encoding="utf-8",
            )

        return ManifestPlugin(
            name=name,
            version=version or entry.version,
            path=str(plugin_file),
            manifest_path=str(manifest_file),
            capabilities=entry.tags,
        )

    def uninstall(self, name: str) -> bool:
        """Uninstall a plugin, removing its files.

        Args:
            name: Plugin name to uninstall.

        Returns:
            True if the plugin was removed.
        """
        installed_path = self._install_dir / name
        if not installed_path.exists():
            logger.warning("Plugin %r is not installed", name)
            return False

        try:
            shutil.rmtree(installed_path)
            logger.info("Uninstalled plugin %r", name)
            return True
        except OSError as exc:
            logger.error("Failed to remove %s: %s", installed_path, exc)
            return False

    def list_installed(self) -> list[ManifestPlugin]:
        """List all currently installed plugins.

        Returns:
            List of ManifestPlugin entries discovered in the install directory.
        """
        return self._discovery.discover()

    def is_installed(self, name: str) -> bool:
        """Check if a plugin is installed.

        Args:
            name: Plugin name.

        Returns:
            True if installed.
        """
        return (self._install_dir / name).exists()

    @staticmethod
    def _stub_plugin_template(name: str, version: str) -> str:
        """Generate a minimal plugin stub file."""
        return (
            f'"""Plugin: {name} v{version}."""\n'
            f"from __future__ import annotations\n"
            f"from typing import Any\n\n"
            f"name: str = {name!r}\n"
            f"version: str = {version!r}\n"
            f"tools: list[Any] = []\n"
            f"hooks: list[Any] = []\n\n"
            f"async def initialize() -> None: ...\n"
            f"async def shutdown() -> None: ...\n"
        )


__all__ = [
    "MarketPlugin",
    "PluginMarketplace",
]
