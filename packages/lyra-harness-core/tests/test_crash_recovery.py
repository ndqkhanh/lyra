"""Tests for Append-Only Context Log for Crash Recovery (P1-X #16)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lyra_harness_core.crash_recovery import (
    AppendOnlyLog,
    Checkpoint,
    CrashRecovery,
    LogEntry,
)


# ---------------------------------------------------------------------------
# LogEntry
# ---------------------------------------------------------------------------


class TestLogEntry:
    def test_minimal(self):
        e = LogEntry(sequence=0, timestamp=1.0, event="test")
        assert e.sequence == 0
        assert e.timestamp == 1.0
        assert e.event == "test"
        assert e.data == {}

    def test_with_data(self):
        e = LogEntry(sequence=5, timestamp=2.5, event="tool_call", data={"tool": "read"})
        assert e.data == {"tool": "read"}

    def test_frozen(self):
        e = LogEntry(sequence=0, timestamp=1.0, event="test")
        with pytest.raises(Exception):
            e.sequence = 99  # type: ignore[misc]

    def test_to_json(self):
        e = LogEntry(sequence=1, timestamp=1.0, event="test", data={"k": "v"})
        j = e.to_json()
        assert "seq" in j
        assert "test" in j

    def test_from_json(self):
        line = '{"seq": 3, "ts": 2.0, "event": "tool_result", "data": {"ok": true}}'
        e = LogEntry.from_json(line)
        assert e.sequence == 3
        assert e.event == "tool_result"
        assert e.data == {"ok": True}

    def test_roundtrip(self):
        original = LogEntry(sequence=7, timestamp=3.14, event="hook_fired", data={"hook": "PreToolUse"})
        restored = LogEntry.from_json(original.to_json())
        assert restored.sequence == original.sequence
        assert restored.event == original.event
        assert restored.data == original.data


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------


class TestCheckpoint:
    def test_minimal(self):
        cp = Checkpoint(sequence=10, timestamp=5.0)
        assert cp.sequence == 10
        assert cp.label == ""
        assert cp.snapshot == {}

    def test_with_data(self):
        cp = Checkpoint(
            sequence=20,
            timestamp=5.0,
            label="after_tool",
            snapshot={"state": "ok", "step": 3},
        )
        assert cp.label == "after_tool"
        assert cp.snapshot == {"state": "ok", "step": 3}

    def test_frozen(self):
        cp = Checkpoint(sequence=1, timestamp=1.0)
        with pytest.raises(Exception):
            cp.label = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AppendOnlyLog
# ---------------------------------------------------------------------------


class TestAppendOnlyLog:
    @pytest.fixture
    def log_path(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            pass
        path = Path(f.name)
        yield path
        if path.exists():
            path.unlink()

    @pytest.fixture
    def log(self, log_path):
        alog = AppendOnlyLog(log_path)
        yield alog
        alog.clear()

    def test_empty_log(self, log):
        assert log.is_empty
        assert log.entry_count == 0
        assert log.last_sequence == -1

    def test_append(self, log):
        entry = log.append("tool_call", {"tool": "read"})
        assert entry.sequence == 0
        assert entry.event == "tool_call"
        assert entry.data == {"tool": "read"}
        assert log.entry_count == 1
        assert log.last_sequence == 0

    def test_append_multiple(self, log):
        log.append("event1")
        log.append("event2")
        log.append("event3")
        assert log.entry_count == 3
        assert log.last_sequence == 2

    def test_checkpoint(self, log):
        entry = log.checkpoint(label="phase1", snapshot={"step": 5})
        assert entry.event == "__checkpoint__"
        assert entry.data["label"] == "phase1"
        assert entry.data["snapshot"] == {"step": 5}

    def test_mark_start(self, log):
        entry = log.mark_start({"session": "abc"})
        assert entry.event == "__session_start__"

    def test_mark_end(self, log):
        entry = log.mark_end({"status": "ok"})
        assert entry.event == "__session_end__"

    def test_mark_error(self, log):
        entry = log.mark_error("division by zero", {"line": 42})
        assert entry.event == "__error__"
        assert entry.data["error"] == "division by zero"
        assert entry.data["line"] == 42

    def test_entries(self, log):
        log.append("e1")
        log.append("e2")
        log.append("e3")
        entries = log.entries()
        assert len(entries) == 3
        assert [e.sequence for e in entries] == [0, 1, 2]

    def test_entries_since(self, log):
        log.append("e0")
        log.append("e1")
        log.append("e2")
        log.append("e3")
        since = log.entries_since(1)
        assert len(since) == 2
        assert [e.sequence for e in since] == [2, 3]

    def test_entries_since_none(self, log):
        log.append("e0")
        since = log.entries_since(0)
        assert len(since) == 0

    def test_checkpoints(self, log):
        log.append("e1")
        log.checkpoint(label="cp1")
        log.append("e2")
        log.checkpoint(label="cp2")
        cps = log.checkpoints()
        assert len(cps) == 2
        assert cps[0].label == "cp1"
        assert cps[1].label == "cp2"

    def test_last_checkpoint(self, log):
        assert log.last_checkpoint() is None
        log.checkpoint(label="first")
        log.checkpoint(label="second")
        assert log.last_checkpoint().label == "second"  # type: ignore[union-attr]

    def test_replay_until_checkpoint_no_cps(self, log):
        log.append("e1")
        log.append("e2")
        cp, after = log.replay_until_checkpoint()
        assert cp is None
        assert len(after) == 2

    def test_replay_until_checkpoint_with_cps(self, log):
        log.append("before_cp")
        log.checkpoint(label="mid", snapshot={"count": 1})
        log.append("after_cp1")
        log.append("after_cp2")
        log.checkpoint(label="final", snapshot={"count": 3})

        cp, after = log.replay_until_checkpoint()
        assert cp is not None
        assert cp.label == "final"
        assert cp.snapshot == {"count": 3}
        assert len(after) == 0  # nothing after the last checkpoint

    def test_replay_entries_after_checkpoint(self, log):
        log.checkpoint(label="cp1", snapshot={"step": 1})
        log.append("step2")
        log.append("step3")

        cp, after = log.replay_until_checkpoint()
        assert cp is not None
        assert cp.label == "cp1"
        assert len(after) == 2
        assert [e.event for e in after] == ["step2", "step3"]

    def test_entries_by_event(self, log):
        log.append("type_a")
        log.append("type_b")
        log.append("type_a")
        log.append("type_c")
        a_entries = log.entries_by_event("type_a")
        assert len(a_entries) == 2

    def test_size_bytes(self, log):
        assert log.size_bytes == 0
        log.append("e1", {"key": "value"})
        assert log.size_bytes > 0

    def test_clear(self, log):
        log.append("e1")
        log.checkpoint()
        log.clear()
        assert log.is_empty
        assert log.entry_count == 0
        assert log.last_sequence == -1

    def test_truncate_before(self, log):
        for i in range(10):
            log.append(f"event_{i}")
        assert log.entry_count == 10
        removed = log.truncate_before(5)
        assert removed == 5
        assert log.entry_count == 5
        sequences = [e.sequence for e in log.entries()]
        assert sequences == [5, 6, 7, 8, 9]

    def test_truncate_before_all(self, log):
        for i in range(3):
            log.append(f"event_{i}")
        removed = log.truncate_before(10)
        assert removed == 3
        assert log.is_empty

    def test_truncate_before_none(self, log):
        for i in range(3):
            log.append(f"event_{i}")
        removed = log.truncate_before(0)
        assert removed == 0
        assert log.entry_count == 3

    def test_persistence_across_instances(self, log, log_path):
        log.append("e1", {"k": "v"})
        log.checkpoint(label="test")

        # New instance on same file
        log2 = AppendOnlyLog(log_path)
        assert log2.entry_count == 2
        assert log2.last_sequence == 1
        entries = log2.entries()
        assert entries[0].event == "e1"
        assert entries[1].event == "__checkpoint__"

        log2.clear()

    def test_durable_write(self, log, log_path):
        """After append, data is immediately visible on disk."""
        log.append("crash_test", {"important": True})

        # Read the file directly
        content = log_path.read_text()
        assert "crash_test" in content
        assert "important" in content

    def test_large_log(self, log):
        """Handle a log with many entries."""
        for i in range(100):
            log.append(f"event_{i % 10}", {"index": i})
        assert log.entry_count == 100
        assert log.last_sequence == 99
        cps = log.checkpoints()
        assert len(cps) == 0  # no explicit checkpoints

    def test_event_order_preserved(self, log):
        events = ["start", "step1", "step2", "checkpoint", "step3", "end"]
        expected = ["start", "step1", "step2", "__checkpoint__", "step3", "end"]
        for e in events:
            if e == "checkpoint":
                log.checkpoint(label=e)
            else:
                log.append(e)
        recovered = [e.event for e in log.entries()]
        assert recovered == expected


# ---------------------------------------------------------------------------
# CrashRecovery
# ---------------------------------------------------------------------------


class TestCrashRecovery:
    @pytest.fixture
    def log_path(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            pass
        path = Path(f.name)
        yield path
        if path.exists():
            path.unlink()

    @pytest.fixture
    def alog(self, log_path):
        alog = AppendOnlyLog(log_path)
        yield alog
        alog.clear()

    @pytest.fixture
    def recovery(self, alog):
        return CrashRecovery(alog)

    def test_clean_shutdown_detected(self, recovery):
        recovery.begin_session()
        recovery.end_session()
        assert recovery.was_clean_shutdown

    def test_dirty_shutdown_detected(self, recovery):
        recovery.begin_session()
        recovery.log.append("tool_call")
        # No end_session — simulates crash
        assert not recovery.was_clean_shutdown

    def test_empty_log_not_clean_shutdown(self, recovery):
        assert not recovery.was_clean_shutdown

    def test_begin_session(self, recovery):
        entry = recovery.begin_session({"user": "test"})
        assert entry.event == "__session_start__"

    def test_end_session(self, recovery):
        recovery.begin_session()
        entry = recovery.end_session()
        assert entry.event == "__session_end__"

    def test_last_error(self, recovery):
        assert recovery.last_error is None
        recovery.log.mark_error("something broke")
        recovery.log.mark_error("still broken")
        err = recovery.last_error
        assert err is not None
        assert err.data["error"] == "still broken"

    def test_replay(self, recovery):
        recovery.begin_session()
        recovery.log.checkpoint(label="phase1", snapshot={"steps": 5})
        recovery.log.append("step6")
        recovery.log.append("step7")

        cp, after = recovery.replay()
        assert cp is not None
        assert cp.label == "phase1"
        assert cp.snapshot == {"steps": 5}
        assert [e.event for e in after] == ["step6", "step7"]

    def test_replay_no_checkpoints(self, recovery):
        recovery.begin_session()
        recovery.log.append("e1")
        recovery.log.append("e2")

        cp, after = recovery.replay()
        assert cp is None
        assert len(after) == 3  # session_start + e1 + e2

    def test_last_session_entries(self, recovery):
        recovery.begin_session({"id": "s1"})
        recovery.log.append("work1")
        recovery.end_session()

        recovery.begin_session({"id": "s2"})
        recovery.log.append("work2")

        entries = recovery.last_session_entries()
        events = [e.event for e in entries]
        assert "__session_start__" in events
        assert "work2" in events
        # Should NOT include work1
        assert "work1" not in events

    def test_session_count(self, recovery):
        assert recovery.session_count() == 0
        recovery.begin_session()
        recovery.end_session()
        recovery.begin_session()
        assert recovery.session_count() == 2

    def test_error_count(self, recovery):
        assert recovery.error_count() == 0
        recovery.log.mark_error("err1")
        recovery.log.mark_error("err2")
        assert recovery.error_count() == 2

    def test_is_empty(self, recovery):
        assert recovery.is_empty
        recovery.begin_session()
        assert not recovery.is_empty

    def test_clear(self, recovery):
        recovery.begin_session()
        recovery.log.append("work")
        recovery.clear()
        assert recovery.is_empty


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestCrashRecoveryIntegration:
    def test_crash_recovery_workflow(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            pass
        log_path = Path(f.name)

        try:
            # Simulate a session that crashes
            log = AppendOnlyLog(log_path)
            recovery = CrashRecovery(log)

            recovery.begin_session({"task": "implement feature X"})
            log.checkpoint(label="after_planning", snapshot={"files_created": 3})
            log.append("write_code", {"file": "a.py"})
            log.append("write_code", {"file": "b.py"})
            log.checkpoint(label="after_coding", snapshot={"files_created": 5})
            log.append("run_tests", {"passed": True})
            # CRASH — no end_session

            # New process starts, detects crash
            log2 = AppendOnlyLog(log_path)
            recovery2 = CrashRecovery(log2)

            assert not recovery2.was_clean_shutdown
            assert recovery2.session_count() == 1

            cp, pending = recovery2.replay()
            assert cp is not None
            assert cp.label == "after_coding"
            assert cp.snapshot == {"files_created": 5}
            assert len(pending) == 1
            assert pending[0].event == "run_tests"

            # Resume: re-apply pending, then start new session
            recovery2.begin_session({"task": "resume feature X"})
            recovery2.end_session()

            assert recovery2.was_clean_shutdown
        finally:
            log_path.unlink(missing_ok=True)

    def test_multiple_crash_resilience(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            pass
        log_path = Path(f.name)

        try:
            log = AppendOnlyLog(log_path)
            recovery = CrashRecovery(log)

            for session in range(3):
                recovery.begin_session({"session": session})
                log.append(f"work_{session}_a")
                log.checkpoint(label=f"cp_{session}")
                log.append(f"work_{session}_b")
                # Crash each time
                assert not recovery.was_clean_shutdown

            assert recovery.session_count() == 3
            assert recovery.log.entry_count > 0

            # Final clean session
            recovery.begin_session({"session": "final"})
            recovery.end_session()
            assert recovery.was_clean_shutdown
        finally:
            log_path.unlink(missing_ok=True)

    def test_error_recovery(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            pass
        log_path = Path(f.name)

        try:
            log = AppendOnlyLog(log_path)
            recovery = CrashRecovery(log)

            recovery.begin_session()
            log.append("step1", {"status": "ok"})
            log.mark_error("network timeout", {"retry": 1})
            log.append("step2", {"status": "retrying"})
            log.mark_error("network timeout", {"retry": 2})

            assert recovery.error_count() == 2
            last_err = recovery.last_error
            assert last_err is not None
            assert last_err.data["retry"] == 2

            # Recovery can inspect errors to decide next action
            cp, pending = recovery.replay()
            assert cp is None  # no checkpoints
            assert len(pending) > 0
        finally:
            log_path.unlink(missing_ok=True)
