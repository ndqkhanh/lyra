"""Red tests for the retrospective artifact."""
from __future__ import annotations

from pathlib import Path

from lyra_core.observability.retro import build_retro_artifact


def test_retro_markdown_has_required_sections(tmp_path: Path) -> None:
    events = [
        {"kind": "session.start", "session_id": "s1", "ts": "t1"},
        {"kind": "tool.call", "session_id": "s1", "payload": {"name": "Read"}},
        {"kind": "tool.result", "session_id": "s1", "payload": {"ok": True}},
        {"kind": "session.end", "session_id": "s1", "ts": "t2"},
    ]
    md = build_retro_artifact(
        session_id="s1",
        events=events,
        plan={
            "title": "Hello",
            "feature_items": [{"skill": "edit", "description": "tiny edit"}],
            "acceptance_tests": ["tests/test_x.py::test_a"],
        },
        verdict="pass",
        artifact_index={"plan": "sha256:abc", "transcript": "sha256:def"},
    )
    assert "# Retro for s1" in md
    assert "## Plan" in md
    assert "## Timeline" in md
    assert "## Verdict" in md
    assert "## Artifacts" in md
    assert "sha256:abc" in md
    assert "sha256:def" in md


def test_retro_lists_tool_calls(tmp_path: Path) -> None:
    events = [
        {"kind": "tool.call", "session_id": "s", "payload": {"name": "Read", "args": {"path": "x"}}},
        {"kind": "tool.call", "session_id": "s", "payload": {"name": "Write", "args": {"path": "y"}}},
    ]
    md = build_retro_artifact(
        session_id="s",
        events=events,
        plan=None,
        verdict="pass",
        artifact_index={},
    )
    assert "Read" in md
    assert "Write" in md
