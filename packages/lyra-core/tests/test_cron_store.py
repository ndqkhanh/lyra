"""Contract tests for ``lyra_core.cron.store.CronStore``.

The store is a JSON-backed persistence layer for scheduled jobs
(equivalent to ``~/.hermes/cron/jobs.json``). It must:

- round-trip jobs through disk, preserving id, prompt, schedule, skills,
  state, and run metadata;
- support CRUD plus pause/resume/edit as first-class verbs;
- never lose a job on a crash mid-write (atomic rename).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.cron.store import CronJob, CronStore


def test_add_then_list_round_trip(tmp_path: Path) -> None:
    store = CronStore(jobs_path=tmp_path / "jobs.json")
    j = store.add(
        prompt="Check feeds",
        schedule="every 1h",
        skills=["blogwatcher"],
        name="Morning feeds",
    )
    assert j.id
    assert j.state == "active"

    jobs = store.list()
    assert len(jobs) == 1
    assert jobs[0].id == j.id
    assert jobs[0].prompt == "Check feeds"
    assert jobs[0].skills == ["blogwatcher"]


def test_remove_by_id(tmp_path: Path) -> None:
    store = CronStore(jobs_path=tmp_path / "jobs.json")
    j = store.add(prompt="x", schedule="30m")
    removed = store.remove(j.id)
    assert removed is True
    assert store.list() == []


def test_remove_unknown_returns_false(tmp_path: Path) -> None:
    store = CronStore(jobs_path=tmp_path / "jobs.json")
    assert store.remove("does-not-exist") is False


def test_pause_and_resume(tmp_path: Path) -> None:
    store = CronStore(jobs_path=tmp_path / "jobs.json")
    j = store.add(prompt="x", schedule="every 1h")
    assert store.pause(j.id).state == "paused"
    assert store.resume(j.id).state == "active"


def test_edit_prompt_and_schedule(tmp_path: Path) -> None:
    store = CronStore(jobs_path=tmp_path / "jobs.json")
    j = store.add(prompt="old prompt", schedule="every 1h")
    updated = store.edit(j.id, prompt="new prompt", schedule="every 4h")
    assert updated.prompt == "new prompt"
    assert updated.schedule == "every 4h"


def test_edit_skills_list_replaces(tmp_path: Path) -> None:
    store = CronStore(jobs_path=tmp_path / "jobs.json")
    j = store.add(prompt="x", schedule="every 1h", skills=["a"])
    updated = store.edit(j.id, skills=["b", "c"])
    assert updated.skills == ["b", "c"]


def test_edit_add_and_remove_skill(tmp_path: Path) -> None:
    store = CronStore(jobs_path=tmp_path / "jobs.json")
    j = store.add(prompt="x", schedule="every 1h", skills=["a"])
    store.add_skill(j.id, "b")
    store.add_skill(j.id, "c")
    after_add = store.get(j.id)
    assert after_add.skills == ["a", "b", "c"]

    store.remove_skill(j.id, "b")
    after_remove = store.get(j.id)
    assert after_remove.skills == ["a", "c"]


def test_persistence_across_reopens(tmp_path: Path) -> None:
    p = tmp_path / "jobs.json"
    store = CronStore(jobs_path=p)
    j = store.add(prompt="survives restart", schedule="every 1h")

    reopened = CronStore(jobs_path=p)
    assert reopened.get(j.id).prompt == "survives restart"


def test_cronjob_serialisation_round_trip() -> None:
    j = CronJob(
        id="abc",
        prompt="x",
        schedule="every 1h",
        skills=["s"],
        state="active",
    )
    d = j.to_dict()
    j2 = CronJob.from_dict(d)
    assert j2 == j


def test_get_raises_on_unknown(tmp_path: Path) -> None:
    store = CronStore(jobs_path=tmp_path / "jobs.json")
    with pytest.raises(KeyError):
        store.get("nope")
