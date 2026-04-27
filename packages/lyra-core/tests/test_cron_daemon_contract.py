"""Contract tests for the real :class:`CronDaemon` (v1.7.3).

v1.7.2 shipped :class:`CronStore` + :class:`Schedule` primitives but
never the background runner. This pass adds :class:`CronDaemon` —
a deterministic tick loop that:

1. Finds every ``active`` job whose ``next_run_at`` is ``<= now``.
2. Runs the job through an injected ``runner`` callable.
3. Updates ``last_run_at`` + ``next_run_at`` via the job's Schedule.
4. Removes one-shot (``once``) jobs after their single firing.
5. Isolates runner failures so one bad job can't starve the others.

The daemon supports ``tick(now=...)`` for pure unit tests *and*
``start()`` / ``stop()`` for the real background thread. Tests only
exercise ``tick`` so we never depend on wall clock.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


UTC = timezone.utc


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


@pytest.fixture
def jobs_path(tmp_path: Path) -> Path:
    return tmp_path / "cron" / "jobs.json"


def test_tick_skips_jobs_not_yet_due(jobs_path: Path) -> None:
    from lyra_core.cron import CronStore
    from lyra_core.cron.daemon import CronDaemon

    store = CronStore(jobs_path=jobs_path)
    future = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    now = datetime(2026, 4, 30, 9, 0, tzinfo=UTC)

    job = store.add(prompt="hi", schedule="every 1h")
    store._mutate(job.id, next_run_at=_iso(future))

    runs: list[str] = []
    daemon = CronDaemon(store=store, runner=lambda j: runs.append(j.id))

    daemon.tick(now=now)
    assert runs == []


def test_tick_fires_due_recurring_job_and_advances_next_run(jobs_path: Path) -> None:
    from lyra_core.cron import CronStore
    from lyra_core.cron.daemon import CronDaemon

    store = CronStore(jobs_path=jobs_path)
    now = datetime(2026, 4, 30, 9, 0, tzinfo=UTC)
    job = store.add(prompt="ping", schedule="every 30m")
    store._mutate(job.id, next_run_at=_iso(now - timedelta(seconds=1)))

    runs: list[str] = []
    daemon = CronDaemon(
        store=store,
        runner=lambda j: runs.append(j.id),
        clock=lambda: now,
    )
    daemon.tick(now=now)

    assert runs == [job.id]
    reloaded = store.get(job.id)
    assert reloaded.last_run_at is not None
    assert reloaded.next_run_at is not None
    assert datetime.fromisoformat(reloaded.next_run_at) > now


def test_tick_removes_one_shot_jobs_after_firing(jobs_path: Path) -> None:
    from lyra_core.cron import CronStore
    from lyra_core.cron.daemon import CronDaemon

    store = CronStore(jobs_path=jobs_path)
    now = datetime(2026, 4, 30, 9, 0, tzinfo=UTC)
    job = store.add(prompt="one-shot", schedule="5s")
    store._mutate(job.id, next_run_at=_iso(now - timedelta(seconds=1)))

    runs: list[str] = []
    daemon = CronDaemon(store=store, runner=lambda j: runs.append(j.id))
    daemon.tick(now=now)

    assert runs == [job.id]
    with pytest.raises(KeyError):
        store.get(job.id)


def test_tick_skips_paused_jobs(jobs_path: Path) -> None:
    from lyra_core.cron import CronStore
    from lyra_core.cron.daemon import CronDaemon

    store = CronStore(jobs_path=jobs_path)
    now = datetime(2026, 4, 30, 9, 0, tzinfo=UTC)
    job = store.add(prompt="paused", schedule="every 5m")
    store._mutate(
        job.id,
        next_run_at=_iso(now - timedelta(seconds=1)),
        state="paused",
    )

    runs: list[str] = []
    daemon = CronDaemon(store=store, runner=lambda j: runs.append(j.id))
    daemon.tick(now=now)

    assert runs == []


def test_runner_exception_is_isolated_other_jobs_still_fire(jobs_path: Path) -> None:
    from lyra_core.cron import CronStore
    from lyra_core.cron.daemon import CronDaemon

    store = CronStore(jobs_path=jobs_path)
    now = datetime(2026, 4, 30, 9, 0, tzinfo=UTC)
    bad = store.add(prompt="bad", schedule="every 1m")
    good = store.add(prompt="good", schedule="every 1m")
    for j in (bad, good):
        store._mutate(j.id, next_run_at=_iso(now - timedelta(seconds=1)))

    fired: list[str] = []

    def runner(job):
        if job.id == bad.id:
            raise RuntimeError("boom")
        fired.append(job.id)

    daemon = CronDaemon(store=store, runner=runner)
    daemon.tick(now=now)

    assert fired == [good.id]
    # The failed job still gets rescheduled so a transient runner
    # error isn't fatal.
    assert store.get(bad.id).next_run_at is not None


def test_tick_uses_clock_when_now_omitted(jobs_path: Path) -> None:
    from lyra_core.cron import CronStore
    from lyra_core.cron.daemon import CronDaemon

    store = CronStore(jobs_path=jobs_path)
    fixed_now = datetime(2026, 4, 30, 9, 0, tzinfo=UTC)
    job = store.add(prompt="x", schedule="every 1m")
    store._mutate(job.id, next_run_at=_iso(fixed_now - timedelta(seconds=1)))

    runs: list[str] = []
    daemon = CronDaemon(
        store=store,
        runner=lambda j: runs.append(j.id),
        clock=lambda: fixed_now,
    )
    daemon.tick()  # no explicit ``now`` — daemon consults clock
    assert runs == [job.id]


def test_start_stop_lifecycle_is_idempotent(jobs_path: Path) -> None:
    """Smoke check on the background mode: start → stop must
    terminate the thread quickly without raising."""
    from lyra_core.cron import CronStore
    from lyra_core.cron.daemon import CronDaemon

    store = CronStore(jobs_path=jobs_path)
    daemon = CronDaemon(
        store=store,
        runner=lambda j: None,
        tick_interval=0.01,
    )
    daemon.start()
    try:
        assert daemon.is_running() is True
        # Double start should be a no-op, not raise.
        daemon.start()
    finally:
        daemon.stop()
    assert daemon.is_running() is False
