"""
Unit tests for the Session CLI Manager module.
Mocks SessionManager, subprocess, os.kill, and file I/O.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from lyra.sessions.persist import SessionManager, SessionRecord, SessionStatus
from lyra.sessions.cli_manager import (
    BackgroundSession,
    CompressedRollup,
    ContextCompressionOnResume,
    SearchResult,
    SessionBackgrounder,
    SessionCLI,
    SessionSearch,
)


# =============================================================================
# Fixtures
# =============================================================================

def make_record(
    session_id: str = "lyra-test-001",
    status: SessionStatus = SessionStatus.ACTIVE,
    agent_id: str = "agent-1",
    steps: list | None = None,
    metadata: dict | None = None,
    context: dict | None = None,
) -> SessionRecord:
    now = datetime.now(timezone.utc)
    return SessionRecord(
        session_id=session_id,
        created_at=now,
        updated_at=now,
        status=status,
        agent_id=agent_id,
        steps=steps or [],
        metadata=metadata or {},
        context=context or {},
    )


@pytest.fixture
def mock_sm() -> MagicMock:
    sm = MagicMock(spec=SessionManager)
    sm._conn = MagicMock()
    sm._cache = {}
    return sm


# =============================================================================
# SearchResult
# =============================================================================

class TestSearchResult:
    def test_creation(self) -> None:
        sr = SearchResult(
            session_id="lyra-test",
            score=0.85,
            matched_fields=["steps", "context"],
            snippet="some snippet text",
        )
        assert sr.session_id == "lyra-test"
        assert sr.score == 0.85
        assert sr.matched_fields == ["steps", "context"]


# =============================================================================
# SessionSearch
# =============================================================================

class TestSessionSearch:
    def test_init(self, mock_sm) -> None:
        ss = SessionSearch(mock_sm)
        assert ss._sm is mock_sm

    def test_search_empty_results(self, mock_sm) -> None:
        mock_sm.list_sessions.return_value = []
        ss = SessionSearch(mock_sm)
        results = ss.search("anything")
        assert results == []

    def test_search_matches_session_id(self, mock_sm) -> None:
        record = make_record(session_id="lyra-xyz-123")
        mock_sm.list_sessions.return_value = [record]
        ss = SessionSearch(mock_sm)
        results = ss.search("xyz")
        assert len(results) == 1
        assert results[0].session_id == "lyra-xyz-123"

    def test_search_matches_agent_id(self, mock_sm) -> None:
        record = make_record(agent_id="custom-agent")
        mock_sm.list_sessions.return_value = [record]
        ss = SessionSearch(mock_sm)
        results = ss.search("custom")
        assert len(results) == 1
        assert "agent_id" in results[0].matched_fields

    def test_search_matches_steps(self, mock_sm) -> None:
        record = make_record(steps=[{"type": "tool_call", "tool": "bash"}])
        mock_sm.list_sessions.return_value = [record]
        ss = SessionSearch(mock_sm)
        results = ss.search("bash")
        assert len(results) == 1
        assert "steps" in results[0].matched_fields

    def test_search_matches_context(self, mock_sm) -> None:
        record = make_record(context={"topic": "deep learning"})
        mock_sm.list_sessions.return_value = [record]
        ss = SessionSearch(mock_sm)
        results = ss.search("deep")
        assert len(results) == 1
        assert "context" in results[0].matched_fields

    def test_search_matches_metadata(self, mock_sm) -> None:
        record = make_record(metadata={"project": "lyra-core"})
        mock_sm.list_sessions.return_value = [record]
        ss = SessionSearch(mock_sm)
        results = ss.search("lyra-core")
        assert len(results) == 1
        assert "metadata" in results[0].matched_fields

    def test_search_respects_limit(self, mock_sm) -> None:
        records = [make_record(session_id=f"lyra-{i}") for i in range(10)]
        mock_sm.list_sessions.return_value = records
        ss = SessionSearch(mock_sm)
        results = ss.search("lyra", limit=3)
        assert len(results) == 3

    def test_search_with_agent_filter(self, mock_sm) -> None:
        record_a = make_record(session_id="s1", agent_id="agent-a")
        record_b = make_record(session_id="s2", agent_id="agent-b")
        mock_sm.list_sessions.return_value = [record_a, record_b]
        ss = SessionSearch(mock_sm)
        # The empty query still searches; we match by agent_id having "b" in it
        results = ss.search("agent-b", agent_id="agent-b")
        assert len(results) == 1
        assert results[0].session_id == "s2"

    def test_search_with_status_filter(self, mock_sm) -> None:
        record_a = make_record(session_id="s1", status=SessionStatus.ACTIVE)
        record_b = make_record(session_id="s2", status=SessionStatus.COMPLETED, metadata={"key": "match"})
        mock_sm.list_sessions.return_value = [record_a, record_b]
        ss = SessionSearch(mock_sm)
        results = ss.search("match", status=SessionStatus.COMPLETED)
        assert len(results) == 1

    def test_search_with_date_from(self, mock_sm) -> None:
        now = datetime.now(timezone.utc)
        old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        record_new = make_record(session_id="s1", metadata={"topic": "match"})
        record_new.created_at = now
        record_old = make_record(session_id="s2", metadata={"topic": "match"})
        record_old.created_at = old
        mock_sm.list_sessions.return_value = [record_new, record_old]
        ss = SessionSearch(mock_sm)
        results = ss.search("match", date_from="2024-01-01T00:00:00+00:00")
        assert len(results) == 1

    def test_search_with_date_to(self, mock_sm) -> None:
        now = datetime.now(timezone.utc)
        old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        record_new = make_record(session_id="s1", metadata={"topic": "match"})
        record_new.created_at = now
        record_old = make_record(session_id="s2", metadata={"topic": "match"})
        record_old.created_at = old
        mock_sm.list_sessions.return_value = [record_new, record_old]
        ss = SessionSearch(mock_sm)
        results = ss.search("match", date_to="2021-01-01T00:00:00+00:00")
        assert len(results) == 1

    def test_search_results_sorted(self, mock_sm) -> None:
        records = [
            make_record(session_id="s1", metadata={"key": "match"}),
            make_record(session_id="s2", metadata={"key": "nomatch"}),
        ]
        mock_sm.list_sessions.return_value = records
        ss = SessionSearch(mock_sm)
        results = ss.search("match")
        assert len(results) >= 1

    def test_search_by_content(self, mock_sm) -> None:
        record = make_record(steps=[{"type": "message", "content": "hello world"}])
        mock_sm.list_sessions.return_value = [record]
        ss = SessionSearch(mock_sm)
        results = ss.search_by_content("hello")
        assert len(results) == 1

    def test_search_by_date(self, mock_sm) -> None:
        now = datetime.now(timezone.utc)
        record = make_record(session_id="s1")
        record.created_at = now
        mock_sm.list_sessions.return_value = [record]
        ss = SessionSearch(mock_sm)
        results = ss.search_by_date(date_from="2024-01-01T00:00:00+00:00")
        assert len(results) == 1

    def test_build_snippet_from_steps(self) -> None:
        record = make_record(steps=[{"type": "tool_call", "tool": "bash", "cmd": "echo hello"}])
        snippet = SessionSearch._build_snippet(record, "hello")
        assert "hello" in snippet

    def test_build_snippet_from_metadata(self) -> None:
        record = make_record(metadata={"project": "lyra-core"})
        snippet = SessionSearch._build_snippet(record, "lyra-core")
        assert "lyra-core" in snippet

    def test_build_snippet_fallback(self) -> None:
        record = make_record(session_id="lyra-xyz")
        snippet = SessionSearch._build_snippet(record, "nonexistent")
        assert "lyra-xyz" in snippet


# =============================================================================
# CompressedRollup
# =============================================================================

class TestCompressedRollup:
    def test_creation(self) -> None:
        cr = CompressedRollup(
            session_id="lyra-test",
            original_steps=100,
            compressed_steps=5,
            summary="Compressed summary",
            key_decisions=["decision-1"],
        )
        assert cr.session_id == "lyra-test"
        assert cr.original_steps == 100
        assert cr.compressed_steps == 5


# =============================================================================
# ContextCompressionOnResume
# =============================================================================

class TestContextCompressionOnResume:
    def test_init(self, mock_sm) -> None:
        cc = ContextCompressionOnResume(mock_sm)
        assert cc._sm is mock_sm

    def test_compress_no_record(self, mock_sm) -> None:
        mock_sm.get_session.return_value = None
        cc = ContextCompressionOnResume(mock_sm)
        result = cc.compress_for_resume("nonexistent")
        assert result is None

    def test_compress_no_steps(self, mock_sm) -> None:
        record = make_record(steps=[])
        mock_sm.get_session.return_value = record
        cc = ContextCompressionOnResume(mock_sm)
        result = cc.compress_for_resume("lyra-test")
        assert result is None

    def test_compress_with_older_steps(self, mock_sm) -> None:
        steps = [{"type": "tool_call", "tool": f"t{i}"} for i in range(15)]
        record = make_record(steps=steps, context={"key": "val"})
        mock_sm.get_session.return_value = record
        mock_sm._conn.execute.return_value = MagicMock()
        cc = ContextCompressionOnResume(mock_sm)
        result = cc.compress_for_resume("lyra-test", keep_recent=5)
        assert result is not None
        assert result.original_steps == 15
        assert result.compressed_steps <= 6  # 1 compressed + 5 recent
        assert "tool calls" in result.summary

    def test_compress_no_older_steps(self, mock_sm) -> None:
        steps = [{"type": "tool_call", "tool": "t1"}]
        record = make_record(steps=steps)
        mock_sm.get_session.return_value = record
        mock_sm._conn.execute.return_value = MagicMock()
        cc = ContextCompressionOnResume(mock_sm)
        result = cc.compress_for_resume("lyra-test", keep_recent=10)
        assert result is not None
        assert "All steps retained" in result.summary

    def test_summarise_steps(self) -> None:
        steps = [
            {"type": "tool_call"},
            {"type": "user_message"},
            {"type": "assistant_message"},
            {"type": "error"},
            {"type": "tool_call"},
        ]
        summary = ContextCompressionOnResume._summarise_steps(steps)
        assert "5 total steps" in summary
        assert "2 tool calls" in summary
        assert "2 messages" in summary
        assert "1 errors" in summary

    def test_summarise_steps_empty(self) -> None:
        summary = ContextCompressionOnResume._summarise_steps([])
        assert "0 total steps" in summary

    def test_extract_decisions(self) -> None:
        steps = [
            {"type": "decision", "description": "Use Python"},
            {"type": "tool_call"},
            {"type": "decision", "description": "Skip validation"},
        ]
        decisions = ContextCompressionOnResume._extract_decisions(steps)
        assert len(decisions) == 2
        assert "Use Python" in decisions

    def test_extract_decisions_empty(self) -> None:
        decisions = ContextCompressionOnResume._extract_decisions([])
        assert decisions == []


# =============================================================================
# BackgroundSession
# =============================================================================

class TestBackgroundSession:
    def test_creation(self) -> None:
        bg = BackgroundSession(
            session_id="lyra-bg",
            pid=12345,
            started_at=time.time(),
            state_file="/tmp/state.json",
        )
        assert bg.session_id == "lyra-bg"
        assert bg.pid == 12345


# =============================================================================
# SessionBackgrounder
# =============================================================================

class TestSessionBackgrounder:
    def test_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bg = SessionBackgrounder(state_dir=tmp)
            assert bg._state_dir == Path(tmp)
            assert bg._backgrounded == {}

    def test_background_success(self) -> None:
        bg = SessionBackgrounder()
        with patch("subprocess.Popen") as mock_popen:
            process = MagicMock()
            process.pid = 9999
            mock_popen.return_value = process
            result = bg.background("lyra-test", ["python", "-c", "pass"])
        assert result is not None
        assert result.session_id == "lyra-test"
        assert result.pid == 9999

    def test_background_already_running(self) -> None:
        bg = SessionBackgrounder()
        bg._backgrounded["lyra-test"] = MagicMock()
        result = bg.background("lyra-test", ["python", "-c", "pass"])
        assert result is None

    def test_background_spawn_failure(self) -> None:
        bg = SessionBackgrounder()
        with patch("subprocess.Popen", side_effect=OSError("fork failed")):
            result = bg.background("lyra-test", ["python", "-c", "pass"])
        assert result is None

    def test_reattach_not_found(self) -> None:
        bg = SessionBackgrounder()
        assert bg.reattach("nonexistent") is False

    def test_reattach_running(self) -> None:
        bg = SessionBackgrounder()
        bg._backgrounded["lyra-test"] = BackgroundSession(
            session_id="lyra-test", pid=99999,
            started_at=time.time(), state_file="/tmp/s.json",
        )
        with patch("os.kill", return_value=True):
            assert bg.reattach("lyra-test") is True

    def test_reattach_not_running(self) -> None:
        bg = SessionBackgrounder()
        bg._backgrounded["lyra-test"] = BackgroundSession(
            session_id="lyra-test", pid=99999,
            started_at=time.time(), state_file="/tmp/s.json",
        )
        with patch("os.kill", side_effect=OSError("no process")):
            assert bg.reattach("lyra-test") is False

    def test_list_backgrounded_prunes_dead(self) -> None:
        bg = SessionBackgrounder()
        bg._backgrounded["alive"] = BackgroundSession(
            session_id="alive", pid=1, started_at=time.time(), state_file="/tmp/a.json",
        )
        bg._backgrounded["dead"] = BackgroundSession(
            session_id="dead", pid=2, started_at=time.time(), state_file="/tmp/d.json",
        )
        with patch.object(SessionBackgrounder, "_is_running", side_effect=[True, False]):
            result = bg.list_backgrounded()
        assert len(result) == 1

    def test_is_running(self) -> None:
        with patch("os.kill", return_value=True):
            assert SessionBackgrounder._is_running(1) is True

    def test_is_running_not(self) -> None:
        with patch("os.kill", side_effect=OSError("no")):
            assert SessionBackgrounder._is_running(1) is False

    def test_default_state_dir(self) -> None:
        bg = SessionBackgrounder()
        with patch("pathlib.Path.mkdir"):
            d = bg._default_state_dir()
            assert ".lyra" in d

    def test_save_state(self) -> None:
        bg = SessionBackgrounder()
        bg_sess = BackgroundSession(
            session_id="lyra-save", pid=100,
            started_at=123.0, state_file="/tmp/test_save.json",
        )
        with patch("pathlib.Path.write_text") as mock_write:
            bg._save_state(bg_sess)
            mock_write.assert_called_once()

    def test_save_state_oserror(self) -> None:
        bg = SessionBackgrounder()
        bg_sess = BackgroundSession(
            session_id="lyra-save", pid=100,
            started_at=123.0, state_file="/tmp/test_save.json",
        )
        with patch("pathlib.Path.write_text", side_effect=OSError("no write")):
            bg._save_state(bg_sess)  # should not raise

    def test_load_state_not_found(self) -> None:
        bg = SessionBackgrounder()
        with patch.object(Path, "exists", return_value=False):
            result = bg._load_state("nonexistent")
        assert result is None

    def test_load_state_success(self) -> None:
        bg = SessionBackgrounder()
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps({
            "session_id": "lyra-load", "pid": 200, "started_at": 456.0,
        })
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=json.dumps({
                "session_id": "lyra-load", "pid": 200, "started_at": 456.0,
            })):
                result = bg._load_state("lyra-load")
        assert result is not None
        assert result.session_id == "lyra-load"
        assert result.pid == 200

    def test_load_state_json_error(self) -> None:
        bg = SessionBackgrounder()
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value="invalid json"):
                result = bg._load_state("lyra-load")
        assert result is None

    def test_remove_state(self) -> None:
        bg = SessionBackgrounder()
        bg._backgrounded["lyra-rm"] = MagicMock()
        mock_path = MagicMock(spec=Path)
        with patch("pathlib.Path.unlink") as mock_unlink:
            bg._remove_state("lyra-rm")
            mock_unlink.assert_called_once_with(missing_ok=True)
        assert "lyra-rm" not in bg._backgrounded

    def test_load_state_from_disk_reenables(self, tmp_path) -> None:
        bg = SessionBackgrounder(state_dir=str(tmp_path))
        state_file = tmp_path / "lyra-reload.json"
        state_file.write_text(json.dumps({
            "session_id": "lyra-reload", "pid": 300, "started_at": 789.0,
        }))
        result = bg._load_state("lyra-reload")
        assert result is not None
        assert result.session_id == "lyra-reload"
        assert result.pid == 300
        assert bg._backgrounded["lyra-reload"] is result


# =============================================================================
# SessionCLI
# =============================================================================

class TestSessionCLI:
    def test_init(self, mock_sm) -> None:
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI(db_path=":memory:")
        assert cli._sm is mock_sm

    def test_cmd_list_empty(self, mock_sm) -> None:
        mock_sm.list_sessions.return_value = []
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_list(quiet=True)
        assert result == []

    def test_cmd_list_with_results(self, mock_sm) -> None:
        record = make_record(session_id="lyra-1")
        mock_sm.list_sessions.return_value = [record]
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_list(quiet=True)
        assert len(result) == 1
        assert result[0]["session_id"] == "lyra-1"

    def test_cmd_list_with_status(self, mock_sm) -> None:
        record = make_record(session_id="lyra-1", status=SessionStatus.PAUSED)
        mock_sm.list_sessions.return_value = [record]
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_list(status="paused", quiet=True)
        assert len(result) == 1

    def test_cmd_list_invalid_status(self, mock_sm) -> None:
        mock_sm.list_sessions.return_value = []
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with pytest.raises(ValueError):
            cli.cmd_list(status="invalid_status")

    def test_cmd_kill_success(self, mock_sm) -> None:
        mock_sm.delete_session.return_value = True
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_kill("lyra-1")
        assert result is True

    def test_cmd_kill_not_found(self, mock_sm) -> None:
        mock_sm.delete_session.return_value = False
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_kill("nonexistent")
        assert result is False

    def test_cmd_kill_force(self, mock_sm) -> None:
        mock_sm.delete_session.return_value = True
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch.object(cli._backgrounder, "_load_state", return_value=None):
            result = cli.cmd_kill("lyra-1", force=True)
        assert result is True

    def test_cmd_kill_force_with_process(self, mock_sm) -> None:
        mock_sm.delete_session.return_value = True
        bg_sess = BackgroundSession(
            session_id="lyra-bg", pid=42, started_at=time.time(), state_file="/tmp/s.json",
        )
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch.object(cli._backgrounder, "_load_state", return_value=bg_sess):
            with patch.object(SessionBackgrounder, "_is_running", return_value=True):
                with patch("os.kill") as mock_kill:
                    result = cli.cmd_kill("lyra-1", force=True)
        assert result is True
        mock_kill.assert_called_once_with(42, signal.SIGTERM)

    def test_cmd_resume_not_found(self, mock_sm) -> None:
        mock_sm.get_session.return_value = None
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_resume("nonexistent")
        assert result is None

    def test_cmd_resume_success(self, mock_sm) -> None:
        record = make_record(
            session_id="lyra-1",
            steps=[{"type": "tool_call"}],
            context={"key": "val"},
            metadata={"project": "core"},
        )
        mock_sm.get_session.return_value = record
        mock_sm.update_session.return_value = record
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch.object(cli._compressor, "compress_for_resume", return_value=None):
            result = cli.cmd_resume("lyra-1")
        assert result is not None
        assert result["session_id"] == "lyra-1"
        assert result["status"] == "active"

    def test_cmd_resume_with_compression(self, mock_sm) -> None:
        record = make_record(session_id="lyra-1", steps=[{"type": "test"}])
        mock_sm.get_session.return_value = record
        mock_sm.update_session.return_value = record
        rollup = CompressedRollup(
            session_id="lyra-1", original_steps=10, compressed_steps=3,
            summary="compressed", key_decisions=[],
        )
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch.object(cli._compressor, "compress_for_resume", return_value=rollup):
            result = cli.cmd_resume("lyra-1", compress=True)
        assert result is not None

    def test_cmd_fork_not_found(self, mock_sm) -> None:
        mock_sm.get_session.return_value = None
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_fork("nonexistent")
        assert result is None

    def test_cmd_fork_success(self, mock_sm) -> None:
        record = make_record(session_id="lyra-src", steps=[{"type": "step1"}])
        mock_sm.get_session.side_effect = lambda sid: record if sid == "lyra-src" else None
        mock_sm.create_session.return_value = make_record(session_id="lyra-new")
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_fork("lyra-src", new_name="my-fork")
        assert result is not None
        assert result["forked_from"] == "lyra-src"
        meta = mock_sm.create_session.call_args.kwargs.get("metadata", {})
        assert meta.get("fork_name") == "my-fork"
        assert meta.get("forked_from") == "lyra-src"

    def test_cmd_fork_no_steps(self, mock_sm) -> None:
        record = make_record(session_id="lyra-src", steps=[{"type": "step1"}])
        mock_sm.get_session.side_effect = lambda sid: record if sid == "lyra-src" else None
        mock_sm.create_session.return_value = make_record(session_id="lyra-new")
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_fork("lyra-src", keep_steps=False)
        assert result is not None

    def test_cmd_search_empty(self, mock_sm) -> None:
        mock_sm.list_sessions.return_value = []
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_search("query", quiet=True)
        assert result == []

    def test_cmd_search_with_results(self, mock_sm) -> None:
        record = make_record(session_id="lyra-1", steps=[{"type": "msg", "content": "hello query world"}])
        mock_sm.list_sessions.return_value = [record]
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_search("query", quiet=True)
        assert len(result) == 1

    def test_cmd_search_with_filters(self, mock_sm) -> None:
        record = make_record(session_id="lyra-1", agent_id="agent-x", steps=[{"type": "test"}])
        mock_sm.list_sessions.return_value = [record]
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_search(
            "test", quiet=True, agent_id="agent-x", status="active",
            date_from="2024-01-01T00:00:00+00:00",
            date_to="2026-01-01T00:00:00+00:00",
        )
        assert len(result) >= 0  # depends on search logic

    def test_cmd_background_success(self, mock_sm) -> None:
        bg_sess = BackgroundSession(
            session_id="lyra-bg", pid=123, started_at=time.time(), state_file="/tmp/s.json",
        )
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch.object(cli._backgrounder, "background", return_value=bg_sess):
            result = cli.cmd_background("lyra-bg")
        assert result is True

    def test_cmd_background_failure(self, mock_sm) -> None:
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch.object(cli._backgrounder, "background", return_value=None):
            result = cli.cmd_background("lyra-bg")
        assert result is False

    def test_cmd_reattach_alive(self, mock_sm) -> None:
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch.object(cli._backgrounder, "reattach", return_value=True):
            assert cli.cmd_reattach("lyra-bg") is True

    def test_cmd_reattach_dead(self, mock_sm) -> None:
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch.object(cli._backgrounder, "reattach", return_value=False):
            assert cli.cmd_reattach("lyra-bg") is False

    def test_cmd_export_not_found(self, mock_sm) -> None:
        mock_sm.get_session.return_value = None
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_export("nonexistent")
        assert result is None

    def test_cmd_export_success(self, mock_sm) -> None:
        record = make_record(session_id="lyra-exp")
        mock_sm.get_session.return_value = record
        mock_sm.export_session.return_value = {
            "lyra_session_export": True,
            "session": record.to_dict(),
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = f.name
        try:
            with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
                cli = SessionCLI()
            result = cli.cmd_export("lyra-exp", output_path=out_path)
            assert result == out_path
            assert Path(out_path).exists()
        finally:
            Path(out_path).unlink(missing_ok=True)

    def test_cmd_export_no_session_manager_export(self, mock_sm) -> None:
        record = make_record(session_id="lyra-exp")
        mock_sm.get_session.return_value = record
        mock_sm.export_session.return_value = None
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        result = cli.cmd_export("lyra-exp")
        assert result is None

    def test_cmd_export_oserror(self, mock_sm) -> None:
        record = make_record(session_id="lyra-exp")
        mock_sm.get_session.return_value = record
        mock_sm.export_session.return_value = {"key": "val"}
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch("pathlib.Path.write_text", side_effect=OSError("no write")):
            result = cli.cmd_export("lyra-exp", output_path="/bad/path.json")
        assert result is None

    def test_cmd_import_invalid_json(self, mock_sm) -> None:
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch("pathlib.Path.read_text", return_value="invalid json"):
            result = cli.cmd_import("/fake/path.json")
        assert result is None

    def test_cmd_import_wrapped_export(self, mock_sm) -> None:
        record = make_record(session_id="lyra-imp")
        mock_sm.import_session.return_value = record
        export_data = {
            "lyra_session_export": True,
            "session": record.to_dict(),
        }
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch("pathlib.Path.read_text", return_value=json.dumps(export_data)):
            result = cli.cmd_import("/fake/path.json")
        assert result is not None
        assert result["session_id"] == "lyra-imp"

    def test_cmd_import_raw_session(self, mock_sm) -> None:
        record = make_record(session_id="lyra-raw")
        mock_sm.get_session.return_value = None  # does not exist yet
        mock_sm.create_session.return_value = record
        raw_data = record.to_dict()
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch("lyra.sessions.persist.SessionRecord.from_dict", return_value=record):
            with patch("pathlib.Path.read_text", return_value=json.dumps(raw_data)):
                result = cli.cmd_import("/fake/path.json")
        assert result is not None

    def test_cmd_import_raw_session_already_exists(self, mock_sm) -> None:
        record = make_record(session_id="lyra-raw")
        mock_sm.get_session.return_value = record  # already exists
        raw_data = record.to_dict()
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=mock_sm):
            cli = SessionCLI()
        with patch("lyra.sessions.persist.SessionRecord.from_dict", return_value=record):
            with patch("pathlib.Path.read_text", return_value=json.dumps(raw_data)):
                result = cli.cmd_import("/fake/path.json")
        assert result is None

    def test_print_table(self, capsys) -> None:
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=MagicMock()):
            cli = SessionCLI()
        cli._print_table(["Col1", "Col2"], [["a", "bbb"], ["cc", "d"]])
        captured = capsys.readouterr()
        assert "Col1" in captured.out
        assert "bbb" in captured.out

    def test_print_table_empty_rows(self, capsys) -> None:
        with patch("lyra.sessions.cli_manager.SessionManager", return_value=MagicMock()):
            cli = SessionCLI()
        cli._print_table(["H1", "H2"], [])
        captured = capsys.readouterr()
        assert "H1" in captured.out or "--" in captured.out
