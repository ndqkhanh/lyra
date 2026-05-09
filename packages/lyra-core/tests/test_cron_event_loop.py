"""L312-6 — cron sleep-mode + after-event triggers tests."""
from __future__ import annotations

import os
import signal
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lyra_core.cron.daemon import CronDaemon
from lyra_core.cron.store import CronStore, CronJob
from lyra_core.cron.triggers import (
    AfterSessionTrigger,
    GitPushTrigger,
    SignalTrigger,
)


UTC = timezone.utc


# --- Helpers --------------------------------------------------------- #


@pytest.fixture
def store(tmp_path: Path) -> CronStore:
    return CronStore(jobs_path=tmp_path / "cron.json")


def _add_job(store: CronStore, *, job_id: str, schedule: str, next_at: datetime) -> CronJob:
    """Helper to insert a job and arm its next_run_at."""
    job = store.add(prompt=f"job-{job_id}", schedule=schedule, name=job_id)
    store.mark_run(
        job.id,
        last_run_at="",
        next_run_at=next_at.astimezone(UTC).isoformat(),
    )
    return store.get(job.id)


# --- 1. next_fire_at returns earliest active next_run_at ------------- #


def test_next_fire_at_returns_earliest(store: CronStore):
    now = datetime.now(UTC)
    _add_job(store, job_id="late", schedule="0 0 * * *", next_at=now + timedelta(hours=2))
    _add_job(store, job_id="soon", schedule="0 0 * * *", next_at=now + timedelta(minutes=5))
    _add_job(store, job_id="latest", schedule="0 0 * * *", next_at=now + timedelta(days=1))

    daemon = CronDaemon(store=store, runner=lambda j: None)
    earliest = daemon.next_fire_at(now=now)
    assert earliest is not None
    assert earliest - now < timedelta(minutes=10)


# --- 2. next_fire_at returns None when no active jobs ---------------- #


def test_next_fire_at_none_when_no_jobs(store: CronStore):
    daemon = CronDaemon(store=store, runner=lambda j: None)
    assert daemon.next_fire_at(now=datetime.now(UTC)) is None


# --- 3. run_event_loop fires when next_fire arrives ------------------ #


def test_run_event_loop_fires_when_due(store: CronStore):
    now = datetime.now(UTC)
    _add_job(store, job_id="A", schedule="0 0 * * *", next_at=now + timedelta(seconds=0.1))

    fired_log: list[str] = []
    daemon = CronDaemon(
        store=store,
        runner=lambda j: fired_log.append(j.name),
        clock=lambda: datetime.now(UTC),
        tick_interval=0.05,
    )

    th = threading.Thread(target=daemon.run_event_loop, kwargs={"idle_recheck_s": 0.05})
    th.start()
    # Wait > MIN_SLEEP_S (1.0) to give the daemon time to fire.
    time.sleep(1.6)
    daemon.stop(timeout=2.0)
    th.join(timeout=2.0)
    assert "A" in fired_log


# --- 4. run_event_loop wakes on stop event --------------------------- #


def test_run_event_loop_wakes_on_stop(store: CronStore):
    now = datetime.now(UTC)
    # A schedule far in the future so the daemon would otherwise sleep long.
    _add_job(store, job_id="far", schedule="0 0 * * *",
             next_at=now + timedelta(hours=1))

    daemon = CronDaemon(store=store, runner=lambda j: None,
                        clock=lambda: datetime.now(UTC))
    th = threading.Thread(target=daemon.run_event_loop, kwargs={"idle_recheck_s": 60.0})
    th.start()
    time.sleep(0.05)
    started = time.time()
    daemon.stop(timeout=2.0)
    th.join(timeout=2.0)
    elapsed = time.time() - started
    assert elapsed < 1.5, "daemon should wake immediately on stop event"
    assert not th.is_alive()


# --- 5. run_event_loop with no jobs idles cheaply -------------------- #


def test_run_event_loop_idles_when_no_jobs(store: CronStore):
    daemon = CronDaemon(store=store, runner=lambda j: None)
    th = threading.Thread(target=daemon.run_event_loop, kwargs={"idle_recheck_s": 0.05})
    th.start()
    time.sleep(0.2)
    daemon.stop(timeout=1.0)
    th.join(timeout=1.0)
    assert not th.is_alive()


# --- 6. SignalTrigger.fired() is self-clearing ----------------------- #


@pytest.mark.skipif(not hasattr(signal, "SIGUSR1"), reason="POSIX-only")
def test_signal_trigger_self_clearing():
    trig = SignalTrigger(signum=signal.SIGUSR1)
    trig.arm()
    try:
        os.kill(os.getpid(), signal.SIGUSR1)
        time.sleep(0.05)
        assert trig.fired() is True
        # Self-clearing.
        assert trig.fired() is False
    finally:
        trig.disarm()


# --- 7. SignalTrigger inactive when signum=0 ------------------------- #


def test_signal_trigger_disabled_with_signum_zero():
    trig = SignalTrigger(signum=0)
    trig.arm()
    assert trig.fired() is False


# --- 8. GitPushTrigger fires on ref mtime advance --------------------- #


def test_git_push_trigger_fires_on_mtime_advance(tmp_path: Path):
    repo = tmp_path
    ref_dir = repo / ".git" / "refs" / "heads"
    ref_dir.mkdir(parents=True)
    ref_file = ref_dir / "main"
    ref_file.write_text("0" * 40)

    trig = GitPushTrigger(repo=repo, ref="heads/main")
    trig.arm()
    assert trig.fired() is False

    # Bump mtime explicitly (some filesystems are second-resolution).
    new_mtime = ref_file.stat().st_mtime + 5.0
    os.utime(ref_file, (new_mtime, new_mtime))
    assert trig.fired() is True
    # Self-clearing: once consumed, future calls return False until next bump.
    assert trig.fired() is False


# --- 9. GitPushTrigger missing ref → no fire, no crash --------------- #


def test_git_push_trigger_missing_ref_returns_false(tmp_path: Path):
    trig = GitPushTrigger(repo=tmp_path, ref="heads/main")
    trig.arm()
    assert trig.fired() is False


# --- 10. AfterSessionTrigger fires on matching session id ------------ #


def test_after_session_trigger_matches_id():
    trig = AfterSessionTrigger(session_id="sess-7")
    assert trig.fired() is False
    trig.notify_session_end("sess-other")
    assert trig.fired() is False
    trig.notify_session_end("sess-7")
    assert trig.fired() is True
    # Self-clearing.
    assert trig.fired() is False


# --- 11. min-sleep floor — sleep-deprivation defence ----------------- #


def test_min_sleep_floor_prevents_busy_loop(store: CronStore):
    """A misconfigured next-fire in the past should still respect the
    1-second min-sleep floor; the daemon never busy-loops."""
    now = datetime.now(UTC)
    # Schedule in the past — daemon would compute negative sleep_s.
    _add_job(store, job_id="past", schedule="0 0 * * *",
             next_at=now - timedelta(seconds=10))

    fired_log: list[str] = []
    daemon = CronDaemon(
        store=store, runner=lambda j: fired_log.append(j.id),
        clock=lambda: datetime.now(UTC),
    )
    th = threading.Thread(target=daemon.run_event_loop)
    th.start()
    time.sleep(0.2)
    daemon.stop(timeout=2.0)
    th.join(timeout=2.0)
    # Started=0.2s; min-sleep=1s; so the past job should NOT fire yet.
    assert not fired_log


# --- 12. Stop without start — daemon does not error ------------------ #


def test_daemon_stop_without_start_is_safe(store: CronStore):
    daemon = CronDaemon(store=store, runner=lambda j: None)
    daemon.stop()  # no-op
