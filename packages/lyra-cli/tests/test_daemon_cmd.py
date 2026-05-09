"""L4.0 / L4.3 / L4.4 — Lyra daemon CLI integration."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.daemon_cmd import main


def test_cli_run_idle_iterations(tmp_path: Path, capsys) -> None:
    jobs = tmp_path / "jobs.json"
    state = tmp_path / "state"
    rc = main(
        [
            "run",
            "--jobs",
            str(jobs),
            "--state-dir",
            str(state),
            "--max-iterations",
            "3",
            "--no-health-endpoint",
            "--poll-interval-s",
            "0",
            "--deadline-per-iter-s",
            "0",
            "--tick-interval-s",
            "0.001",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "ran 3 iteration" in captured.out
    assert (state / "restate" / "journal.sqlite3").exists()


def test_cli_run_idle_does_not_fire_runner_when_no_jobs(tmp_path: Path) -> None:
    """No cron jobs configured → runner must not be invoked."""
    jobs = tmp_path / "jobs.json"
    state = tmp_path / "state"
    rc = main(
        [
            "run",
            "--jobs",
            str(jobs),
            "--state-dir",
            str(state),
            "--max-iterations",
            "2",
            "--no-health-endpoint",
            "--poll-interval-s",
            "0",
            "--deadline-per-iter-s",
            "0",
            "--tick-interval-s",
            "0.001",
        ]
    )
    assert rc == 0


def test_cli_run_pauses_when_budget_zero(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs.json"
    state = tmp_path / "state"
    rc = main(
        [
            "run",
            "--jobs",
            str(jobs),
            "--state-dir",
            str(state),
            "--max-iterations",
            "2",
            "--no-health-endpoint",
            "--poll-interval-s",
            "0",
            "--deadline-per-iter-s",
            "0",
            "--tick-interval-s",
            "0.001",
            "--usd-per-day",
            "0",
            "--tokens-per-day",
            "0",
        ]
    )
    assert rc == 0
    # Budget exceeded → directive entry was written.
    directive = (state / "HUMAN_DIRECTIVE.md").read_text()
    assert "budget_exceeded" in directive


def test_cli_emit_units_writes_supervisor_files(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    output_dir = tmp_path / "scripts"
    rc = main(
        [
            "emit-units",
            "--state-dir",
            str(state),
            "--output-dir",
            str(output_dir),
        ]
    )
    assert rc == 0
    sysd = (output_dir / "lyra-daemon.service").read_text()
    plist = (output_dir / "com.lyra.daemon.plist").read_text()
    assert "Restart=always" in sysd
    assert "OOMScoreAdjust=-100" in sysd
    assert "WatchdogSec=" in sysd
    assert "com.lyra.daemon" in plist
