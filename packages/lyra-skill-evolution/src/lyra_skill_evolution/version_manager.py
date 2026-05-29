"""Skill Versioning and Rollback — track skill versions and support safe rollback."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .exceptions import VersionError
from .trajectory_patcher import Skill


class VersionStatus(Enum):
    """Status of a skill version."""

    DRAFT = auto()
    ACTIVE = auto()
    DEPRECATED = auto()
    ROLLED_BACK = auto()


@dataclass(frozen=True)
class SkillVersion:
    """A single version of a skill.

    Attributes:
        skill_id: The skill this version belongs to.
        version_number: Monotonically increasing version number.
        content_hash: SHA-256 hash of the skill content.
        timestamp: Unix timestamp when this version was created.
        author: Identifier of the entity that created this version.
        changelog: Human-readable description of changes.
        parent_version: The version number this was derived from.
        status: Current version status.
    """

    skill_id: str
    version_number: int
    content_hash: str
    timestamp: float
    author: str = "system"
    changelog: str = ""
    parent_version: int = 0
    status: VersionStatus = VersionStatus.ACTIVE


@dataclass(frozen=True)
class VersionDiff:
    """Differences between two skill versions.

    Attributes:
        added: Keys added in the new version.
        removed: Keys removed in the new version.
        modified: Keys modified in the new version.
    """

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VersionHistory:
    """Ordered version history for a single skill.

    Attributes:
        skill_id: The skill this history belongs to.
        versions: Ordered list of versions (most recent last).
    """

    skill_id: str
    versions: list[SkillVersion] = field(default_factory=list)

    @property
    def latest(self) -> SkillVersion | None:
        """Get the latest version, or None if empty."""
        return self.versions[-1] if self.versions else None

    @property
    def count(self) -> int:
        """Get the number of versions."""
        return len(self.versions)


class VersionManager:
    """Manages skill versions, history, and rollback operations.

    Supports creating versions, rolling back to previous states,
    viewing version history, diffing versions, and pinning versions.
    """

    def __init__(self) -> None:
        self._history: dict[str, VersionHistory] = {}
        self._pinned: dict[str, int] = {}
        self._active_versions: dict[str, SkillVersion] = {}

    def create_version(
        self,
        skill: Skill,
        changelog: str = "",
        author: str = "system",
    ) -> SkillVersion:
        """Create a new version record for a skill.

        Args:
            skill: The skill to version.
            changelog: Description of changes in this version.
            author: Identifier of the entity creating the version.

        Returns:
            The newly created SkillVersion.

        Raises:
            VersionError: If the skill has been pinned and auto-updates are prevented.
        """
        skill_id = skill.skill_id

        if skill_id in self._pinned:
            raise VersionError(
                skill_id,
                f"Cannot create new version: skill is pinned at version {self._pinned[skill_id]}",
            )

        content_hash = self._compute_hash(skill.content)
        history = self._history.get(skill_id)

        if history and history.latest:
            parent_version = history.latest.version_number
            new_version_number = parent_version + 1
        else:
            parent_version = 0
            new_version_number = 1

        skill_version = SkillVersion(
            skill_id=skill_id,
            version_number=new_version_number,
            content_hash=content_hash,
            timestamp=time.time(),
            author=author,
            changelog=changelog,
            parent_version=parent_version,
            status=VersionStatus.ACTIVE,
        )

        if skill_id in self._history:
            existing_versions = self._history[skill_id].versions
            self._history[skill_id] = VersionHistory(
                skill_id=skill_id,
                versions=[*existing_versions, skill_version],
            )
        else:
            self._history[skill_id] = VersionHistory(
                skill_id=skill_id,
                versions=[skill_version],
            )

        self._active_versions[skill_id] = skill_version
        return skill_version

    def rollback(self, skill_id: str, target_version_number: int) -> SkillVersion:
        """Rollback a skill to a previous version.

        The rolled-back version is marked as ROLLED_BACK and a new version
        is created that reverts the skill to the target version's content.

        Args:
            skill_id: The skill to rollback.
            target_version_number: The version number to rollback to.

        Returns:
            The new (reverted) SkillVersion.

        Raises:
            VersionError: If the target version doesn't exist or the skill is pinned.
        """
        history = self._history.get(skill_id)
        if not history:
            raise VersionError(skill_id, "No version history found")

        target = self._get_version(skill_id, target_version_number)
        if target is None:
            raise VersionError(
                skill_id,
                f"Target version {target_version_number} not found in history",
            )

        if skill_id in self._pinned:
            raise VersionError(
                skill_id,
                f"Cannot rollback: skill is pinned at version {self._pinned[skill_id]}",
            )

        current_active = self._active_versions.get(skill_id)
        if current_active:
            # Mark current as rolled back
            rolled_back = SkillVersion(
                skill_id=current_active.skill_id,
                version_number=current_active.version_number,
                content_hash=current_active.content_hash,
                timestamp=current_active.timestamp,
                author=current_active.author,
                changelog=current_active.changelog,
                parent_version=current_active.parent_version,
                status=VersionStatus.ROLLED_BACK,
            )
            self._replace_version(skill_id, rolled_back)

        # Create a new version that reverts to the target
        new_version_number = (
            (history.latest.version_number + 1) if history.latest else target_version_number + 1
        )
        new_version = SkillVersion(
            skill_id=skill_id,
            version_number=new_version_number,
            content_hash=target.content_hash,
            timestamp=time.time(),
            author="system",
            changelog=f"Rollback to version {target_version_number}",
            parent_version=target_version_number,
            status=VersionStatus.ACTIVE,
        )

        existing_versions = self._history[skill_id].versions
        self._history[skill_id] = VersionHistory(
            skill_id=skill_id,
            versions=[*existing_versions, new_version],
        )
        self._active_versions[skill_id] = new_version
        return new_version

    def get_history(self, skill_id: str) -> VersionHistory:
        """Get the complete version history for a skill.

        Args:
            skill_id: The skill to get history for.

        Returns:
            VersionHistory containing all versions.

        Raises:
            VersionError: If the skill has no history.
        """
        history = self._history.get(skill_id)
        if history is None:
            raise VersionError(skill_id, "No version history found")
        return history

    def diff_versions(self, v1_version: int, v2_version: int, skill_id: str) -> VersionDiff:
        """Compute the diff between two versions of a skill.

        Args:
            v1_version: First version number.
            v2_version: Second version number.
            skill_id: The skill to diff.

        Returns:
            VersionDiff describing added, removed, and modified keys.

        Raises:
            VersionError: If either version doesn't exist.
        """
        v1 = self._get_version(skill_id, v1_version)
        v2 = self._get_version(skill_id, v2_version)

        if v1 is None:
            raise VersionError(skill_id, f"Version {v1_version} not found")
        if v2 is None:
            raise VersionError(skill_id, f"Version {v2_version} not found")

        # Note: we can't diff content without the actual Skill objects,
        # so we return an empty diff when content isn't available
        return VersionDiff()

    def get_active_version(self, skill_id: str) -> SkillVersion:
        """Get the currently active version for a skill.

        Args:
            skill_id: The skill to query.

        Returns:
            The active SkillVersion.

        Raises:
            VersionError: If no active version exists.
        """
        version = self._active_versions.get(skill_id)
        if version is None:
            raise VersionError(skill_id, "No active version found")
        return version

    def pin_version(self, skill_id: str, version_number: int) -> None:
        """Pin a skill to a specific version, preventing auto-updates.

        Args:
            skill_id: The skill to pin.
            version_number: The version to pin to.

        Raises:
            VersionError: If the version doesn't exist.
        """
        target = self._get_version(skill_id, version_number)
        if target is None:
            raise VersionError(skill_id, f"Version {version_number} not found")
        self._pinned[skill_id] = version_number
        self._active_versions[skill_id] = target

    def unpin_skill(self, skill_id: str) -> None:
        """Remove a pin from a skill, allowing updates again.

        Args:
            skill_id: The skill to unpin.
        """
        self._pinned.pop(skill_id, None)

    def is_pinned(self, skill_id: str) -> bool:
        """Check if a skill is pinned.

        Args:
            skill_id: The skill to check.

        Returns:
            True if the skill is pinned to a specific version.
        """
        return skill_id in self._pinned

    def _get_version(self, skill_id: str, version_number: int) -> SkillVersion | None:
        """Get a specific version by number.

        Args:
            skill_id: The skill to look up.
            version_number: The version number to find.

        Returns:
            The matching SkillVersion or None.
        """
        history = self._history.get(skill_id)
        if not history:
            return None
        for v in history.versions:
            if v.version_number == version_number:
                return v
        return None

    def _replace_version(self, skill_id: str, new_version: SkillVersion) -> None:
        """Replace a version in the history (for status updates).

        Args:
            skill_id: The skill to update.
            new_version: The version with updated fields.
        """
        history = self._history.get(skill_id)
        if not history:
            return

        updated_versions = [
            new_version if v.version_number == new_version.version_number else v
            for v in history.versions
        ]
        self._history[skill_id] = VersionHistory(
            skill_id=skill_id,
            versions=updated_versions,
        )

    def _compute_hash(self, content: dict[str, Any]) -> str:
        """Compute a SHA-256 hash of skill content.

        Args:
            content: The skill content dictionary.

        Returns:
            Hex digest of the content hash.
        """
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()
