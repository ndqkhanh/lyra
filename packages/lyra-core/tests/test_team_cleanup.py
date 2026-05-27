"""Tests for Team Cleanup Manager (Plan 29.6)."""

import os
import tempfile
from pathlib import Path

from lyra_core.teams.cleanup import CleanupAction, CleanupReport, TeamCleanupManager


class TestTeamCleanupManager:
    def test_archive_nonexistent_team(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = TeamCleanupManager(base_dir=tmp)
            report = mgr.archive("nonexistent_team")
            assert isinstance(report, CleanupReport)
            assert report.team_name == "nonexistent_team"

    def test_delete_nonexistent_team(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = TeamCleanupManager(base_dir=tmp)
            report = mgr.delete("nonexistent_team")
            assert isinstance(report, CleanupReport)

    def test_archive_existing_team(self):
        with tempfile.TemporaryDirectory() as tmp:
            teams_dir = f"{tmp}/.lyra/teams/test_team"
            os.makedirs(teams_dir, exist_ok=True)
            (teams_dir + "/config.json").__str__()
            with open(f"{teams_dir}/config.json", "w") as f:
                f.write('{"name": "test_team"}')

            mgr = TeamCleanupManager(base_dir=tmp)
            report = mgr.archive("test_team")

            assert report.success_count >= 1
            assert any(a.action == CleanupAction.ARCHIVED for a in report.actions)

    def test_delete_existing_team(self):
        with tempfile.TemporaryDirectory() as tmp:
            teams_dir = f"{tmp}/.lyra/teams/test_team"
            os.makedirs(teams_dir, exist_ok=True)
            with open(f"{teams_dir}/config.json", "w") as f:
                f.write('{"name": "test_team"}')

            tasks_dir = f"{tmp}/.lyra/tasks/test_team"
            os.makedirs(tasks_dir, exist_ok=True)

            mgr = TeamCleanupManager(base_dir=tmp)
            report = mgr.delete("test_team")

            assert report.success_count >= 1
            assert all(a.action != CleanupAction.ARCHIVED for a in report.actions)

    def test_recover_orphans_no_teams(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = TeamCleanupManager(base_dir=tmp)
            orphans = mgr.recover_orphans()
            assert orphans == []

    def test_recover_orphans_with_dead_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            teams_dir = Path(tmp) / ".lyra" / "teams" / "dead_team"
            teams_dir.mkdir(parents=True, exist_ok=True)
            (teams_dir / ".lead.lock").write_text("99999")  # Dead PID

            mgr = TeamCleanupManager(base_dir=tmp)
            orphans = mgr.recover_orphans()
            assert "dead_team" in orphans

    def test_recover_orphans_skips_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_dir = Path(tmp) / ".lyra" / "teams" / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)

            mgr = TeamCleanupManager(base_dir=tmp)
            orphans = mgr.recover_orphans()
            assert "archive" not in orphans

    def test_recover_orphans_no_lock_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            teams_dir = Path(tmp) / ".lyra" / "teams" / "orphan_team"
            teams_dir.mkdir(parents=True, exist_ok=True)

            mgr = TeamCleanupManager(base_dir=tmp)
            orphans = mgr.recover_orphans()
            assert "orphan_team" in orphans

    def test_cleanup_report_summary(self):
        report = CleanupReport(team_name="test")
        assert "test" in report.summary
        assert report.success_count == 0
        assert report.failure_count == 0

    def test_get_archive_list_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = TeamCleanupManager(base_dir=tmp)
            archives = mgr.get_archive_list()
            assert archives == []
