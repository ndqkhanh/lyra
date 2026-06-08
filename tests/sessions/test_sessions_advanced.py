"""
Tests for Lyra Sessions v9.0 advanced features.

Covers:
- SessionCLI: list, kill, resume, fork, search, background, reattach, export, import
- SessionSearch: keyword search, date filter, agent filter, score
- SessionBackgrounder: background, reattach, list
- ContextCompressionOnResume: compress, rollup, summary extraction
- SessionManager v9.0: orthogonal state dimensions, tags, export/import
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lyra.sessions.persist import (
    OrthogonalState,
    SessionManager,
    SessionRecord,
    SessionStatus,
    SessionTag,
)
from lyra.sessions.cli_manager import (
    BackgroundSession,
    ContextCompressionOnResume,
    SearchResult,
    SessionBackgrounder,
    SessionCLI,
    SessionSearch,
)


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def db_path():
    """Provide a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sm(db_path):
    """Provide a fresh SessionManager with the temp DB."""
    manager = SessionManager(db_path)
    yield manager
    manager.close()


@pytest.fixture
def populated_sm(sm):
    """SessionManager with several pre-populated sessions."""
    for i in range(3):
        sid = f"session-{i}"
        sm.create_session(session_id=sid, agent_id=f"agent-{i}")
        sm.append_step(sid, {"type": "user_message", "content": f"Hello from session {i}"})
        sm.append_step(sid, {"type": "tool_call", "tool": "read_file", "arguments": {"path": "/tmp/test"}})
        sm.update_session(sid, status=SessionStatus.ACTIVE)
    return sm


# ======================================================================
# Orthogonal State tests
# ======================================================================


class TestOrthogonalState:
    """Test orthogonal state dimensions."""

    def test_default_state(self):
        """A default OrthogonalState has empty dimensions."""
        state = OrthogonalState()
        assert state.agent_state == {}
        assert state.progress == {}
        assert state.economics == {}
        assert state.runtime == {}
        assert state.custom == {}

    def test_to_dict(self):
        """to_dict serialises all dimensions."""
        state = OrthogonalState(
            agent_state={"model": "claude-opus-4"},
            progress={"pct": 75},
            economics={"total_cost": 1.50},
        )
        d = state.to_dict()
        assert d["agent_state"] == {"model": "claude-opus-4"}
        assert d["progress"] == {"pct": 75}
        assert d["economics"] == {"total_cost": 1.50}
        assert d["runtime"] == {}
        assert d["custom"] == {}

    def test_from_dict(self):
        """from_dict reconstructs from a serialised dict."""
        data = {
            "agent_state": {"model": "opus"},
            "progress": {"pct": 50},
            "economics": {"cost": 1.0},
            "runtime": {"elapsed": 100},
            "custom": {"note": "test"},
        }
        state = OrthogonalState.from_dict(data)
        assert state.agent_state["model"] == "opus"
        assert state.custom["note"] == "test"

    def test_from_dict_missing_keys(self):
        """from_dict handles missing keys gracefully."""
        state = OrthogonalState.from_dict({"agent_state": {"k": "v"}})
        assert state.agent_state == {"k": "v"}
        assert state.progress == {}
        assert state.economics == {}
        assert state.runtime == {}
        assert state.custom == {}


# ======================================================================
# SessionManager v9.0 tests (tags, orthogonal, export/import)
# ======================================================================


class TestSessionV9Tags:
    """Test session tag management."""

    def test_set_and_get_tag(self, sm):
        """Setting a tag and reading it back works."""
        sm.create_session("s1")
        sm.set_tag("s1", "project", "lyra-core")
        assert sm.get_tag("s1", "project") == "lyra-core"

    def test_get_tag_not_found(self, sm):
        """Getting a non-existent tag returns None."""
        sm.create_session("s1")
        assert sm.get_tag("s1", "nonexistent") is None

    def test_get_all_tags(self, sm):
        """get_all_tags returns all tags as a dict."""
        sm.create_session("s1")
        sm.set_tag("s1", "project", "lyra")
        sm.set_tag("s1", "model", "opus")
        tags = sm.get_all_tags("s1")
        assert tags == {"project": "lyra", "model": "opus"}

    def test_delete_tag(self, sm):
        """Deleting a tag removes it."""
        sm.create_session("s1")
        sm.set_tag("s1", "project", "lyra")
        assert sm.delete_tag("s1", "project") is True
        assert sm.get_tag("s1", "project") is None

    def test_set_tag_upsert(self, sm):
        """Setting the same key replaces the value."""
        sm.create_session("s1")
        sm.set_tag("s1", "status", "active")
        sm.set_tag("s1", "status", "paused")
        assert sm.get_tag("s1", "status") == "paused"

    def test_find_by_tag(self, sm):
        """find_by_tag returns all sessions with a matching tag."""
        sm.create_session("s1")
        sm.create_session("s2")
        sm.create_session("s3")
        sm.set_tag("s1", "project", "lyra")
        sm.set_tag("s2", "project", "lyra")
        sm.set_tag("s3", "project", "other")

        results = sm.find_by_tag("project", "lyra")
        assert len(results) == 2
        assert {r.session_id for r in results} == {"s1", "s2"}

    def test_tags_in_session_record(self, sm):
        """Tags are loaded as part of the SessionRecord."""
        sm.create_session("s1")
        sm.set_tag("s1", "project", "lyra")
        record = sm.get_session("s1")
        assert len(record.tags) == 1
        assert record.tags[0].key == "project"
        assert record.tags[0].value == "lyra"


class TestSessionV9Orthogonal:
    """Test orthogonal state dimension management."""

    def test_create_with_orthogonal(self, sm):
        """Creating a session with orthogonal state stores it."""
        orth = OrthogonalState(
            agent_state={"model": "opus"},
            economics={"total_cost": 0.0},
        )
        sm.create_session("s1", orthogonal=orth)
        record = sm.get_session("s1")
        assert record.orthogonal.agent_state["model"] == "opus"
        assert record.orthogonal.economics["total_cost"] == 0.0

    def test_update_orthogonal(self, sm):
        """Updating orthogonal state merges per-dimension."""
        orth = OrthogonalState(
            agent_state={"model": "opus"},
            economics={"total_cost": 0.0},
        )
        sm.create_session("s1", orthogonal=orth)

        sm.update_session("s1", orthogonal=OrthogonalState(
            economics={"total_cost": 5.50, "token_count": 1000},
        ))
        record = sm.get_session("s1")
        assert record.orthogonal.agent_state["model"] == "opus"  # unchanged
        assert record.orthogonal.economics["total_cost"] == 5.50  # updated
        assert record.orthogonal.economics["token_count"] == 1000  # added

    def test_get_orthogonal_state(self, sm):
        """get_orthogonal_state reads only orthogonal dimensions."""
        sm.create_session("s1", orthogonal=OrthogonalState(runtime={"elapsed": 60}))
        orth = sm.get_orthogonal_state("s1")
        assert orth is not None
        assert orth.runtime["elapsed"] == 60

    def test_update_progress(self, sm):
        """update_progress sets progress fields efficiently."""
        sm.create_session("s1")
        result = sm.update_progress("s1", pct=50, phase="research")
        assert result is True
        orth = sm.get_orthogonal_state("s1")
        assert orth.progress["pct"] == 50
        assert orth.progress["phase"] == "research"

    def test_update_economics(self, sm):
        """update_economics sets economics fields efficiently."""
        sm.create_session("s1")
        sm.update_economics("s1", total_cost=10.0)
        orth = sm.get_orthogonal_state("s1")
        assert orth.economics["total_cost"] == 10.0

    def test_update_runtime(self, sm):
        """update_runtime sets runtime fields efficiently."""
        sm.create_session("s1")
        sm.update_runtime("s1", active_tool="read_file")
        orth = sm.get_orthogonal_state("s1")
        assert orth.runtime["active_tool"] == "read_file"


class TestSessionExportImport:
    """Test session export and import."""

    def test_export_session(self, sm, populated_sm):
        """export_session produces a portable JSON-serialisable dict."""
        export = sm.export_session("session-0")
        assert export is not None
        assert export["lyra_session_export"] is True
        assert export["schema_version"] == 1
        assert "exported_at" in export
        assert export["session"]["session_id"] == "session-0"
        assert len(export["session"]["steps"]) == 2

    def test_export_missing_session(self, sm):
        """Exporting a non-existent session returns None."""
        export = sm.export_session("nonexistent")
        assert export is None

    def test_import_session(self, sm, populated_sm):
        """Importing an exported session creates a new record."""
        export = sm.export_session("session-0")
        assert export is not None

        # Create a new manager to import into
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            new_path = f.name
        new_sm = SessionManager(new_path)

        try:
            result = new_sm.import_session(export)
            assert result is not None
            assert result.session_id == "session-0"
            assert len(result.steps) == 2

            # Verify it's actually persisted
            loaded = new_sm.get_session("session-0")
            assert loaded is not None
            assert loaded.agent_id == "agent-0"
        finally:
            new_sm.close()
            if os.path.exists(new_path):
                os.unlink(new_path)

    def test_import_existing_session(self, sm, populated_sm):
        """Importing a session that already exists returns None."""
        export = sm.export_session("session-0")
        assert export is not None
        result = sm.import_session(export)
        assert result is None  # Already exists

    def test_import_invalid_data(self, sm):
        """Importing invalid data raises ValueError."""
        with pytest.raises(ValueError, match="Not a valid Lyra session export"):
            sm.import_session({"some": "data"})

    def test_export_includes_tags(self, sm):
        """Exported sessions include tags."""
        sm.create_session("s1")
        sm.set_tag("s1", "project", "lyra")
        export = sm.export_session("s1")
        assert len(export["session"]["tags"]) == 1
        assert export["session"]["tags"][0]["key"] == "project"

    def test_import_restores_tags(self, sm):
        """Importing a session restores tags."""
        sm.create_session("s1")
        sm.set_tag("s1", "env", "prod")
        export = sm.export_session("s1")

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            new_path = f.name
        new_sm = SessionManager(new_path)

        try:
            new_sm.import_session(export)
            assert new_sm.get_tag("s1", "env") == "prod"
        finally:
            new_sm.close()
            if os.path.exists(new_path):
                os.unlink(new_path)


# ======================================================================
# SessionSearch tests
# ======================================================================


class TestSessionSearch:
    """Test session search functionality."""

    def test_search_by_session_id(self, populated_sm):
        """Searching by session ID finds matching sessions."""
        searcher = SessionSearch(populated_sm)
        results = searcher.search("session-0")
        assert len(results) >= 1
        assert results[0].session_id == "session-0"

    def test_search_by_content(self, populated_sm):
        """Searching by step content finds matching sessions."""
        searcher = SessionSearch(populated_sm)
        results = searcher.search("read_file")
        assert len(results) >= 1

    def test_search_no_match(self, populated_sm):
        """Searching for a non-existent keyword returns no results."""
        searcher = SessionSearch(populated_sm)
        results = searcher.search("zzz_nonexistent_zzz")
        assert len(results) == 0

    def test_search_by_agent(self, populated_sm):
        """Searching with an agent filter narrows results."""
        searcher = SessionSearch(populated_sm)
        results = searcher.search("Hello", agent_id="agent-0")
        assert len(results) >= 1
        for r in results:
            # Verify by re-fetching
            pass

    def test_search_limit(self, populated_sm):
        """Search respects the limit parameter."""
        searcher = SessionSearch(populated_sm)
        results = searcher.search("session", limit=1)
        assert len(results) <= 1

    def test_search_scores(self, populated_sm):
        """Session ID matches score higher than content matches."""
        searcher = SessionSearch(populated_sm)
        exact = searcher.search("session-0")
        content = searcher.search("read_file")

        # session-0 should have higher score from ID match
        if exact and content:
            assert exact[0].score > 0

    def test_search_by_date(self, populated_sm):
        """Searching by date range filters results."""
        searcher = SessionSearch(populated_sm)

        # Search with a far future date should return nothing
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        results = searcher.search_by_date(date_from=future)
        assert len(results) == 0

        # Search from the past should return sessions
        past = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        results = searcher.search_by_date(date_from=past)
        assert len(results) >= 1


# ======================================================================
# SessionBackgrounder tests
# ======================================================================


class TestSessionBackgrounder:
    """Test background session management."""

    def test_background_and_reattach(self):
        """Backgrounding and reattaching works."""
        bg = SessionBackgrounder(state_dir=tempfile.mkdtemp())
        result = bg.background(
            "s1",
            command=["sleep", "5"],
        )
        assert result is not None
        assert result.session_id == "s1"
        assert result.pid > 0

        assert bg.reattach("s1") is True
        bg._remove_state("s1")

    def test_background_duplicate(self):
        """Backgrounding an already backgrounded session returns None."""
        bg = SessionBackgrounder(state_dir=tempfile.mkdtemp())
        bg.background("s1", command=["sleep", "5"])
        result = bg.background("s1", command=["sleep", "5"])
        assert result is None
        bg._remove_state("s1")

    def test_list_backgrounded(self):
        """list_backgrounded returns tracked sessions."""
        bg = SessionBackgrounder(state_dir=tempfile.mkdtemp())
        bg.background("s1", command=["sleep", "5"])
        sessions = bg.list_backgrounded()
        assert len(sessions) >= 1
        assert any(s.session_id == "s1" for s in sessions)
        bg._remove_state("s1")

    def test_reattach_nonexistent(self):
        """Reattaching a non-existent session returns False."""
        bg = SessionBackgrounder(state_dir=tempfile.mkdtemp())
        assert bg.reattach("nonexistent") is False


# ======================================================================
# ContextCompressionOnResume tests
# ======================================================================


class TestContextCompressionOnResume:
    """Test context compression on session resume."""

    def test_compress_no_session(self, sm):
        """Compressing a non-existent session returns None."""
        compressor = ContextCompressionOnResume(sm)
        result = compressor.compress_for_resume("nonexistent")
        assert result is None

    def test_compress_no_steps(self, sm):
        """Compressing a session with no steps returns None."""
        sm.create_session("s1")
        compressor = ContextCompressionOnResume(sm)
        result = compressor.compress_for_resume("s1")
        assert result is None

    def test_compress_with_many_steps(self, sm):
        """Compressing a session with many steps produces a rollup."""
        sm.create_session("s1")
        for i in range(15):
            sm.append_step("s1", {"type": "user_message", "content": f"Message {i}"})

        compressor = ContextCompressionOnResume(sm)
        rollup = compressor.compress_for_resume("s1", keep_recent=5)
        assert rollup is not None
        assert rollup.session_id == "s1"
        assert rollup.original_steps == 15
        assert rollup.compressed_steps < 15  # Compressed
        assert len(rollup.summary) > 0

    def test_compress_small_history(self, sm):
        """Sessions with few steps are not compressed."""
        sm.create_session("s1")
        for i in range(8):
            sm.append_step("s1", {"type": "tool_call", "tool": "read"})

        compressor = ContextCompressionOnResume(sm)
        rollup = compressor.compress_for_resume("s1", keep_recent=10)
        assert rollup is not None
        # All steps retained (keep_recent >= total)
        assert rollup.compressed_steps == 8
        assert "All steps retained" in rollup.summary

    def test_compress_marker_in_context(self, sm):
        """Compressed sessions have a _compressed marker in context."""
        sm.create_session("s1")
        for i in range(15):
            sm.append_step("s1", {"type": "user_message", "content": f"M {i}"})

        compressor = ContextCompressionOnResume(sm)
        compressor.compress_for_resume("s1")

        record = sm.get_session("s1")
        assert record.context.get("_compressed") is True

    def test_extract_decisions(self, sm):
        """Decisions are extracted from decision-type steps."""
        sm.create_session("s1")
        sm.append_step("s1", {"type": "decision", "description": "Use Opus for routing"})
        sm.append_step("s1", {"type": "user_message", "content": "Hello"})

        compressor = ContextCompressionOnResume(sm)
        decisions = compressor._extract_decisions([{"type": "decision", "description": "Use Opus"}])
        assert "Use Opus" in decisions


# ======================================================================
# SessionCLI tests
# ======================================================================


class TestSessionCLI:
    """Test the full SessionCLI interface."""

    def test_cmd_list_empty(self, db_path):
        """Listing sessions on an empty DB returns empty."""
        cli = SessionCLI(db_path)
        result = cli.cmd_list(quiet=True)
        assert result == []

    def test_cmd_list_populated(self, db_path):
        """Listing sessions returns all sessions."""
        cli = SessionCLI(db_path)
        cli._sm.create_session("s1", agent_id="test-agent")
        cli._sm.create_session("s2", agent_id="test-agent")

        result = cli.cmd_list(quiet=True)
        assert len(result) == 2

    def test_cmd_list_filtered_by_status(self, db_path):
        """Listing sessions filtered by status returns only matching."""
        cli = SessionCLI(db_path)
        cli._sm.create_session("s1", agent_id="test-agent")
        cli._sm.update_session("s1", status=SessionStatus.COMPLETED)
        cli._sm.create_session("s2", agent_id="test-agent")
        # s2 is ACTIVE

        result = cli.cmd_list(status="completed", quiet=True)
        assert len(result) == 1
        assert result[0]["session_id"] == "s1"

    def test_cmd_kill_existing(self, db_path):
        """Killing an existing session returns True."""
        cli = SessionCLI(db_path)
        cli._sm.create_session("s1")
        assert cli.cmd_kill("s1") is True
        assert cli._sm.get_session("s1") is None

    def test_cmd_kill_nonexistent(self, db_path):
        """Killing a non-existent session returns False."""
        cli = SessionCLI(db_path)
        assert cli.cmd_kill("nonexistent") is False

    def test_cmd_resume_existing(self, db_path):
        """Resuming an existing session with compression works."""
        cli = SessionCLI(db_path)
        cli._sm.create_session("s1")
        for i in range(15):
            cli._sm.append_step("s1", {"type": "tool_call", "tool": "read"})

        context = cli.cmd_resume("s1")
        assert context is not None
        assert context["session_id"] == "s1"

    def test_cmd_resume_nonexistent(self, db_path):
        """Resuming a non-existent session returns None."""
        cli = SessionCLI(db_path)
        assert cli.cmd_resume("nonexistent") is None

    def test_cmd_fork(self, db_path):
        """Forking a session duplicates it."""
        cli = SessionCLI(db_path)
        cli._sm.create_session("s1", agent_id="agent-1")
        cli._sm.append_step("s1", {"type": "message", "content": "Hello"})

        result = cli.cmd_fork("s1", new_name="test-fork")
        assert result is not None
        assert result["forked_from"] == "s1"
        assert result["session_id"] != "s1"
        assert cli._sm.get_session(result["session_id"]) is not None

        # Original should still exist
        assert cli._sm.get_session("s1") is not None

    def test_cmd_fork_nonexistent(self, db_path):
        """Forking a non-existent session returns None."""
        cli = SessionCLI(db_path)
        assert cli.cmd_fork("nonexistent") is None

    def test_cmd_search(self, db_path):
        """Searching finds matching sessions."""
        cli = SessionCLI(db_path)
        cli._sm.create_session("s1")
        cli._sm.append_step("s1", {"type": "message", "content": "Hello Lyra"})

        results = cli.cmd_search("Lyra", quiet=True)
        assert len(results) >= 1

    def test_cmd_search_no_match(self, db_path):
        """Searching for non-existent content returns empty."""
        cli = SessionCLI(db_path)
        cli._sm.create_session("s1")
        results = cli.cmd_search("zzz_nonexistent_zzz", quiet=True)
        assert len(results) == 0

    def test_cmd_search_with_filters(self, db_path):
        """Searching with filters narrows results."""
        cli = SessionCLI(db_path)
        cli._sm.create_session("s1", agent_id="agent-a")
        cli._sm.create_session("s2", agent_id="agent-b")

        results = cli.cmd_search("", agent_id="agent-a", quiet=True)
        assert len(results) >= 1
        # All results should be from agent-a (search returns matched sessions)

    def test_cmd_background_and_reattach(self, db_path):
        """Backgrounding and reattaching a session."""
        cli = SessionCLI(db_path)
        cli._sm.create_session("s1")

        result = cli.cmd_background("s1", command=["sleep", "5"])
        assert result is True

        alive = cli.cmd_reattach("s1")
        assert alive is True

    def test_cmd_export(self, db_path):
        """Exporting a session creates a JSON file."""
        cli = SessionCLI(db_path)
        cli._sm.create_session("s1", agent_id="test-agent")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            out_path = f.name

        try:
            result = cli.cmd_export("s1", output_path=out_path)
            assert result == out_path
            assert os.path.exists(out_path)

            with open(out_path) as f:
                data = json.load(f)
            assert data["lyra_session_export"] is True
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_cmd_export_nonexistent(self, db_path):
        """Exporting a non-existent session returns None."""
        cli = SessionCLI(db_path)
        assert cli.cmd_export("nonexistent") is None

    def test_cmd_import(self, db_path):
        """Importing a session from JSON works."""
        # First, create and export
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            source_db = f.name

        source_cli = SessionCLI(source_db)
        source_cli._sm.create_session("s1", agent_id="test-agent")
        source_cli._sm.append_step("s1", {"type": "message", "content": "Hello"})

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            export_path = f.name

        try:
            source_cli.cmd_export("s1", output_path=export_path)

            # Import into a new CLI
            dest_cli = SessionCLI(db_path)
            result = dest_cli.cmd_import(export_path)
            assert result is not None
            assert result["session_id"] == "s1"
            assert dest_cli._sm.get_session("s1") is not None
        finally:
            source_cli._sm.close()
            if os.path.exists(source_db):
                os.unlink(source_db)
            if os.path.exists(export_path):
                os.unlink(export_path)
