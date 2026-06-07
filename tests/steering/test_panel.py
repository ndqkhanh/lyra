"""Tests for steering panel."""
import pytest
from lyra.steering.panel import SteerPanel, SteerAction, ApprovalGate
from lyra.steering.interrupt import InterruptHandler, InterruptSignal


class TestApprovalGate:
    def test_auto_approve(self):
        gate = ApprovalGate(auto_approve_patterns=["read_file"])
        assert gate.needs_approval("read_file /tmp/test") is False

    def test_require_approval(self):
        gate = ApprovalGate(require_approval_patterns=["write_file"])
        assert gate.needs_approval("write_file /tmp/test") is True

    def test_deny_pattern(self):
        gate = ApprovalGate(deny_patterns=["rm -rf"])
        assert gate.needs_approval("rm -rf /") is False  # Denied entirely

    def test_request_and_approve(self):
        gate = ApprovalGate()
        gate.request_approval("req-1", "write_file /tmp/x", {})
        assert gate.pending_count == 1
        assert gate.approve("req-1") is True
        assert gate.pending_count == 0

    def test_request_and_reject(self):
        gate = ApprovalGate()
        gate.request_approval("req-1", "write_file /tmp/x", {})
        assert gate.reject("req-1", "unsafe path") is True
        assert gate.pending_count == 0

    def test_pending_requests(self):
        gate = ApprovalGate()
        gate.request_approval("req-1", "action-1", {"key": "val"})
        pending = gate.pending_requests()
        assert len(pending) == 1
        assert pending[0]["id"] == "req-1"


class TestSteerPanel:
    def test_peek_unknown_session(self):
        panel = SteerPanel()
        assert panel.peek("unknown") is None

    def test_update_and_peek(self):
        panel = SteerPanel()
        panel.update_state("s1", {"status": "working"})
        assert panel.peek("s1") == {"status": "working"}

    def test_redirect(self):
        panel = SteerPanel()
        panel.update_state("s1", {"status": "working"})
        assert panel.redirect("s1", "try different approach") is True
        assert panel.peek("s1")["redirect"] == "try different approach"

    def test_redirect_unknown_session(self):
        panel = SteerPanel()
        assert panel.redirect("unknown", "new direction") is False

    def test_request_decision(self):
        panel = SteerPanel()
        result = panel.request_decision("s1", "Which path?", ["A", "B"])
        assert result is None  # Async — human responds via UI

    def test_remove_session(self):
        panel = SteerPanel()
        panel.update_state("s1", {})
        panel.remove_session("s1")
        assert panel.peek("s1") is None


class TestInterruptHandler:
    def test_initial_no_signal(self):
        handler = InterruptHandler()
        assert handler.current_signal is None
        assert handler.is_paused is False

    def test_send_pause(self):
        handler = InterruptHandler()
        handler.send(InterruptSignal.PAUSE)
        assert handler.is_paused is True

    def test_send_abort(self):
        handler = InterruptHandler()
        handler.send(InterruptSignal.ABORT)
        assert handler.current_signal == InterruptSignal.ABORT

    def test_clear(self):
        handler = InterruptHandler()
        handler.send(InterruptSignal.PAUSE)
        handler.clear()
        assert handler.current_signal is None

    def test_checkpoint_save_restore(self):
        handler = InterruptHandler()
        handler.save_checkpoint("before-edit", {"file": "x.py", "line": 42})
        restored = handler.restore_checkpoint("before-edit")
        assert restored == {"file": "x.py", "line": 42}

    def test_restore_nonexistent(self):
        handler = InterruptHandler()
        assert handler.restore_checkpoint("nope") is None

    def test_list_checkpoints(self):
        handler = InterruptHandler()
        handler.save_checkpoint("a", {})
        handler.save_checkpoint("b", {})
        assert handler.list_checkpoints() == ["a", "b"]

    def test_barge_in_detection(self):
        handler = InterruptHandler()
        assert handler.handle_barge_in("stop please") == InterruptSignal.BARGE_IN
        assert handler.handle_barge_in("wait a moment") == InterruptSignal.BARGE_IN
        assert handler.handle_barge_in("cancel that") == InterruptSignal.BARGE_IN
        assert handler.handle_barge_in("continue please") is None

    def test_auto_resume_initial(self):
        handler = InterruptHandler()
        assert handler.should_auto_resume() is False
