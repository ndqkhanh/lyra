"""Tests for supervisor state types."""

from datetime import datetime, timezone

from src.supervisor.state import ProcessState, SessionInfo, SessionState


class TestSessionState:
    def test_values(self) -> None:
        assert SessionState.WORKING.value == "WORKING"
        assert SessionState.IDLE.value == "IDLE"
        assert SessionState.NEEDS_INPUT.value == "NEEDS_INPUT"
        assert SessionState.COMPLETED.value == "COMPLETED"
        assert SessionState.FAILED.value == "FAILED"
        assert SessionState.STOPPED.value == "STOPPED"

    def test_all_members_present(self) -> None:
        expected = {"WORKING", "IDLE", "NEEDS_INPUT", "COMPLETED", "FAILED", "STOPPED"}
        assert {m.value for m in SessionState} == expected


class TestProcessState:
    def test_values(self) -> None:
        assert ProcessState.ALIVE.value == "ALIVE"
        assert ProcessState.EXITED.value == "EXITED"
        assert ProcessState.LOOP_SLEEPING.value == "LOOP_SLEEPING"

    def test_all_members_present(self) -> None:
        expected = {"ALIVE", "EXITED", "LOOP_SLEEPING"}
        assert {m.value for m in ProcessState} == expected


class TestSessionInfo:
    def test_dataclass_fields(self) -> None:
        now = datetime.now(tz=timezone.utc)
        info = SessionInfo(
            session_id="abc123",
            name="test-session",
            state=SessionState.WORKING,
            process_state=ProcessState.ALIVE,
            working_dir="/tmp/test",
            created_at=now,
            last_active=now,
        )
        assert info.session_id == "abc123"
        assert info.name == "test-session"
        assert info.state == SessionState.WORKING
        assert info.process_state == ProcessState.ALIVE
        assert info.working_dir == "/tmp/test"
        assert info.created_at == now
        assert info.last_active == now
        assert info.pr_url is None

    def test_dataclass_frozen(self) -> None:
        now = datetime.now(tz=timezone.utc)
        info = SessionInfo(
            session_id="abc123",
            name="test",
            state=SessionState.WORKING,
            process_state=ProcessState.ALIVE,
            working_dir="/tmp",
            created_at=now,
            last_active=now,
        )
        try:
            info.state = SessionState.COMPLETED  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except Exception as exc:
            # dataclasses.FrozenInstanceError is a subclass of AttributeError
            assert isinstance(exc, AttributeError)

    def test_pr_url_optional(self) -> None:
        now = datetime.now(tz=timezone.utc)
        info = SessionInfo(
            session_id="x",
            name="x",
            state=SessionState.COMPLETED,
            process_state=ProcessState.EXITED,
            working_dir="/tmp",
            created_at=now,
            last_active=now,
            pr_url="https://github.com/example/repo/pull/42",
        )
        assert info.pr_url == "https://github.com/example/repo/pull/42"
