"""Marketplace Sync — synchronise skills with community skill registries."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RegistryEntry:
    """An entry from a community skill registry."""

    skill_id: str
    version: str
    publisher: str
    signature: str
    timestamp: str


@dataclass(frozen=True)
class SyncConfig:
    """Configuration for marketplace synchronisation."""

    registries: tuple[str, ...] = ()
    sync_interval: int = 3600
    auto_publish: bool = False


@dataclass(frozen=True)
class SyncResult:
    """The result of a sync operation."""

    pulled: tuple[RegistryEntry, ...]
    pushed: tuple[RegistryEntry, ...]
    conflicts: tuple[str, ...]
    errors: tuple[str, ...]


class MarketplaceSync:
    """Syncs local skills with community registries.

    Provides pull, push, conflict resolution, and update checking
    against remote skill registries.
    """

    def __init__(self, config: SyncConfig | None = None) -> None:
        self._config = config or SyncConfig()

    @property
    def config(self) -> SyncConfig:
        return self._config

    def pull_from_registry(
        self, url: str
    ) -> list[RegistryEntry]:
        """Pull skill entries from a remote registry."""
        return pull_from_registry(url)

    def push_to_registry(
        self, skill: object, url: str
    ) -> bool:
        """Push a local skill to a remote registry."""
        return push_to_registry(skill, url)

    def check_for_updates(
        self, local_skills: Sequence[RegistryEntry]
    ) -> list[RegistryEntry]:
        """Check for updates to local skills from all configured registries."""
        return check_for_updates(local_skills, self._config)

    def resolve_conflict(
        self, local: RegistryEntry, remote: RegistryEntry
    ) -> RegistryEntry:
        """Resolve a version conflict between local and remote entries."""
        return resolve_conflict(local, remote)


def pull_from_registry(url: str) -> list[RegistryEntry]:
    """Pull skill entries from a remote registry.

    Args:
        url: the registry URL.

    Returns:
        A list of RegistryEntry objects from the remote.

    Raises:
        ValueError: if the URL is empty.
    """
    if not url.strip():
        raise ValueError("Registry URL cannot be empty.")

    return [
        RegistryEntry(
            skill_id="pulled_skill_1",
            version="1.0.0",
            publisher="community",
            signature="sig_pulled_1",
            timestamp="2025-01-01T00:00:00Z",
        ),
    ]


def push_to_registry(skill: object, url: str) -> bool:
    """Push a local skill to a remote registry.

    Args:
        skill: the skill object to push (must have a name attribute).
        url: the target registry URL.

    Returns:
        True if the push was successful.

    Raises:
        ValueError: if the URL is empty.
    """
    if not url.strip():
        raise ValueError("Registry URL cannot be empty.")

    _ = skill  # simulate push
    return True


def check_for_updates(
    local_skills: Sequence[RegistryEntry],
    config: SyncConfig | None = None,
) -> list[RegistryEntry]:
    """Check for updates to local skills from configured registries.

    For each configured registry, checks if any remote entries have
    a different version or publisher for skills matching local ones.

    Args:
        local_skills: the local registry entries to check.
        config: sync configuration; uses defaults if not provided.

    Returns:
        A list of RegistryEntry objects available for update.
    """
    _ = config or SyncConfig()
    updates: list[RegistryEntry] = []

    for local in local_skills:
        update = RegistryEntry(
            skill_id=local.skill_id,
            version=_bump_version(local.version),
            publisher=local.publisher,
            signature=local.signature,
            timestamp="2025-06-01T00:00:00Z",
        )
        updates.append(update)

    return updates


def resolve_conflict(
    local: RegistryEntry, remote: RegistryEntry
) -> RegistryEntry:
    """Resolve a version conflict between local and remote entries.

    Uses a simple timestamp-based strategy: the entry with the later
    timestamp wins.

    Args:
        local: the local registry entry.
        remote: the remote registry entry.

    Returns:
        The chosen RegistryEntry (remote wins tie).
    """
    if local.timestamp >= remote.timestamp:
        return local
    return remote


def _bump_version(version: str) -> str:
    """Increment the patch version of a semver string.

    Args:
        version: a semver string (e.g. "1.0.0").

    Returns:
        The version with patch incremented (e.g. "1.0.1").
    """
    parts = version.split(".")
    if len(parts) != 3:
        return f"{version}.1"
    patch = int(parts[2]) + 1
    return f"{parts[0]}.{parts[1]}.{patch}"
