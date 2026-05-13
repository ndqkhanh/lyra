"""Tests for commands/trace.py — lyra trace + lyra cost (Phase 5)."""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lyra_cli.commands.trace import (
    _aggregate_cost,
    _classify_kind,
    _find_jsonl,
    _load_events,
    trace_app,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_events(tmp_path: Path, records: list[dict], session: str = "sess-1") -> Path:
    d = tmp_path / ".lyra" / session
    d.mkdir(parents=True, exist_ok=True)
    p = d / "events.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return tmp_path


def _llm_finished(session: str = "s1", model: str = "claude",
                   inp: int = 500, out: int = 100, cache: int = 200,
                   ms: float = 800.0) -> dict:
    return {
        "kind": "LLMCallFinished",
        "ts": "2026-01-01T10:00:00Z",
        "session_id": session,
        "model": model,
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_tokens": cache,
        "duration_ms": ms,
    }


# ---------------------------------------------------------------------------
# _classify_kind
# ---------------------------------------------------------------------------


def test_classify_llm():
    assert _classify_kind({"kind": "LLMCallStarted"}) == "llm"


def test_classify_tool():
    assert _classify_kind({"kind": "ToolCallStarted"}) == "tool"


def test_classify_blocked():
    assert _classify_kind({"kind": "ToolCallBlocked"}) == "blocked"


def test_classify_subagent():
    assert _classify_kind({"kind": "SubagentSpawned"}) == "subagent"


def test_classify_cron():
    assert _classify_kind({"kind": "CronJobFired"}) == "cron"


def test_classify_stop():
    assert _classify_kind({"kind": "StopHookFired"}) == "stop"


def test_classify_permission():
    assert _classify_kind({"kind": "PermissionDecision"}) == "permission"


def test_classify_fallback():
    assert _classify_kind({"kind": "UnknownEvent"}) == "tool"


def test_classify_event_type_key():
    assert _classify_kind({"event_type": "LLMCallFinished"}) == "llm"


# ---------------------------------------------------------------------------
# _find_jsonl
# ---------------------------------------------------------------------------


def test_find_jsonl_all_sessions(tmp_path):
    lyra = tmp_path / ".lyra"
    for name in ("s1", "s2"):
        d = lyra / name
        d.mkdir(parents=True)
        (d / "events.jsonl").write_text("")
    files = _find_jsonl(lyra, None)
    assert len(files) == 2


def test_find_jsonl_session_filter(tmp_path):
    lyra = tmp_path / ".lyra"
    (lyra / "s1").mkdir(parents=True)
    (lyra / "s1" / "events.jsonl").write_text("")
    files = _find_jsonl(lyra, "s1")
    assert len(files) == 1
    assert "s1" in str(files[0])


def test_find_jsonl_missing_session(tmp_path):
    lyra = tmp_path / ".lyra"
    lyra.mkdir()
    files = _find_jsonl(lyra, "no-such")
    assert files == []


# ---------------------------------------------------------------------------
# _load_events
# ---------------------------------------------------------------------------


def test_load_events_returns_tail(tmp_path):
    records = [{"kind": f"E.{i}", "ts": "2026-01-01T00:00:00Z"} for i in range(20)]
    root = _write_events(tmp_path, records)
    files = _find_jsonl(root / ".lyra", None)
    rows = _load_events(files, tail=5)
    assert len(rows) == 5
    assert rows[-1]["kind"] == "E.19"


def test_load_events_skips_invalid_json(tmp_path):
    lyra = tmp_path / ".lyra" / "s"
    lyra.mkdir(parents=True)
    (lyra / "events.jsonl").write_text('{"kind": "ok"}\n{not json}\n{"kind": "ok2"}\n')
    files = _find_jsonl(tmp_path / ".lyra", None)
    rows = _load_events(files, tail=50)
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# _aggregate_cost
# ---------------------------------------------------------------------------


def test_aggregate_cost_single_session(tmp_path):
    records = [_llm_finished(session="s1", model="claude", inp=500, out=100, cache=200)]
    root = _write_events(tmp_path, records)
    files = _find_jsonl(root / ".lyra", None)
    buckets = _aggregate_cost(files)
    assert len(buckets) == 1
    assert buckets[0]["input_tokens"] == 500
    assert buckets[0]["output_tokens"] == 100
    assert buckets[0]["cache_read_tokens"] == 200
    assert buckets[0]["calls"] == 1


def test_aggregate_cost_multiple_calls(tmp_path):
    records = [
        _llm_finished(inp=500, out=100, cache=200),
        _llm_finished(inp=300, out=50, cache=100),
    ]
    root = _write_events(tmp_path, records)
    files = _find_jsonl(root / ".lyra", None)
    buckets = _aggregate_cost(files)
    assert buckets[0]["input_tokens"] == 800
    assert buckets[0]["calls"] == 2


def test_aggregate_cost_two_models(tmp_path):
    records = [
        _llm_finished(session="s1", model="claude"),
        _llm_finished(session="s1", model="gpt-4o"),
    ]
    root = _write_events(tmp_path, records)
    files = _find_jsonl(root / ".lyra", None)
    buckets = _aggregate_cost(files)
    assert len(buckets) == 2


def test_aggregate_cost_empty_files(tmp_path):
    lyra = tmp_path / ".lyra" / "s"
    lyra.mkdir(parents=True)
    (lyra / "events.jsonl").write_text("")
    files = _find_jsonl(tmp_path / ".lyra", None)
    buckets = _aggregate_cost(files)
    assert buckets == []


def test_aggregate_cost_ignores_non_llm_events(tmp_path):
    records = [
        {"kind": "ToolCallStarted", "ts": "2026-01-01T00:00:00Z", "session_id": "s"},
        _llm_finished(),
    ]
    root = _write_events(tmp_path, records)
    files = _find_jsonl(root / ".lyra", None)
    buckets = _aggregate_cost(files)
    assert len(buckets) == 1


# ---------------------------------------------------------------------------
# lyra trace CLI
# ---------------------------------------------------------------------------


def test_trace_no_events(tmp_path):
    result = runner.invoke(trace_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "No event files" in result.output


def test_trace_shows_table(tmp_path):
    records = [
        {"kind": "ToolCallStarted", "ts": "2026-01-01T10:00:00Z", "session_id": "s",
         "tool_name": "bash"},
        {"kind": "LLMCallStarted", "ts": "2026-01-01T10:00:01Z", "session_id": "s",
         "model": "claude"},
    ]
    root = _write_events(tmp_path, records)
    result = runner.invoke(trace_app, ["--repo-root", str(root)])
    assert result.exit_code == 0
    assert "ToolCallStarted" in result.output or "LLMCallStarted" in result.output


def test_trace_tail_limits(tmp_path):
    records = [{"kind": f"E.{i}", "ts": "2026-01-01T00:00:00Z", "session_id": "s"}
               for i in range(20)]
    root = _write_events(tmp_path, records)
    result = runner.invoke(trace_app, ["--repo-root", str(root), "--tail", "3"])
    assert result.exit_code == 0
    assert "E.19" in result.output
    assert "E.0" not in result.output


# ---------------------------------------------------------------------------
# lyra cost CLI
# ---------------------------------------------------------------------------


def test_cost_no_events(tmp_path):
    result = runner.invoke(trace_app, ["cost", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "No event files" in result.output


def test_cost_shows_table(tmp_path):
    records = [_llm_finished(session="s1", model="claude", inp=600, out=200, cache=300)]
    root = _write_events(tmp_path, records)
    result = runner.invoke(trace_app, ["cost", "--repo-root", str(root)])
    assert result.exit_code == 0
    assert "claude" in result.output


def test_cost_json_output(tmp_path):
    records = [_llm_finished(session="s1", model="claude")]
    root = _write_events(tmp_path, records)
    result = runner.invoke(trace_app, ["cost", "--repo-root", str(root), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["model"] == "claude"


def test_cost_no_llm_records(tmp_path):
    records = [{"kind": "ToolCallStarted", "ts": "2026-01-01T00:00:00Z", "session_id": "s"}]
    root = _write_events(tmp_path, records)
    result = runner.invoke(trace_app, ["cost", "--repo-root", str(root)])
    assert result.exit_code == 0
    assert "No LLM call records" in result.output
