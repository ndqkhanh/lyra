"""Contract tests for :class:`SubagentRegistry` (v1.7.3).

The registry is the backing store for the ``/agents`` and ``/spawn``
slash commands: each spawn registers a :class:`SubagentRecord` with a
stable id, records state transitions, and stores the final
``TaskResult`` dict. The registry is deliberately agnostic about
*where* the fork runs — it takes an injectable ``task`` callable so
tests can exercise dispatch semantics without instantiating an LLM or
an :class:`AgentLoop`.

Invariants tested:

- Empty registry lists nothing and doesn't raise.
- ``spawn(description)`` returns a fresh record with a monotonically
  assigned id and state ``"pending"`` before dispatch / ``"done"``
  after sync dispatch.
- Spawned records are visible via ``list_all()`` and findable by id.
- The task callable is invoked with the description and the
  subagent_type kwarg; any extra kwargs passed through.
- When the task callable raises, the record lands in state
  ``"failed"`` with the exception stringified in ``error``.
- ``cancel(id)`` on a pending record marks it ``"cancelled"`` and
  the task callable is never invoked.
"""
from __future__ import annotations

import pytest

from lyra_core.subagent.registry import (
    SubagentRecord,
    SubagentRegistry,
)


def _succeeding_task(description: str, **kwargs) -> dict:
    return {
        "subagent_type": kwargs.get("subagent_type", "general"),
        "final_text": f"ok: {description}",
        "iterations": 1,
        "tool_calls": [],
        "stopped_by": "end_turn",
    }


def _failing_task(description: str, **kwargs) -> dict:
    raise RuntimeError("boom: " + description)


# ---- empty state --------------------------------------------------- #


def test_empty_registry_lists_empty() -> None:
    reg = SubagentRegistry(task=_succeeding_task)
    assert reg.list_all() == []


# ---- spawn + list roundtrip --------------------------------------- #


def test_spawn_registers_and_returns_record() -> None:
    reg = SubagentRegistry(task=_succeeding_task)

    rec = reg.spawn("explore the worktree manager")

    assert isinstance(rec, SubagentRecord)
    assert rec.id.startswith("sub-")
    assert rec.description == "explore the worktree manager"
    assert rec.state == "done"
    assert rec.result is not None
    assert rec.result["final_text"].startswith("ok: ")

    listed = reg.list_all()
    assert len(listed) == 1
    assert listed[0].id == rec.id


# ---- id uniqueness & ordering ------------------------------------- #


def test_spawn_assigns_unique_incrementing_ids() -> None:
    reg = SubagentRegistry(task=_succeeding_task)

    a = reg.spawn("first")
    b = reg.spawn("second")

    assert a.id != b.id
    # Natural-sorted id ordering matches insertion order.
    listed_ids = [r.id for r in reg.list_all()]
    assert listed_ids == [a.id, b.id]


# ---- subagent_type + extra kwargs forwarded ----------------------- #


def test_spawn_forwards_subagent_type_and_extra_kwargs() -> None:
    seen_kwargs: list[dict] = []

    def _spy(description: str, **kwargs):
        seen_kwargs.append(dict(kwargs))
        return {
            "subagent_type": kwargs.get("subagent_type", "general"),
            "final_text": description,
            "iterations": 1,
            "tool_calls": [],
            "stopped_by": "end_turn",
        }

    reg = SubagentRegistry(task=_spy)
    reg.spawn(
        "plan the refactor",
        subagent_type="plan",
        max_iterations=42,
        worktree=False,
    )

    assert len(seen_kwargs) == 1
    kw = seen_kwargs[0]
    assert kw["subagent_type"] == "plan"
    assert kw["max_iterations"] == 42
    assert kw["worktree"] is False


# ---- failure bookkeeping ------------------------------------------ #


def test_spawn_records_failure_when_task_raises() -> None:
    reg = SubagentRegistry(task=_failing_task)

    rec = reg.spawn("crash please")

    assert rec.state == "failed"
    assert rec.error is not None
    assert "boom" in rec.error
    assert rec.result is None


# ---- get(id) ------------------------------------------------------- #


def test_get_returns_record_by_id_and_none_for_unknown() -> None:
    reg = SubagentRegistry(task=_succeeding_task)
    rec = reg.spawn("indexing")

    assert reg.get(rec.id) is rec
    assert reg.get("sub-999999") is None


# ---- cancel(id) ---------------------------------------------------- #


def test_cancel_marks_pending_record_cancelled() -> None:
    """``cancel`` on a freshly-reserved record prevents dispatch."""
    reg = SubagentRegistry(task=_succeeding_task)

    rec = reg.reserve("to be cancelled")
    assert rec.state == "pending"

    ok = reg.cancel(rec.id)
    assert ok is True
    assert rec.state == "cancelled"

    # Calling dispatch on a cancelled record must be a no-op.
    reg.dispatch(rec.id)
    assert rec.state == "cancelled"


def test_cancel_returns_false_for_done_record() -> None:
    reg = SubagentRegistry(task=_succeeding_task)
    rec = reg.spawn("finished")

    assert reg.cancel(rec.id) is False
    assert rec.state == "done"


# ---- bad input ----------------------------------------------------- #


def test_spawn_empty_description_raises() -> None:
    reg = SubagentRegistry(task=_succeeding_task)
    with pytest.raises(ValueError):
        reg.spawn("   ")
