"""`/cron` slash-command wiring (hermes parity).

The handler exposes subcommands ``list``, ``add``, ``remove``, ``pause``,
``resume``, ``run``, and ``edit``. Each dispatches to the underlying
``CronStore`` through a thin injected interface so the CLI stays
test-friendly and the scheduler stays decoupled from Typer.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.cron import (
    CronCommandError,
    handle_cron,
)
from lyra_core.cron.store import CronStore


@pytest.fixture
def store(tmp_path: Path) -> CronStore:
    return CronStore(jobs_path=tmp_path / "jobs.json")


def test_add_schedules_new_job(store: CronStore) -> None:
    out = handle_cron(["add", "every 1h", "Check feeds"], store=store)
    assert "added" in out.lower()
    assert len(store.list()) == 1


def test_add_with_skill_flags(store: CronStore) -> None:
    handle_cron(
        ["add", "every 1h", "prompt", "--skill", "a", "--skill", "b"],
        store=store,
    )
    job = store.list()[0]
    assert job.skills == ["a", "b"]


def test_list_empty_says_no_jobs(store: CronStore) -> None:
    out = handle_cron(["list"], store=store)
    assert "no" in out.lower()


def test_list_prints_job_rows(store: CronStore) -> None:
    store.add(prompt="a", schedule="every 1h")
    store.add(prompt="b", schedule="30m")
    out = handle_cron(["list"], store=store)
    assert "every 1h" in out
    assert "30m" in out


def test_remove_by_id(store: CronStore) -> None:
    j = store.add(prompt="x", schedule="every 1h")
    out = handle_cron(["remove", j.id], store=store)
    assert "removed" in out.lower()
    assert store.list() == []


def test_pause_and_resume(store: CronStore) -> None:
    j = store.add(prompt="x", schedule="every 1h")
    handle_cron(["pause", j.id], store=store)
    assert store.get(j.id).state == "paused"
    handle_cron(["resume", j.id], store=store)
    assert store.get(j.id).state == "active"


def test_unknown_subcommand_raises(store: CronStore) -> None:
    with pytest.raises(CronCommandError):
        handle_cron(["teleport"], store=store)


def test_add_missing_args_raises(store: CronStore) -> None:
    with pytest.raises(CronCommandError):
        handle_cron(["add"], store=store)


def test_empty_args_is_shortcut_for_list(store: CronStore) -> None:
    out = handle_cron([], store=store)
    assert "no" in out.lower()


def test_remove_unknown_raises_friendly_error(store: CronStore) -> None:
    with pytest.raises(CronCommandError, match="not found"):
        handle_cron(["remove", "nope"], store=store)
