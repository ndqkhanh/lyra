"""Release automation — version bumping, changelog, and release notes."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from enum import StrEnum


class BumpLevel(StrEnum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class ReleaseStatus(StrEnum):
    DRAFT = "draft"
    PREPARING = "preparing"
    READY = "ready"
    PUBLISHED = "published"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: str = ""

    def __str__(self) -> str:
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            v += f"-{self.prerelease}"
        return v

    def bump(self, level: BumpLevel) -> Version:
        if level == BumpLevel.MAJOR:
            return Version(major=self.major + 1, minor=0, patch=0)
        if level == BumpLevel.MINOR:
            return Version(major=self.major, minor=self.minor + 1, patch=0)
        return Version(major=self.major, minor=self.minor, patch=self.patch + 1)

    @classmethod
    def parse(cls, version_str: str) -> Version:
        m = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-(.+))?", version_str.strip())
        if not m:
            raise ValueError(f"Invalid version string: {version_str}")
        return cls(
            major=int(m.group(1)),
            minor=int(m.group(2)),
            patch=int(m.group(3)),
            prerelease=m.group(4) or "",
        )


@dataclass(frozen=True)
class ChangelogEntry:
    version: Version
    date: str
    changes: tuple[str, ...]
    category: str = ""  # feature, fix, breaking, etc.


@dataclass(frozen=True)
class ReleaseNotes:
    version: Version
    title: str
    highlights: tuple[str, ...]
    changelog: tuple[ChangelogEntry, ...]
    breaking_changes: tuple[str, ...]
    contributors: tuple[str, ...]
    generated_at: float


class ReleaseManager:
    """Manages semantic versioning, changelogs, and release notes.

    Usage::

        mgr = ReleaseManager(current_version="1.2.3")
        new_ver = mgr.bump_version(BumpLevel.MINOR)
        mgr.add_change("Added new routing system", category="feature")
        notes = mgr.generate_release_notes(title="Lyra v1.3.0")
    """

    def __init__(self, current_version: str) -> None:
        self._version = Version.parse(current_version)
        self._changes: list[ChangelogEntry] = []
        self._pending_changes: list[str] = []
        self._pending_categories: list[str] = []
        self._breaking: list[str] = []
        self._release_history: list[ReleaseNotes] = []

    @property
    def current_version(self) -> str:
        return str(self._version)

    def bump_version(self, level: BumpLevel) -> Version:
        self._version = self._version.bump(level)
        return self._version

    def add_change(self, description: str, category: str = "", breaking: bool = False) -> None:
        self._pending_changes.append(description)
        self._pending_categories.append(category)
        if breaking:
            self._breaking.append(description)

    def generate_release_notes(
        self,
        title: str = "",
        contributors: tuple[str, ...] = (),
    ) -> ReleaseNotes:
        if not title:
            title = f"Release {self._version}"

        entry = ChangelogEntry(
            version=self._version,
            date=time.strftime("%Y-%m-%d"),
            changes=tuple(self._pending_changes),
        )
        self._changes.append(entry)

        notes = ReleaseNotes(
            version=self._version,
            title=title,
            highlights=tuple(self._pending_changes[:3]),
            changelog=tuple(self._changes),
            breaking_changes=tuple(self._breaking),
            contributors=contributors,
            generated_at=time.time(),
        )
        self._release_history.append(notes)
        self._pending_changes = []
        self._pending_categories = []
        self._breaking = []
        return notes

    def format_notes(self, notes: ReleaseNotes, fmt: str = "markdown") -> str:
        if fmt == "markdown":
            return self._format_markdown(notes)
        return self._format_text(notes)

    @staticmethod
    def _format_markdown(notes: ReleaseNotes) -> str:
        lines = [
            f"# {notes.title}",
            "",
            f"**Version:** {notes.version}",
            "",
            "## Highlights",
            *(f"- {h}" for h in notes.highlights),
        ]
        if notes.breaking_changes:
            lines.extend(["", "## Breaking Changes", *(f"- {b}" for b in notes.breaking_changes)])
        lines.extend(["", "## Changelog"])
        for entry in notes.changelog:
            lines.append(f"\n### {entry.version} ({entry.date})")
            for change in entry.changes:
                lines.append(f"- {change}")
        if notes.contributors:
            lines.extend(["", "## Contributors", *(f"- {c}" for c in notes.contributors)])
        return "\n".join(lines)

    @staticmethod
    def _format_text(notes: ReleaseNotes) -> str:
        lines = [
            f"RELEASE: {notes.title}",
            f"Version: {notes.version}",
            "",
            "Highlights:",
            *(f"  - {h}" for h in notes.highlights),
        ]
        if notes.breaking_changes:
            lines.extend(["", "Breaking Changes:", *(f"  - {b}" for b in notes.breaking_changes)])
        return "\n".join(lines)
