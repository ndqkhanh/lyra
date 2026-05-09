"""End-to-end REPL wiring: ``/cron …`` through :class:`InteractiveSession`."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.session import InteractiveSession


@pytest.fixture
def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> InteractiveSession:
    jobs = tmp_path / "jobs.json"
    monkeypatch.setenv("LYRA_CRON_JOBS_PATH", str(jobs))
    return InteractiveSession(repo_root=tmp_path)


def test_cron_is_in_registry(session: InteractiveSession) -> None:
    from lyra_cli.interactive.session import COMMAND_REGISTRY

    names = {c.name for c in COMMAND_REGISTRY}
    assert "cron" in names


def test_slash_cron_list_empty(session: InteractiveSession) -> None:
    result = session.dispatch("/cron")
    assert "no" in result.output.lower()


def test_slash_cron_add_and_list(session: InteractiveSession) -> None:
    r1 = session.dispatch("/cron add 'every 1h' 'Check feeds'")
    assert "added" in r1.output.lower()
    r2 = session.dispatch("/cron list")
    assert "every 1h" in r2.output
    assert "Check feeds" in r2.output


def test_slash_cron_pause_resume_remove(session: InteractiveSession) -> None:
    session.dispatch("/cron add 30m 'hello'")
    list_out = session.dispatch("/cron list").output
    job_id = [
        line.split()[0]
        for line in list_out.splitlines()
        if line and not line.startswith("id ")
    ][0]

    assert "paused" in session.dispatch(f"/cron pause {job_id}").output.lower()
    assert "resumed" in session.dispatch(f"/cron resume {job_id}").output.lower()
    assert "removed" in session.dispatch(f"/cron remove {job_id}").output.lower()


def test_slash_cron_unknown_subcommand_is_friendly(session: InteractiveSession) -> None:
    r = session.dispatch("/cron teleport")
    assert "unknown cron subcommand" in r.output.lower()


def test_slash_cron_bad_quoting_is_friendly(session: InteractiveSession) -> None:
    r = session.dispatch("/cron add 'unterminated")
    assert "bad quoting" in r.output.lower()
