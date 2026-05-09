"""Tests for L311 — Anthropic Agent Teams runtime + shared task list + mailbox.

These tests are stdlib-only (no live LLM, no network); the
``Executor`` seam is wired to deterministic stubs so the runtime can
be exercised end-to-end without API keys.
"""
from __future__ import annotations

import pytest

from lyra_core.teams import (
    LeadSession,
    Mailbox,
    SharedTaskList,
    TEAMMATE_BLOCK_THRESHOLD,
    TeamCostError,
    TeammateNotFoundError,
    TeammateSpec,
)


# ---- shared task list -------------------------------------------------


def test_shared_task_list_create_pending(tmp_path):
    tl = SharedTaskList(tmp_path / "tasks")
    t = tl.create(title="review auth.py")
    assert t.state == "pending"
    assert t.owner is None
    assert t.depends_on == ()


def test_shared_task_list_create_blocked_on_deps(tmp_path):
    tl = SharedTaskList(tmp_path / "tasks")
    a = tl.create(title="design schema")
    b = tl.create(title="implement", depends_on=[a.id])
    assert b.state == "blocked"
    assert a.id in b.depends_on


def test_shared_task_list_claim_unowned(tmp_path):
    tl = SharedTaskList(tmp_path / "tasks")
    t = tl.create(title="x")
    claimed = tl.claim_unowned("alice")
    assert claimed is not None
    assert claimed.id == t.id
    # Re-claiming finds nothing — the task is now owned.
    assert tl.claim_unowned("bob") is None


def test_shared_task_list_start_and_complete(tmp_path):
    tl = SharedTaskList(tmp_path / "tasks")
    t = tl.create(title="x", owner="alice")
    started = tl.start(t.id, owner="alice")
    assert started.state == "in_progress"
    completed = tl.complete(t.id, output="done")
    assert completed.state == "completed"
    assert completed.output == "done"


def test_shared_task_list_unblocks_dependents(tmp_path):
    tl = SharedTaskList(tmp_path / "tasks")
    a = tl.create(title="a", owner="alice")
    b = tl.create(title="b", owner="alice", depends_on=[a.id])
    assert tl.get(b.id).state == "blocked"
    tl.start(a.id, owner="alice")
    tl.complete(a.id)
    # b should now be pending.
    assert tl.get(b.id).state == "pending"


def test_shared_task_list_cannot_start_completed(tmp_path):
    tl = SharedTaskList(tmp_path / "tasks")
    t = tl.create(title="x", owner="alice")
    tl.start(t.id, owner="alice")
    tl.complete(t.id)
    with pytest.raises(ValueError):
        tl.start(t.id, owner="alice")


def test_shared_task_list_summary(tmp_path):
    tl = SharedTaskList(tmp_path / "tasks")
    a = tl.create(title="a", owner="alice")
    tl.create(title="b", owner="bob")
    tl.create(title="c", depends_on=[a.id])
    snap = tl.summary()
    assert snap.pending == 2
    assert snap.blocked == 1
    assert snap.total == 3


def test_shared_task_list_fail_marks_blocked(tmp_path):
    tl = SharedTaskList(tmp_path / "tasks")
    t = tl.create(title="x", owner="alice")
    tl.start(t.id, owner="alice")
    failed = tl.fail(t.id, reason="executor timeout")
    assert failed.state == "blocked"
    assert failed.failure_reason == "executor timeout"


def test_shared_task_list_persists_round_trip(tmp_path):
    tl = SharedTaskList(tmp_path / "tasks")
    a = tl.create(title="round-trip", owner="alice", depends_on=())
    # Open a fresh instance — state must survive.
    tl2 = SharedTaskList(tmp_path / "tasks")
    re_read = tl2.get(a.id)
    assert re_read is not None
    assert re_read.title == "round-trip"
    assert re_read.owner == "alice"


# ---- mailbox ----------------------------------------------------------


def test_mailbox_send_and_read(tmp_path):
    mb = Mailbox(tmp_path / "mailbox")
    mb.ensure("alice")
    mb.send(sender="lead", recipient="alice", body="hi", kind="info")
    msgs = mb.read("alice")
    assert len(msgs) == 1
    assert msgs[0].sender == "lead"
    assert msgs[0].kind == "info"
    assert msgs[0].body.startswith("hi")


def test_mailbox_idle_kind(tmp_path):
    mb = Mailbox(tmp_path / "mailbox")
    mb.send(sender="alice", recipient="lead", body="done", kind="idle")
    msgs = mb.read("lead")
    assert msgs[0].is_idle


def test_mailbox_rejects_invalid_name(tmp_path):
    mb = Mailbox(tmp_path / "mailbox")
    with pytest.raises(ValueError):
        mb.send(sender="LEAD!!!", recipient="alice", body="x")


def test_mailbox_rejects_unknown_kind(tmp_path):
    mb = Mailbox(tmp_path / "mailbox")
    with pytest.raises(ValueError):
        mb.send(sender="lead", recipient="alice", body="x", kind="explode")  # type: ignore[arg-type]


def test_mailbox_mark_read(tmp_path):
    mb = Mailbox(tmp_path / "mailbox")
    mb.send(sender="lead", recipient="alice", body="hi")
    msgs = mb.read("alice")
    assert len(msgs) == 1
    mb.mark_read(msgs[0])
    assert mb.read("alice") == []
    assert len(mb.read("alice", include_read=True)) == 1


# ---- LeadSession spawn / cost guard ----------------------------------


def _stub_executor(spec: TeammateSpec, body: str) -> str:
    return f"<{spec.name}> {body}"


def test_lead_session_spawn_basic(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="security"))
    lead.spawn(TeammateSpec(name="performance", model="fast"))
    assert lead.teammates == ("security", "performance")


def test_lead_session_rejects_reserved_name(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    with pytest.raises(ValueError):
        lead.spawn(TeammateSpec(name="lead"))


def test_lead_session_rejects_duplicate(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="security"))
    with pytest.raises(ValueError):
        lead.spawn(TeammateSpec(name="security"))


def test_lead_session_cost_guard_blocks_at_threshold(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    for i in range(TEAMMATE_BLOCK_THRESHOLD):
        lead.spawn(TeammateSpec(name=f"t{i}"))
    with pytest.raises(TeamCostError):
        lead.spawn(TeammateSpec(name="overflow"))


def test_lead_session_cost_guard_can_be_overridden(tmp_path):
    lead = LeadSession.create(
        team_name="t",
        team_dir=tmp_path / "t",
        executor=_stub_executor,
        allow_unsafe_token_overage=True,
    )
    for i in range(TEAMMATE_BLOCK_THRESHOLD + 2):
        lead.spawn(TeammateSpec(name=f"t{i}"))
    assert len(lead.teammates) == TEAMMATE_BLOCK_THRESHOLD + 2


def test_lead_session_warn_threshold(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    for i in range(6):
        lead.spawn(TeammateSpec(name=f"t{i}"))
    assert lead.warn_cost is True


# ---- LeadSession step / run-until-idle -------------------------------


def test_lead_session_run_completes_assigned_tasks(tmp_path):
    captured: list[tuple[str, str]] = []

    def exec_(spec: TeammateSpec, body: str) -> str:
        captured.append((spec.name, body))
        return f"output-from-{spec.name}"

    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=exec_
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.spawn(TeammateSpec(name="bob"))
    lead.add_task("review module A", assign="alice", body="A body")
    lead.add_task("review module B", assign="bob", body="B body")

    n = lead.run_until_idle(timeout_s=2.0)
    assert n == 2
    # Each teammate should have run exactly its assigned task.
    assert ("alice", "A body") in captured
    assert ("bob", "B body") in captured


def test_lead_session_unassigned_task_gets_claimed(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.add_task("anyone please", body="payload")
    n = lead.run_until_idle(timeout_s=2.0)
    assert n == 1
    snap = lead.tasks.summary()
    assert snap.completed == 1


def test_lead_session_dependent_task_unblocks(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="alice"))
    a_id = lead.add_task("first", assign="alice")
    b_id = lead.add_task("second", assign="alice", depends_on=[a_id])
    # Initially only `a` is runnable.
    assert lead.tasks.get(b_id).state == "blocked"
    lead.run_until_idle(timeout_s=2.0)
    snap = lead.tasks.summary()
    assert snap.completed == 2


def test_lead_session_executor_failure_marks_blocked(tmp_path):
    def boom(spec: TeammateSpec, body: str) -> str:
        raise RuntimeError("kaboom")

    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=boom
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.add_task("doomed", assign="alice")
    lead.run_until_idle(timeout_s=2.0)
    report = lead.shutdown()
    assert report.failed == 1
    assert report.completed == 0


def test_lead_session_idle_notifications_reach_lead(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.add_task("a", assign="alice")
    lead.add_task("b", assign="alice")
    lead.run_until_idle(timeout_s=2.0)
    inbox = lead.inbox()
    idle = [m for m in inbox if m.is_idle]
    assert len(idle) == 2
    assert all(m.sender == "alice" for m in idle)


def test_lead_session_send_to_unknown_raises(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    with pytest.raises(TeammateNotFoundError):
        lead.send_to("ghost", "hi")


def test_lead_session_assign_to_unknown_raises(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    with pytest.raises(TeammateNotFoundError):
        lead.add_task("ghost task", assign="ghost")


def test_lead_session_send_to_delivers_message(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.send_to("alice", "context please")
    msgs = lead.mailbox.read("alice")
    assert len(msgs) == 1
    assert msgs[0].sender == "lead"


def test_lead_session_shutdown_report(tmp_path):
    lead = LeadSession.create(
        team_name="auth-refactor",
        team_dir=tmp_path / "t",
        executor=_stub_executor,
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.add_task("x", assign="alice")
    lead.run_until_idle(timeout_s=2.0)
    report = lead.shutdown()
    assert report.team_name == "auth-refactor"
    assert report.spawned == ("alice",)
    assert report.completed == 1
    assert report.elapsed_s >= 0.0
    d = report.as_dict()
    assert d["completed"] == 1
    assert d["team_name"] == "auth-refactor"


# ---- HIR event emission ------------------------------------------------


def test_lead_session_emits_lifecycle_events(tmp_path, monkeypatch):
    captured: list[tuple[str, dict]] = []

    def fake_emit(name: str, /, **attrs):
        captured.append((name, attrs))

    # Monkey-patch the lazily-imported events module.
    from lyra_core.hir import events

    monkeypatch.setattr(events, "emit", fake_emit)

    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.add_task("x", assign="alice")
    lead.run_until_idle(timeout_s=2.0)
    lead.shutdown()

    names = [n for n, _ in captured]
    assert "team.create" in names
    assert "team.spawn" in names
    assert "team.task_created" in names
    assert "team.task_completed" in names
    assert "team.teammate_idle" in names
    assert "team.shutdown" in names
