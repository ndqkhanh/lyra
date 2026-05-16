"""Registry client for skill marketplace."""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests


@dataclass
class SkillMetadata:
    """Metadata for a skill package."""

    name: str
    version: str
    description: str
    author: str
    repository: str
    tags: list[str]
    dependencies: dict
    download_url: str


class RegistryClient:
    """Client for interacting with skill registries."""

    def __init__(self, config_path: Path):
        """Initialize registry client.

        Args:
            config_path: Path to registry configuration file
        """
        self.config_path = config_path
        self.cache_dir = config_path.parent / "cache" / "registry"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load registry configuration."""
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return self._default_config()

    def _default_config(self) -> dict:
        """Return default registry configuration."""
        return {
            "registries": [
                {
                    "name": "official",
                    "url": "https://registry.lyra.ai/index.json",
                    "enabled": True,
                    "priority": 1,
                }
            ],
            "cache_ttl": 3600,
            "auto_update_check": True,
        }

    def fetch_index(self, registry_name: str) -> dict:
        """Fetch registry index with caching.

        Args:
            registry_name: Name of the registry to fetch

        Returns:
            Registry index as dict

        Raises:
            ValueError: If registry not found
            requests.RequestException: If network request fails
        """
        cache_file = self.cache_dir / f"{registry_name}-index.json"

        # Check cache
        if cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < self.config["cache_ttl"]:
                return json.loads(cache_file.read_text())

        # Fetch from remote
        registry = next(
            (r for r in self.config["registries"] if r["name"] == registry_name),
            None,
        )
        if not registry:
            raise ValueError(f"Registry '{registry_name}' not found")

        response = requests.get(registry["url"], timeout=10)
        response.raise_for_status()
        index = response.json()

        # Update cache
        cache_file.write_text(json.dumps(index, indent=2))

        return index

    def search_skills(
        self, query: Optional[str] = None, tag: Optional[str] = None
    ) -> list[SkillMetadata]:
        """Search for skills across all enabled registries.

        Args:
            query: Optional search query (matches name and description)
            tag: Optional tag filter

        Returns:
            List of matching skill metadata
        """
        results = []

        for registry in self.config["registries"]:
            if not registry["enabled"]:
                continue
            try:
                index = self.fetch_index(registry["name"])
                for skill_name, skill_data in index["skills"].items():
                    # Filter by query
                    if query and query.lower() not in skill_name.lower() and query.lower() not in skill_data["description"].lower():
                        continue

                    # Filter by tag
                    if tag and tag not in skill_data.get("tags", []):
                        continue

                    results.append(SkillMetadata(**skill_data))
            except Exception as e:
                print(f"Warning: Failed to fetch from {registry['name']}: {e}")

        return results

    def download_skill(self, name: str, version: Optional[str] = None) -> dict:
        """Download skill package from registry.

        Args:
            name: Skill name
            version: Optional specific version (defaults to latest)

        Returns:
            Skill package as dict

        Raises:
            ValueError: If skill not found or version mismatch
            requests.RequestException: If download fails
        """
        # Find skill in registries
        for registry in self.config["registries"]:
            if not registry["enabled"]:
                continue

            index = self.fetch_index(registry["name"])
            if name in index["skills"]:
                skill_meta = index["skills"][name]

                # Use specified version or latest
                if version and version != skill_meta["version"]:
                    # TODO: Support version history
                    raise ValueError(f"Version {version} not found for {name}")

                # Download skill package
                response = requests.get(skill_meta["download_url"], timeout=10)
                response.raise_for_status()
                skill_package = response.json()

                # Cache downloaded package
                cache_file = (
                    self.cache_dir / "skills" / f"{name}-{skill_meta['version']}.json"
                )
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(skill_package, indent=2))

                return skill_package

        raise ValueError(f"Skill '{name}' not found in any enabled registry")

    def check_updates(
        self, installed_skills: dict[str, str]
    ) -> dict[str, tuple[str, str]]:
        """Check for updates to installed skills.

        Args:
            installed_skills: Dict of {skill_name: current_version}

        Returns:
            Dict of {skill_name: (current_version, latest_version)} for skills with updates
        """
        updates = {}

        for skill_name, current_version in installed_skills.items():
            try:
                # Find latest version in registries
                for registry in self.config["registries"]:
                    if not registry["enabled"]:
                        continue

                    index = self.fetch_index(registry["name"])
                    if skill_name in index["skills"]:
                        latest_version = index["skills"][skill_name]["version"]
                        if self._is_newer_version(latest_version, current_version):
                            updates[skill_name] = (current_version, latest_version)
                        break
            except Exception:
                continue

        return updates

    def _is_newer_version(self, v1: str, v2: str) -> bool:
        """Compare semantic versions.

        Args:
            v1: First version string
            v2: Second version string

        Returns:
            True if v1 is newer than v2
        """

        def parse_version(v: str) -> tuple[int, ...]:
            return tuple(int(x) for x in v.split("."))

        return parse_version(v1) > parse_version(v2)
