"""Contract tests for :mod:`lyra_core.rl.trajectory`."""
from __future__ import annotations

from pathlib import Path

from lyra_core.rl import (
    RLEnvironment,
    TrajectoryRecord,
    TrajectoryRecorder,
    make_rl_list_environments_tool,
)


def test_recorder_appends_jsonl(tmp_path: Path) -> None:
    sink = tmp_path / "rollouts.jsonl"
    rec = TrajectoryRecorder(sink_path=sink)
    rec.record(
        TrajectoryRecord(
            session_id="s1", turn=0, prompt="2+2=?", action="4", reward=1.0
        )
    )
    rec.record(
        TrajectoryRecord(
            session_id="s1", turn=1, prompt="3+3=?", action="5", reward=0.0
        )
    )
    lines = sink.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_recorder_round_trip(tmp_path: Path) -> None:
    sink = tmp_path / "r.jsonl"
    rec = TrajectoryRecorder(sink_path=sink)
    orig = TrajectoryRecord(
        session_id="s2",
        turn=3,
        prompt="p",
        action="a",
        reward=0.5,
        metadata={"kind": "math"},
    )
    rec.record(orig)
    reopened = TrajectoryRecorder(sink_path=sink).read_all()
    assert len(reopened) == 1
    assert reopened[0].metadata == {"kind": "math"}
    assert reopened[0].reward == 0.5


def test_rl_list_environments_tool_has_schema_and_defaults() -> None:
    tool = make_rl_list_environments_tool()
    schema = getattr(tool, "__tool_schema__", None)
    assert schema is not None
    assert schema["name"] == "rl_list_environments"

    out = tool()
    names = {e["name"] for e in out["environments"]}
    assert {"gsm8k", "mbpp", "swebench-lite"} <= names


def test_rl_list_environments_tool_accepts_injected_envs() -> None:
    envs = (
        RLEnvironment(name="custom", description="test only", tags=("t",)),
    )
    tool = make_rl_list_environments_tool(envs)
    out = tool()
    assert [e["name"] for e in out["environments"]] == ["custom"]


def test_reading_missing_sink_returns_empty_list(tmp_path: Path) -> None:
    rec = TrajectoryRecorder(sink_path=tmp_path / "missing.jsonl")
    assert rec.read_all() == []
