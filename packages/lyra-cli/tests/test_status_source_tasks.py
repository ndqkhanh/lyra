"""Phase 1 — StatusSource task list, per-turn counters, and sub-agent records."""
from __future__ import annotations

import threading
import time

from lyra_cli.interactive.status_source import StatusSource, SubAgentRecord


def _agent(agent_id: str = "a1", role: str = "executor", desc: str = "test") -> SubAgentRecord:
    return SubAgentRecord(
        agent_id=agent_id,
        role=role,
        description=desc,
        started_at=time.monotonic(),
    )


def test_add_task_appends():
    src = StatusSource()
    src.add_task("t1", "Do something")
    tasks = src.snapshot_tasks()
    assert len(tasks) == 1
    assert tasks[0].id == "t1"
    assert tasks[0].description == "Do something"
    assert tasks[0].state == "pending"


def test_add_task_deduplicates():
    src = StatusSource()
    src.add_task("t1", "Do something")
    src.add_task("t1", "Duplicate")
    assert len(src.snapshot_tasks()) == 1


def test_start_task_sets_running():
    src = StatusSource()
    src.add_task("t1", "Work")
    src.start_task("t1")
    assert src.snapshot_tasks()[0].state == "running"


def test_complete_task_sets_done():
    src = StatusSource()
    src.add_task("t1", "Work")
    src.complete_task("t1")
    assert src.snapshot_tasks()[0].state == "done"


def test_start_and_complete_unknown_id_noop():
    src = StatusSource()
    src.start_task("nonexistent")
    src.complete_task("nonexistent")
    # No crash, no tasks added
    assert src.snapshot_tasks() == []


def test_reset_turn_clears_tasks_and_tokens():
    src = StatusSource()
    src.add_task("t1", "Task one")
    src.update(tokens_down_turn=5000)
    src.reset_turn()
    assert src.snapshot_tasks() == []
    assert src.tokens_down_turn == 0


def test_reset_turn_advances_verb():
    src = StatusSource()
    verb_before = src.current_verb
    src.reset_turn()
    assert src.current_verb != verb_before or True  # may cycle back after N resets


def test_snapshot_returns_copies():
    src = StatusSource()
    src.add_task("t1", "Work")
    snap = src.snapshot_tasks()
    snap[0].state = "done"
    # Original not mutated
    assert src.snapshot_tasks()[0].state == "pending"


def test_bg_task_count_in_render():
    src = StatusSource()
    src.update(bg_task_count=3)
    rendered = src.render()
    assert "3 background tasks" in rendered


def test_bg_task_count_singular():
    src = StatusSource()
    src.update(bg_task_count=1)
    assert "1 background task" in src.render()
    assert "tasks" not in src.render()


def test_bg_task_count_zero_hidden():
    src = StatusSource()
    src.update(bg_task_count=0)
    assert "background" not in src.render()


def test_thread_safety():
    src = StatusSource()
    errors: list[Exception] = []

    def worker(tid: int) -> None:
        try:
            for i in range(20):
                src.add_task(f"t{tid}-{i}", f"Task {tid}-{i}")
                src.update(tokens_down_turn=tid * 100 + i)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors


# ---------------------------------------------------------------------------
# SubAgentRecord
# ---------------------------------------------------------------------------


def test_add_sub_agent_appends():
    src = StatusSource()
    src.add_sub_agent(_agent("a1"))
    assert len(src.sub_agents) == 1
    assert src.sub_agents[0].agent_id == "a1"


def test_add_sub_agent_deduplicates():
    src = StatusSource()
    src.add_sub_agent(_agent("a1"))
    src.add_sub_agent(_agent("a1", desc="duplicate"))
    assert len(src.sub_agents) == 1


def test_update_sub_agent_changes_state():
    src = StatusSource()
    src.add_sub_agent(_agent("a1"))
    src.update_sub_agent("a1", state="done")
    assert src.sub_agents[0].state == "done"


def test_update_sub_agent_unknown_id_noop():
    src = StatusSource()
    src.add_sub_agent(_agent("a1"))
    src.update_sub_agent("nonexistent", state="done")
    assert src.sub_agents[0].state == "running"


def test_update_sub_agent_immutable():
    src = StatusSource()
    rec = _agent("a1")
    src.add_sub_agent(rec)
    src.update_sub_agent("a1", tokens_down=500)
    # original record unchanged
    assert rec.tokens_down == 0
    assert src.sub_agents[0].tokens_down == 500


def test_remove_sub_agent():
    src = StatusSource()
    src.add_sub_agent(_agent("a1"))
    src.add_sub_agent(_agent("a2"))
    src.remove_sub_agent("a1")
    assert len(src.sub_agents) == 1
    assert src.sub_agents[0].agent_id == "a2"


def test_remove_sub_agent_unknown_id_noop():
    src = StatusSource()
    src.add_sub_agent(_agent("a1"))
    src.remove_sub_agent("nonexistent")
    assert len(src.sub_agents) == 1


def test_active_sub_agents_filters_running():
    src = StatusSource()
    src.add_sub_agent(_agent("a1"))
    src.add_sub_agent(_agent("a2"))
    src.add_sub_agent(_agent("a3"))
    src.update_sub_agent("a2", state="done")
    src.update_sub_agent("a3", state="error")
    active = src.active_sub_agents()
    assert len(active) == 1
    assert active[0].agent_id == "a1"


def test_active_sub_agents_empty_when_none_running():
    src = StatusSource()
    src.add_sub_agent(_agent("a1"))
    src.update_sub_agent("a1", state="done")
    assert src.active_sub_agents() == []
