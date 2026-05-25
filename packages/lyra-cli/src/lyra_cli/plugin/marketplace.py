"""
Plugin Marketplace — registry and discovery for Lyra plugins.

Supports fetching from a registry index, searching by tag/kind,
and installing plugins to the local plugin directory.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from urllib.request import urlopen

from .manifest import PluginKind, PluginManifest


@dataclass
class RegistryEntry:
    """An entry in the plugin registry."""

    name: str
    version: str
    kind: PluginKind | list[PluginKind]
    description: str
    author: str = ""
    repository: str = ""
    tags: list[str] = field(default_factory=list)
    installs: int = 0
    rating: float = 0.0
    metadata: dict = field(default_factory=dict)


class PluginRegistry:
    """A local or remote plugin registry.

    Usage::

        registry = PluginRegistry()
        registry.add_index("https://plugins.lyra.dev/index.json")
        results = registry.search("theme")
        registry.install("lyra-theme-dracula")
    """

    def __init__(self, install_dir: Path | None = None) -> None:
        self._indexes: list[str] = []
        self._entries: dict[str, RegistryEntry] = {}
        self._install_dir = install_dir or Path.home() / ".lyra" / "plugins"

    def add_index(self, url: str) -> None:
        """Register a remote registry index URL."""
        self._indexes.append(url)

    def fetch_index(self, url: str | None = None) -> int:
        """Fetch and parse a registry index. Returns number of entries loaded."""
        urls = [url] if url else self._indexes
        loaded = 0
        for idx_url in urls:
            try:
                with urlopen(idx_url, timeout=10) as resp:
                    data = json.loads(resp.read())
                    for entry_data in data.get("plugins", []):
                        entry = self._parse_entry(entry_data)
                        self._entries[entry.name] = entry
                        loaded += 1
            except Exception:
                pass
        return loaded

    def search(self, query: str) -> list[RegistryEntry]:
        """Search registry entries by name, description, or tags."""
        q = query.lower()
        results: list[RegistryEntry] = []
        for entry in self._entries.values():
            if q in entry.name.lower() or q in entry.description.lower():
                results.append(entry)
            elif any(q in tag.lower() for tag in entry.tags):
                results.append(entry)
        return results

    def get(self, name: str) -> RegistryEntry | None:
        return self._entries.get(name)

    def install(self, name: str) -> bool:
        """Install a plugin from the registry to the local plugin directory."""
        entry = self._entries.get(name)
        if entry is None:
            return False

        target_dir = self._install_dir / name
        if target_dir.exists():
            shutil.rmtree(target_dir)

        if entry.repository:
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ["git", "clone", "--depth", "1", entry.repository, str(target_dir)],
                    capture_output=True,
                    timeout=60,
                    check=True,
                )
                return True
            except Exception:
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                return False

        return False

    def list_by_kind(self, kind: PluginKind) -> list[RegistryEntry]:
        results: list[RegistryEntry] = []
        for entry in self._entries.values():
            ek = entry.kind
            if isinstance(ek, list):
                if kind in ek:
                    results.append(entry)
            elif ek == kind:
                results.append(entry)
        return results

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @staticmethod
    def _parse_entry(data: dict) -> RegistryEntry:
        kind_raw = data.get("kind", "skill")
        if isinstance(kind_raw, list):
            kind: PluginKind | list[PluginKind] = [PluginKind(k) for k in kind_raw]
        else:
            kind = PluginKind(kind_raw)

        return RegistryEntry(
            name=data["name"],
            version=data.get("version", "0.0.0"),
            kind=kind,
            description=data.get("description", ""),
            author=data.get("author", ""),
            repository=data.get("repository", ""),
            tags=data.get("tags", []),
            installs=data.get("installs", 0),
            rating=data.get("rating", 0.0),
            metadata=data.get("metadata", {}),
        )

    def generate_skeleton(self, name: str, kind: PluginKind, target_dir: str | Path) -> Path:
        """Generate a plugin skeleton directory with plugin.json."""
        target = Path(target_dir) / name
        target.mkdir(parents=True, exist_ok=True)

        manifest = PluginManifest(
            name=name,
            version="0.1.0",
            kind=kind,
            description=f"{name} — a Lyra {kind.value} plugin",
            entry_point="__init__.py",
        )

        manifest_path = target / "plugin.json"
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))

        (target / "__init__.py").write_text(
            f"\"\"\"{name} — Lyra {kind.value} plugin.\"\"\"\n"
        )

        return target
