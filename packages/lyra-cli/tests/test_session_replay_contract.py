"""Wave-E Task 12: ``/replay`` + replay engine contract tests.

What's pinned here:

* ``ReplayController`` walks ``turns.jsonl`` event-by-event.
* The diff between adjacent turns is stable (unified diff over the
  ``input``/``output`` body).
* The ``/replay`` slash command wires through to the controller and
  caches the cursor on the session so successive ``/replay next``
  calls advance.
* Edge cases: missing log → friendly error, empty log → "no recorded
  turns", cursor at start/end returns ``None``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_cli.interactive.replay import (
    ReplayController,
    ReplayError,
    load_replay,
    step_through,
)
from lyra_cli.interactive.session import InteractiveSession


def _write_turns(session_dir: Path, turns: list[dict]) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    log = session_dir / "turns.jsonl"
    log.write_text("\n".join(json.dumps(t) for t in turns) + "\n", encoding="utf-8")


def _session(tmp_path: Path) -> InteractiveSession:
    sessions_root = tmp_path / "sessions"
    sessions_root.mkdir()
    return InteractiveSession(
        repo_root=tmp_path,
        sessions_root=sessions_root,
        session_id="s1",
    )


# ----- engine ----------------------------------------------------------


def test_load_replay_reads_jsonl(tmp_path: Path) -> None:
    _write_turns(
        tmp_path / "s1",
        [{"input": "hi", "output": "hello"}, {"input": "ping", "output": "pong"}],
    )
    turns = load_replay(tmp_path / "s1")
    assert len(turns) == 2
    assert turns[0]["input"] == "hi"
    assert turns[1]["output"] == "pong"


def test_load_replay_skips_malformed_lines(tmp_path: Path) -> None:
    sd = tmp_path / "s1"
    sd.mkdir()
    (sd / "turns.jsonl").write_text(
        "{not-json}\n"
        + json.dumps({"input": "ok", "output": "fine"})
        + "\n",
        encoding="utf-8",
    )
    turns = load_replay(sd)
    assert len(turns) == 1
    assert turns[0]["input"] == "ok"


def test_load_replay_missing_log_raises(tmp_path: Path) -> None:
    with pytest.raises(ReplayError):
        load_replay(tmp_path / "missing")


def test_step_through_emits_diff_between_turns(tmp_path: Path) -> None:
    turns = [
        {"input": "hi", "output": "hello world"},
        {"input": "hi", "output": "hello there"},
    ]
    events = list(step_through(turns))
    assert len(events) == 2
    assert events[0].diff == ""  # first event has no diff
    assert "hello world" in events[1].diff
    assert "hello there" in events[1].diff
    assert events[1].diff.startswith("---")


def test_replay_controller_next_prev_reset(tmp_path: Path) -> None:
    sd = tmp_path / "s1"
    _write_turns(
        sd,
        [
            {"input": "a", "output": "1"},
            {"input": "b", "output": "2"},
            {"input": "c", "output": "3"},
        ],
    )
    rc = ReplayController(session_dir=sd)
    assert len(rc) == 3
    assert rc.current() is None

    e0 = rc.next()
    assert e0 is not None and e0.index == 0
    assert rc.current() == e0

    e1 = rc.next()
    assert e1 is not None and e1.index == 1

    back = rc.prev()
    assert back is not None and back.index == 0

    rc.reset()
    assert rc.current() is None

    # Walk to end then off the edge → None.
    rc.next(); rc.next(); rc.next()
    assert rc.next() is None


# ----- /replay slash command ------------------------------------------


def test_slash_replay_no_session_dir_returns_friendly(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)  # no sessions_root
    res = s.dispatch("/replay")
    assert "no on-disk session" in res.output


def test_slash_replay_no_log_yet(tmp_path: Path) -> None:
    s = _session(tmp_path)
    # Session dir exists but no turns.jsonl yet (fresh session).
    (s._session_dir()).mkdir(parents=True, exist_ok=True)
    res = s.dispatch("/replay")
    assert "no turns recorded" in res.output


def test_slash_replay_advances_cursor(tmp_path: Path) -> None:
    s = _session(tmp_path)
    _write_turns(
        s._session_dir(),
        [
            {"input": "hi", "output": "hello"},
            {"input": "ping", "output": "pong"},
        ],
    )
    a = s.dispatch("/replay next")
    assert "turn 1" in a.output

    b = s.dispatch("/replay next")
    assert "turn 2" in b.output
    assert "pong" in b.output

    end = s.dispatch("/replay next")
    assert "at end" in end.output


def test_slash_replay_reset_and_status(tmp_path: Path) -> None:
    s = _session(tmp_path)
    _write_turns(
        s._session_dir(),
        [{"input": "x", "output": "y"}],
    )
    s.dispatch("/replay next")
    rst = s.dispatch("/replay reset")
    assert "reset" in rst.output
    st = s.dispatch("/replay status")
    assert "cursor=0" in st.output and "total=1" in st.output


def test_slash_replay_all_dumps_every_turn(tmp_path: Path) -> None:
    s = _session(tmp_path)
    _write_turns(
        s._session_dir(),
        [
            {"input": "a", "output": "1"},
            {"input": "b", "output": "2"},
        ],
    )
    res = s.dispatch("/replay all")
    assert "turn 1" in res.output and "turn 2" in res.output


def test_slash_replay_unknown_arg(tmp_path: Path) -> None:
    s = _session(tmp_path)
    _write_turns(s._session_dir(), [{"input": "a", "output": "1"}])
    res = s.dispatch("/replay rewind")
    assert "usage" in res.output and "rewind" in res.output
