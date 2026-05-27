"""Team Cleanup Manager (Plan 29.6).

Handles team lifecycle termination: cleanup files, kill subprocesses/tmux
sessions, archive task state, recover from lead session crashes.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class CleanupAction(str, Enum):
    ARCHIVED = "archived"
    DELETED = "deleted"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class CleanupReport:
    team_name: str
    actions: list[CleanupRecord] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""

    @property
    def success_count(self) -> int:
        return sum(1 for a in self.actions if a.action in (CleanupAction.ARCHIVED, CleanupAction.DELETED))

    @property
    def failure_count(self) -> int:
        return sum(1 for a in self.actions if a.action == CleanupAction.FAILED)

    @property
    def summary(self) -> str:
        return f"{self.team_name}: {self.success_count} cleaned, {self.failure_count} failed"


@dataclass
class CleanupRecord:
    path: str
    action: CleanupAction
    reason: str = ""


class TeamCleanupManager:
    """Manage team lifecycle termination and cleanup.

    Operations:
    - Archive: move team state to ~/.lyra/teams/archive/{team_name}/
    - Delete: remove all team files
    - Clean: delete without archiving (for test/transient teams)
    - Recover: scan for orphaned team state from crashed sessions
    """

    ARCHIVE_DIR: str = ".lyra/teams/archive"

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir or Path.home())

    def archive(self, team_name: str) -> CleanupReport:
        """Move team directory to archive."""
        return self._cleanup(team_name, archive=True)

    def delete(self, team_name: str) -> CleanupReport:
        """Delete team directory without archiving."""
        return self._cleanup(team_name, archive=False)

    def recover_orphans(self) -> list[str]:
        """Find team directories with no active lead session."""
        teams_dir = self._base / ".lyra" / "teams"
        if not teams_dir.exists():
            return []

        orphans: list[str] = []
        for team_dir in sorted(teams_dir.iterdir()):
            if not team_dir.is_dir() or team_dir.name == "archive":
                continue

            lock_file = team_dir / ".lead.lock"
            if lock_file.exists():
                try:
                    pid = int(lock_file.read_text().strip())
                    os.kill(pid, 0)
                except (OSError, ValueError):
                    orphans.append(team_dir.name)
                    logger.warning("Orphaned team detected: %s (PID %s dead)", team_dir.name, lock_file.read_text().strip() if lock_file.exists() else "?")
            else:
                orphans.append(team_dir.name)

        return orphans

    def get_archive_list(self) -> list[dict[str, str]]:
        archive_dir = self._base / self.ARCHIVE_DIR
        if not archive_dir.exists():
            return []

        result: list[dict[str, str]] = []
        for team_dir in sorted(archive_dir.iterdir()):
            if team_dir.is_dir():
                manifest = team_dir / "manifest.json"
                archived_at = ""
                if manifest.exists():
                    try:
                        data = json.loads(manifest.read_text())
                        archived_at = data.get("archived_at", "")
                    except json.JSONDecodeError:
                        pass
                result.append({"name": team_dir.name, "archived_at": archived_at})
        return result

    def _cleanup(self, team_name: str, archive: bool) -> CleanupReport:
        report = CleanupReport(
            team_name=team_name,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        team_dir = self._base / ".lyra" / "teams" / team_name
        tasks_dir = self._base / ".lyra" / "tasks" / team_name

        if archive and team_dir.exists():
            self._archive_dir(team_dir, report)

        for directory in (team_dir, tasks_dir):
            if directory.exists():
                self._remove_dir(directory, report)

        report.completed_at = datetime.now(timezone.utc).isoformat()
        logger.info("Cleanup %s: %s", team_name, report.summary)
        return report

    def _archive_dir(self, team_dir: Path, report: CleanupReport) -> None:
        archive_root = self._base / self.ARCHIVE_DIR
        archive_root.mkdir(parents=True, exist_ok=True)

        dest = archive_root / team_dir.name
        try:
            if dest.exists():
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                dest = archive_root / f"{team_dir.name}-{timestamp}"

            shutil.copytree(team_dir, dest)
            manifest = dest / "manifest.json"
            manifest.write_text(json.dumps({
                "team_name": team_dir.name,
                "archived_at": datetime.now(timezone.utc).isoformat(),
                "original_path": str(team_dir),
            }, indent=2))

            report.actions.append(CleanupRecord(
                path=str(team_dir),
                action=CleanupAction.ARCHIVED,
                reason=f"Archived to {dest}",
            ))
        except OSError as exc:
            report.actions.append(CleanupRecord(
                path=str(team_dir),
                action=CleanupAction.FAILED,
                reason=str(exc),
            ))

    @staticmethod
    def _remove_dir(directory: Path, report: CleanupReport) -> None:
        try:
            shutil.rmtree(directory)
            report.actions.append(CleanupRecord(
                path=str(directory),
                action=CleanupAction.DELETED,
            ))
        except OSError as exc:
            report.actions.append(CleanupRecord(
                path=str(directory),
                action=CleanupAction.FAILED,
                reason=str(exc),
            ))
