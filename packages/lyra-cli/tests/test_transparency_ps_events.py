"""Tests for commands/ps.py — lyra ps + lyra events (Phase 2)."""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lyra_cli.commands.ps import (
    _collect_events,
    _find_event_files,
    _matches_filter,
    _parse_line,
    _scan_state_dirs,
    ps_app,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_state(tmp_path: Path, data: dict) -> Path:
    lyra = tmp_path / ".lyra"
    lyra.mkdir()
    p = lyra / "process_state.json"
    p.write_text(json.dumps(data))
    return tmp_path


def _write_events(tmp_path: Path, records: list[dict], session: str = "sess-1") -> Path:
    d = tmp_path / ".lyra" / session
    d.mkdir(parents=True, exist_ok=True)
    p = d / "events.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return tmp_path


# ---------------------------------------------------------------------------
# _parse_line
# ---------------------------------------------------------------------------


def test_parse_line_valid():
    r = _parse_line('{"kind": "Tool.call", "ts": "2026-01-01T00:00:00Z"}')
    assert r is not None
    assert r["kind"] == "Tool.call"


def test_parse_line_empty():
    assert _parse_line("") is None
    assert _parse_line("   ") is None


def test_parse_line_invalid_json():
    assert _parse_line("{not json") is None


# ---------------------------------------------------------------------------
# _matches_filter
# ---------------------------------------------------------------------------


def test_matches_filter_none_always_true():
    assert _matches_filter({"kind": "anything"}, None)


def test_matches_filter_substring_match():
    assert _matches_filter({"kind": "Tool.call"}, "tool")
    assert _matches_filter({"kind": "Tool.call"}, "Tool")


def test_matches_filter_no_match():
    assert not _matches_filter({"kind": "AgentLoop.start"}, "tool")


def test_matches_filter_event_type_key():
    assert _matches_filter({"event_type": "ToolCallStarted"}, "ToolCall")


# ---------------------------------------------------------------------------
# _scan_state_dirs
# ---------------------------------------------------------------------------


def test_scan_state_dirs_empty(tmp_path):
    assert _scan_state_dirs(tmp_path / "nonexistent") == []


def test_scan_state_dirs_finds_files(tmp_path):
    state_dir = tmp_path / "state"
    sub = state_dir / "session-1"
    sub.mkdir(parents=True)
    (sub / "process_state.json").write_text(json.dumps({"session_id": "s1"}))
    results = _scan_state_dirs(state_dir)
    assert len(results) == 1
    assert results[0]["session_id"] == "s1"


def test_scan_state_dirs_skips_corrupt(tmp_path):
    state_dir = tmp_path / "state"
    sub = state_dir / "bad"
    sub.mkdir(parents=True)
    (sub / "process_state.json").write_text("{not json")
    assert _scan_state_dirs(state_dir) == []


# ---------------------------------------------------------------------------
# _find_event_files
# ---------------------------------------------------------------------------


def test_find_event_files_no_filter(tmp_path):
    lyra = tmp_path / ".lyra"
    sess = lyra / "sess-1"
    sess.mkdir(parents=True)
    (sess / "events.jsonl").write_text("")
    files = _find_event_files(lyra, None)
    assert len(files) == 1


def test_find_event_files_session_filter(tmp_path):
    lyra = tmp_path / ".lyra"
    for name in ("sess-1", "sess-2"):
        d = lyra / name
        d.mkdir(parents=True)
        (d / "events.jsonl").write_text("")
    files = _find_event_files(lyra, "sess-1")
    assert all("sess-1" in str(f) for f in files)


def test_find_event_files_nonexistent_session(tmp_path):
    lyra = tmp_path / ".lyra"
    lyra.mkdir()
    files = _find_event_files(lyra, "no-such-session")
    assert files == []


# ---------------------------------------------------------------------------
# _collect_events
# ---------------------------------------------------------------------------


def test_collect_events_returns_last_n(tmp_path):
    records = [{"kind": f"Event.{i}", "ts": f"2026-01-01T00:00:0{i}Z"} for i in range(10)]
    root = _write_events(tmp_path, records)
    lyra = root / ".lyra"
    files = _find_event_files(lyra, None)
    rows = _collect_events(files, None, tail=3)
    assert len(rows) == 3
    assert rows[-1]["kind"] == "Event.9"


def test_collect_events_type_filter(tmp_path):
    records = [
        {"kind": "Tool.call", "ts": "2026-01-01T00:00:00Z"},
        {"kind": "AgentLoop.start", "ts": "2026-01-01T00:00:01Z"},
        {"kind": "Tool.result", "ts": "2026-01-01T00:00:02Z"},
    ]
    root = _write_events(tmp_path, records)
    lyra = root / ".lyra"
    files = _find_event_files(lyra, None)
    rows = _collect_events(files, "Tool", tail=50)
    assert all("Tool" in r["kind"] for r in rows)
    assert len(rows) == 2


def test_collect_events_empty_file(tmp_path):
    lyra = tmp_path / ".lyra"
    sess = lyra / "s"
    sess.mkdir(parents=True)
    (sess / "events.jsonl").write_text("")
    files = _find_event_files(lyra, None)
    rows = _collect_events(files, None, tail=10)
    assert rows == []


# ---------------------------------------------------------------------------
# lyra ps CLI
# ---------------------------------------------------------------------------


def test_ps_no_state_file(tmp_path):
    result = runner.invoke(ps_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "No process state" in result.output


def test_ps_shows_table(tmp_path):
    _write_state(tmp_path, {
        "session_id": "my-session",
        "status": "running",
        "agent_role": "planner",
        "permission_mode": "plan",
        "current_step": 3,
        "max_steps": 10,
        "token_in": 1200,
        "cost_usd_so_far": 0.0042,
        "last_tool": {"name": "bash", "status": "done", "duration_ms": 120.0},
    })
    result = runner.invoke(ps_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    # Rich may truncate wide columns in narrow terminals; check stable content
    assert "running" in result.output
    assert "planner" in result.output


def test_ps_json_output(tmp_path):
    _write_state(tmp_path, {"session_id": "json-test", "status": "done"})
    result = runner.invoke(ps_app, ["--repo-root", str(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["session_id"] == "json-test"


# ---------------------------------------------------------------------------
# lyra events subcommand
# ---------------------------------------------------------------------------


def test_events_no_files(tmp_path):
    result = runner.invoke(ps_app, ["events", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "No event files" in result.output


def test_events_shows_table(tmp_path):
    records = [
        {"kind": "Tool.call", "ts": "2026-01-01T10:00:00Z", "session_id": "s1", "tool": "bash"},
        {"kind": "Tool.result", "ts": "2026-01-01T10:00:01Z", "session_id": "s1"},
    ]
    root = _write_events(tmp_path, records)
    result = runner.invoke(ps_app, ["events", "--repo-root", str(root)])
    assert result.exit_code == 0
    assert "Tool.call" in result.output


def test_events_type_filter(tmp_path):
    records = [
        {"kind": "Tool.call", "ts": "2026-01-01T00:00:00Z", "session_id": "s"},
        {"kind": "AgentLoop.start", "ts": "2026-01-01T00:00:01Z", "session_id": "s"},
    ]
    root = _write_events(tmp_path, records)
    result = runner.invoke(ps_app, ["events", "--repo-root", str(root), "--type", "AgentLoop"])
    assert result.exit_code == 0
    assert "AgentLoop" in result.output
    assert "Tool.call" not in result.output


def test_events_tail_limits_rows(tmp_path):
    records = [{"kind": f"E.{i}", "ts": "2026-01-01T00:00:00Z", "session_id": "s"}
               for i in range(30)]
    root = _write_events(tmp_path, records)
    result = runner.invoke(ps_app, ["events", "--repo-root", str(root), "--tail", "5"])
    assert result.exit_code == 0
    # Last 5 events should be present
    assert "E.29" in result.output
    assert "E.0" not in result.output
