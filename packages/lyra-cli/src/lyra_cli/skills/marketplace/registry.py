"""
Skill Registry - Central metadata storage for skills.

Provides:
- Skill metadata storage (name, version, author, description, tags)
- Dependency tracking
- Version history
- Download statistics
- JSON/YAML export/import
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Protocol


@dataclass
class SkillVersion:
    """Version information for a skill."""

    version: str
    release_date: str
    changelog: str
    download_url: str
    checksum: str  # SHA256 hash
    dependencies: list[str] = field(default_factory=list)
    min_lyra_version: str | None = None


@dataclass
class RegistryMetadata:
    """Metadata for registry operations."""

    total_downloads: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    verified: bool = False
    security_scan_date: str | None = None
    security_issues: list[str] = field(default_factory=list)


@dataclass
class SkillPackage:
    """Complete skill package with all metadata."""

    name: str
    author: str
    description: str
    category: str
    tags: list[str]
    versions: list[SkillVersion]
    current_version: str
    homepage: str | None = None
    repository: str | None = None
    license: str = "MIT"
    metadata: RegistryMetadata = field(default_factory=RegistryMetadata)

    def get_version(self, version: str) -> SkillVersion | None:
        """Get specific version."""
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def get_latest_version(self) -> SkillVersion | None:
        """Get the latest version."""
        return self.get_version(self.current_version)


class RegistryStorage(Protocol):
    """Protocol for registry storage backends."""

    def save(self, package: SkillPackage) -> None:
        """Save a skill package."""
        ...

    def load(self, name: str) -> SkillPackage | None:
        """Load a skill package by name."""
        ...

    def list_all(self) -> list[str]:
        """List all skill names."""
        ...

    def delete(self, name: str) -> bool:
        """Delete a skill package."""
        ...


class FileSystemStorage:
    """File system based registry storage."""

    def __init__(self, registry_dir: Path):
        self.registry_dir = registry_dir
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, name: str) -> Path:
        """Get file path for a skill."""
        return self.registry_dir / f"{name}.json"

    def save(self, package: SkillPackage) -> None:
        """Save a skill package."""
        path = self._get_path(package.name)
        data = asdict(package)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, name: str) -> SkillPackage | None:
        """Load a skill package by name."""
        path = self._get_path(name)
        if not path.exists():
            return None

        with open(path) as f:
            data = json.load(f)

        # Reconstruct nested dataclasses
        versions = [SkillVersion(**v) for v in data["versions"]]
        metadata = RegistryMetadata(**data["metadata"])

        return SkillPackage(
            name=data["name"],
            author=data["author"],
            description=data["description"],
            category=data["category"],
            tags=data["tags"],
            versions=versions,
            current_version=data["current_version"],
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            license=data.get("license", "MIT"),
            metadata=metadata,
        )

    def list_all(self) -> list[str]:
        """List all skill names."""
        return [p.stem for p in self.registry_dir.glob("*.json")]

    def delete(self, name: str) -> bool:
        """Delete a skill package."""
        path = self._get_path(name)
        if path.exists():
            path.unlink()
            return True
        return False


class SkillRegistry:
    """
    Central registry for skill packages.

    Features:
    - Store and retrieve skill metadata
    - Track versions and dependencies
    - Download statistics
    - Security verification status
    """

    def __init__(self, storage: RegistryStorage | None = None):
        if storage is None:
            # Default to file system storage
            registry_dir = Path.home() / ".lyra" / "skill_registry"
            storage = FileSystemStorage(registry_dir)
        self.storage = storage

    def register(self, package: SkillPackage) -> None:
        """
        Register a new skill package.

        Args:
            package: Skill package to register
        """
        # Update metadata
        package.metadata.last_updated = datetime.now().isoformat()
        self.storage.save(package)

    def get(self, name: str) -> SkillPackage | None:
        """
        Get a skill package by name.

        Args:
            name: Skill name

        Returns:
            SkillPackage or None if not found
        """
        return self.storage.load(name)

    def update_version(
        self,
        name: str,
        version: SkillVersion,
        set_as_current: bool = True,
    ) -> bool:
        """
        Add a new version to a skill.

        Args:
            name: Skill name
            version: New version to add
            set_as_current: Whether to set as current version

        Returns:
            True if successful
        """
        package = self.get(name)
        if not package:
            return False

        # Check if version already exists
        if any(v.version == version.version for v in package.versions):
            return False

        package.versions.append(version)
        if set_as_current:
            package.current_version = version.version

        package.metadata.last_updated = datetime.now().isoformat()
        self.storage.save(package)
        return True

    def increment_downloads(self, name: str, count: int = 1) -> bool:
        """
        Increment download count.

        Args:
            name: Skill name
            count: Number to increment by

        Returns:
            True if successful
        """
        package = self.get(name)
        if not package:
            return False

        package.metadata.total_downloads += count
        package.metadata.last_updated = datetime.now().isoformat()
        self.storage.save(package)
        return True

    def mark_verified(self, name: str, verified: bool = True) -> bool:
        """
        Mark a skill as verified.

        Args:
            name: Skill name
            verified: Verification status

        Returns:
            True if successful
        """
        package = self.get(name)
        if not package:
            return False

        package.metadata.verified = verified
        package.metadata.last_updated = datetime.now().isoformat()
        self.storage.save(package)
        return True

    def update_security_scan(
        self,
        name: str,
        issues: list[str] | None = None,
    ) -> bool:
        """
        Update security scan results.

        Args:
            name: Skill name
            issues: List of security issues found

        Returns:
            True if successful
        """
        package = self.get(name)
        if not package:
            return False

        package.metadata.security_scan_date = datetime.now().isoformat()
        package.metadata.security_issues = issues or []
        self.storage.save(package)
        return True

    def list_all(self) -> list[str]:
        """
        List all registered skill names.

        Returns:
            List of skill names
        """
        return self.storage.list_all()

    def search_by_tag(self, tag: str) -> list[SkillPackage]:
        """
        Search skills by tag.

        Args:
            tag: Tag to search for

        Returns:
            List of matching packages
        """
        results = []
        for name in self.list_all():
            package = self.get(name)
            if package and tag.lower() in [t.lower() for t in package.tags]:
                results.append(package)
        return results

    def search_by_category(self, category: str) -> list[SkillPackage]:
        """
        Search skills by category.

        Args:
            category: Category to search for

        Returns:
            List of matching packages
        """
        results = []
        for name in self.list_all():
            package = self.get(name)
            if package and package.category.lower() == category.lower():
                results.append(package)
        return results

    def search_by_author(self, author: str) -> list[SkillPackage]:
        """
        Search skills by author.

        Args:
            author: Author to search for

        Returns:
            List of matching packages
        """
        results = []
        for name in self.list_all():
            package = self.get(name)
            if package and author.lower() in package.author.lower():
                results.append(package)
        return results

    def get_most_downloaded(self, limit: int = 10) -> list[SkillPackage]:
        """
        Get most downloaded skills.

        Args:
            limit: Maximum number to return

        Returns:
            List of packages sorted by downloads
        """
        packages = []
        for name in self.list_all():
            package = self.get(name)
            if package:
                packages.append(package)

        packages.sort(key=lambda p: p.metadata.total_downloads, reverse=True)
        return packages[:limit]

    def get_recently_updated(self, limit: int = 10) -> list[SkillPackage]:
        """
        Get recently updated skills.

        Args:
            limit: Maximum number to return

        Returns:
            List of packages sorted by update date
        """
        packages = []
        for name in self.list_all():
            package = self.get(name)
            if package:
                packages.append(package)

        packages.sort(key=lambda p: p.metadata.last_updated, reverse=True)
        return packages[:limit]

    def export_to_json(self, output_path: Path) -> None:
        """
        Export entire registry to JSON.

        Args:
            output_path: Path to output file
        """
        packages = []
        for name in self.list_all():
            package = self.get(name)
            if package:
                packages.append(asdict(package))

        with open(output_path, "w") as f:
            json.dump(packages, f, indent=2)

    def import_from_json(self, input_path: Path) -> int:
        """
        Import registry from JSON.

        Args:
            input_path: Path to input file

        Returns:
            Number of packages imported
        """
        with open(input_path) as f:
            data = json.load(f)

        count = 0
        for pkg_data in data:
            # Reconstruct nested dataclasses
            versions = [SkillVersion(**v) for v in pkg_data["versions"]]
            metadata = RegistryMetadata(**pkg_data["metadata"])

            package = SkillPackage(
                name=pkg_data["name"],
                author=pkg_data["author"],
                description=pkg_data["description"],
                category=pkg_data["category"],
                tags=pkg_data["tags"],
                versions=versions,
                current_version=pkg_data["current_version"],
                homepage=pkg_data.get("homepage"),
                repository=pkg_data.get("repository"),
                license=pkg_data.get("license", "MIT"),
                metadata=metadata,
            )

            self.register(package)
            count += 1

        return count

    def delete(self, name: str) -> bool:
        """
        Delete a skill from registry.

        Args:
            name: Skill name

        Returns:
            True if successful
        """
        return self.storage.delete(name)
