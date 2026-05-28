"""Release management automation — version bumping, artifact building, release notes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class BumpType(StrEnum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


@dataclass(frozen=True)
class ReleaseResult:
    old_version: str
    new_version: str
    bump_type: BumpType
    release_notes: str = ""
    success: bool = True
    error: str = ""


@dataclass(frozen=True)
class VersionBumper:
    """Bumps semantic versions according to semver rules."""

    SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$")

    def bump(self, current_version: str, bump_type: BumpType) -> str:
        match = self.SEMVER_PATTERN.match(current_version)
        if not match:
            raise ValueError(f"Invalid semver: {current_version!r}")

        major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))

        if bump_type == BumpType.MAJOR:
            return f"{major + 1}.0.0"
        elif bump_type == BumpType.MINOR:
            return f"{major}.{minor + 1}.0"
        else:
            return f"{major}.{minor}.{patch + 1}"

    def suggest_bump(self, commit_messages: list[str]) -> BumpType:
        has_breaking = any("!" in msg.split(":", 1)[0] for msg in commit_messages)
        if has_breaking or any("BREAKING CHANGE" in msg for msg in commit_messages):
            return BumpType.MAJOR

        has_feat = any(msg.strip().lower().startswith("feat") for msg in commit_messages)
        if has_feat:
            return BumpType.MINOR

        return BumpType.PATCH


@dataclass
class ReleaseManager:
    """Manages the release process including version bumping and notes."""

    version_bumper: VersionBumper = field(default_factory=VersionBumper)

    def release(
        self,
        current_version: str,
        bump_type: BumpType | None = None,
        commit_messages: list[str] | None = None,
        release_notes: str = "",
    ) -> ReleaseResult:
        try:
            if bump_type is None and commit_messages:
                bump_type = self.version_bumper.suggest_bump(commit_messages)
            elif bump_type is None:
                bump_type = BumpType.PATCH

            new_version = self.version_bumper.bump(current_version, bump_type)
            return ReleaseResult(
                old_version=current_version,
                new_version=new_version,
                bump_type=bump_type,
                release_notes=release_notes,
            )
        except ValueError as e:
            return ReleaseResult(
                old_version=current_version,
                new_version=current_version,
                bump_type=BumpType.PATCH,
                success=False,
                error=str(e),
            )
