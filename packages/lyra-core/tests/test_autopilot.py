"""L312-7 — Autopilot supervisor tests.

Sixteen cases:

1. Register a new loop → state='running' in the store.
2. heartbeat() updates cum_usd, iter_count, contract_state.
3. complete() with FULFILLED → state='completed'.
4. complete() with VIOLATED → state='terminated'.
5. start_session reconciles stale running rows to pending_resume.
6. start_session is idempotent.
7. resume() on a pending_resume row → state='running'.
8. resume() on a non-pending row raises AutopilotResumeError.
9. resume() on unknown id raises KeyError.
10. register() refuses to re-register a pending_resume row.
11. register() can refresh a previously-completed row.
12. running() returns only running rows.
13. pending_resume() returns only pending_resume rows.
14. status() returns all rows regardless of state.
15. payload round-trips through JSON.
16. Crash recovery — running row + restart → pending_resume.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from lyra_core.loops.autopilot import Autopilot, AutopilotResumeError
from lyra_core.loops.store import LoopRecord, LoopStore


@pytest.fixture
def store(tmp_path: Path) -> LoopStore:
    return LoopStore(db_path=tmp_path / "loops.sqlite", stale_running_s=0.05)


@pytest.fixture
def autopilot(store: LoopStore) -> Autopilot:
    return Autopilot(store=store)


def test_register_creates_running_row(autopilot: Autopilot, tmp_path: Path):
    rec = autopilot.register(loop_id="L1", kind="loop", run_dir=tmp_path)
    assert rec.state == "running"
    assert rec.run_dir == str(tmp_path)
    assert autopilot.store.get("L1").state == "running"


def test_heartbeat_updates_telemetry(autopilot: Autopilot, tmp_path: Path):
    autopilot.register(loop_id="L1", kind="loop", run_dir=tmp_path)
    autopilot.heartbeat("L1", cum_usd=1.23, iter_count=4, contract_state="running")
    rec = autopilot.store.get("L1")
    assert rec.cum_usd == pytest.approx(1.23)
    assert rec.iter_count == 4
    assert rec.contract_state == "running"


def test_complete_fulfilled_marks_completed(autopilot: Autopilot, tmp_path: Path):
    autopilot.register(loop_id="L1", kind="ralph", run_dir=tmp_path)
    autopilot.complete("L1", contract_state="fulfilled", terminal_cause="predicate")
    rec = autopilot.store.get("L1")
    assert rec.state == "completed"
    assert rec.terminal_cause == "predicate"


def test_complete_violated_marks_terminated(autopilot: Autopilot, tmp_path: Path):
    autopilot.register(loop_id="L1", kind="ralph", run_dir=tmp_path)
    autopilot.complete("L1", contract_state="violated", terminal_cause="budget-usd")
    rec = autopilot.store.get("L1")
    assert rec.state == "terminated"
    assert rec.terminal_cause == "budget-usd"


def test_reconcile_moves_stale_running_to_pending_resume(
    store: LoopStore, autopilot: Autopilot, tmp_path: Path,
):
    autopilot.register(loop_id="L1", kind="loop", run_dir=tmp_path)
    # Wait past stale_running_s.
    time.sleep(0.1)
    new_autopilot = Autopilot(store=store)
    moved = new_autopilot.start_session()
    assert "L1" in moved
    assert store.get("L1").state == "pending_resume"


def test_start_session_idempotent(autopilot: Autopilot):
    autopilot.start_session()
    autopilot.start_session()  # no error
    assert autopilot.started


def test_resume_pending_to_running(
    store: LoopStore, autopilot: Autopilot, tmp_path: Path,
):
    autopilot.register(loop_id="L1", kind="loop", run_dir=tmp_path)
    time.sleep(0.1)
    new_autopilot = Autopilot(store=store)
    new_autopilot.start_session()
    rec = new_autopilot.resume("L1")
    assert rec.state == "running"
    assert store.get("L1").state == "running"


def test_resume_non_pending_raises(autopilot: Autopilot, tmp_path: Path):
    autopilot.register(loop_id="L1", kind="loop", run_dir=tmp_path)
    with pytest.raises(AutopilotResumeError):
        autopilot.resume("L1")


def test_resume_unknown_id_raises_key_error(autopilot: Autopilot):
    with pytest.raises(KeyError):
        autopilot.resume("nope")


def test_register_refuses_pending_resume_re_register(
    store: LoopStore, autopilot: Autopilot, tmp_path: Path,
):
    autopilot.register(loop_id="L1", kind="loop", run_dir=tmp_path)
    time.sleep(0.1)
    new_autopilot = Autopilot(store=store)
    new_autopilot.start_session()
    with pytest.raises(AutopilotResumeError):
        new_autopilot.register(loop_id="L1", kind="loop", run_dir=tmp_path)


def test_register_can_refresh_completed_row(autopilot: Autopilot, tmp_path: Path):
    autopilot.register(loop_id="L1", kind="loop", run_dir=tmp_path)
    autopilot.complete("L1", contract_state="fulfilled", terminal_cause="predicate")
    autopilot.register(loop_id="L1", kind="loop", run_dir=tmp_path)
    assert autopilot.store.get("L1").state == "running"


def test_running_returns_only_running(autopilot: Autopilot, tmp_path: Path):
    autopilot.register(loop_id="A", kind="loop", run_dir=tmp_path)
    autopilot.register(loop_id="B", kind="loop", run_dir=tmp_path)
    autopilot.complete("B", contract_state="fulfilled", terminal_cause="predicate")
    ids = {r.id for r in autopilot.running()}
    assert ids == {"A"}


def test_pending_resume_returns_only_pending(
    store: LoopStore, autopilot: Autopilot, tmp_path: Path,
):
    autopilot.register(loop_id="A", kind="loop", run_dir=tmp_path)
    time.sleep(0.1)
    new_autopilot = Autopilot(store=store)
    new_autopilot.start_session()
    ids = {r.id for r in new_autopilot.pending_resume()}
    assert ids == {"A"}


def test_status_returns_all(autopilot: Autopilot, tmp_path: Path):
    autopilot.register(loop_id="A", kind="loop", run_dir=tmp_path)
    autopilot.register(loop_id="B", kind="loop", run_dir=tmp_path)
    autopilot.complete("B", contract_state="fulfilled", terminal_cause="predicate")
    ids = {r.id for r in autopilot.status()}
    assert ids == {"A", "B"}


def test_payload_round_trips(autopilot: Autopilot, tmp_path: Path):
    payload = {"prd_path": "/tmp/prd.json", "max_iter": 50}
    autopilot.register(loop_id="L1", kind="ralph", run_dir=tmp_path, payload=payload)
    rec = autopilot.store.get("L1")
    assert rec.payload() == payload


def test_crash_recovery_running_to_pending_after_restart(
    store: LoopStore, tmp_path: Path,
):
    """Simulate: first autopilot dies → second autopilot reconciles → row in pending."""
    a1 = Autopilot(store=store)
    a1.register(loop_id="L1", kind="loop", run_dir=tmp_path)
    # Simulate crash by NOT calling complete().
    time.sleep(0.1)
    a2 = Autopilot(store=store)
    moved = a2.start_session()
    assert "L1" in moved
    assert store.get("L1").state == "pending_resume"
