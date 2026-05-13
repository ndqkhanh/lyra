"""Unit tests for InterruptQueue."""
from __future__ import annotations

import json
import time

import pytest

from lyra_core.transparency.interrupt_queue import InterruptQueue, _infer_severity


@pytest.mark.unit
def test_empty_queue_no_pending() -> None:
    q = InterruptQueue()
    assert q.pending_count() == 0
    assert q.get_pending() == []


@pytest.mark.unit
def test_push_creates_pending() -> None:
    q = InterruptQueue()
    q.push("id1", "s1", "Bash", json.dumps({"args": {"command": "ls"}}))
    assert q.pending_count() == 1


@pytest.mark.unit
def test_resolve_removes_from_pending() -> None:
    q = InterruptQueue()
    q.push("id1", "s1", "Bash")
    q.resolve("id1")
    assert q.pending_count() == 0


@pytest.mark.unit
def test_critical_sorted_before_medium() -> None:
    q = InterruptQueue()
    q.push("low", "s1", "Read", json.dumps({"args": {"command": "cat file.txt"}}))
    q.push("crit", "s2", "Bash", json.dumps({"args": {"command": "rm -rf /"}}))
    pending = q.get_pending()
    assert pending[0].interrupt_id == "crit"


@pytest.mark.unit
def test_infer_severity_rm_rf() -> None:
    assert _infer_severity("Bash", {"args": {"command": "rm -rf build/"}}) == "critical"


@pytest.mark.unit
def test_infer_severity_low_read() -> None:
    assert _infer_severity("Read", {}) == "low"


@pytest.mark.unit
def test_clear_resolved_shrinks_dict() -> None:
    q = InterruptQueue()
    q.push("id1", "s1", "Bash")
    q.push("id2", "s2", "Edit")
    q.resolve("id1")
    q.clear_resolved()
    assert "id1" not in q._items
    assert "id2" in q._items
