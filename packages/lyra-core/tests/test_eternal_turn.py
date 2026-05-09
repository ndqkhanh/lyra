"""L4.1 — durable turn wrapper around AgentLoop."""
from __future__ import annotations

from pathlib import Path

import pytest

from harness_eternal import CircuitBreaker
from harness_eternal.restate import LocalRuntime

from lyra_core.agent.eternal_turn import EternalAgentLoop, JournaledTools


# Lightweight stand-in for AgentLoop. The eternal wrapper duck-types,
# so we don't pull in the full agent module here.
class _StubLoop:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    def run_conversation(self, user_text: str, *, session_id: str):
        # Drive one tool call so we exercise the JournaledTools path.
        if "echo" in self.tools:
            self.tools["echo"](msg=user_text)

        class TR:
            final_text = f"reply:{user_text}"
            iterations = 1
            tool_calls = [{"name": "echo"}]
            stopped_by = "end_turn"

        return TR()


def test_journaled_tools_memoizes_idempotent_dispatch(tmp_path: Path) -> None:
    runtime = LocalRuntime(tmp_path / "rt")
    calls = {"n": 0}

    def echo(msg: str) -> str:
        calls["n"] += 1
        return f"echoed:{msg}"

    echo.__eternal_idempotent__ = True

    journaled = JournaledTools(
        {"echo": echo}, journal=runtime.journal, turn_id="turn-1"
    )
    out1 = journaled["echo"](msg="hi")
    out2 = journaled["echo"](msg="hi")  # same args → memoized
    assert out1 == "echoed:hi"
    assert out2 == "echoed:hi"
    assert calls["n"] == 1  # the underlying tool ran once


def test_journaled_tools_does_not_memoize_non_idempotent(tmp_path: Path) -> None:
    runtime = LocalRuntime(tmp_path / "rt")
    calls = {"n": 0}

    def write(msg: str) -> str:
        calls["n"] += 1
        return msg

    # No __eternal_idempotent__ flag → not memoized.
    journaled = JournaledTools(
        {"write": write}, journal=runtime.journal, turn_id="turn-2"
    )
    journaled["write"](msg="a")
    journaled["write"](msg="a")
    assert calls["n"] == 2


def test_journaled_tools_args_distinguish_invocations(tmp_path: Path) -> None:
    runtime = LocalRuntime(tmp_path / "rt")
    calls = {"n": 0}

    def echo(msg: str) -> str:
        calls["n"] += 1
        return f"echoed:{msg}"

    echo.__eternal_idempotent__ = True

    journaled = JournaledTools(
        {"echo": echo}, journal=runtime.journal, turn_id="turn-3"
    )
    journaled["echo"](msg="a")
    journaled["echo"](msg="b")  # different args → fresh call
    journaled["echo"](msg="a")  # same as first → memoized
    assert calls["n"] == 2


def test_eternal_agent_loop_run_conversation_durable(tmp_path: Path) -> None:
    runtime = LocalRuntime(tmp_path / "rt")
    breaker = CircuitBreaker(after=5)

    loop = _StubLoop(llm=None, tools={"echo": _make_idempotent_echo()})
    eternal = EternalAgentLoop(
        loop=loop,
        runtime=runtime,
        breaker=breaker,
        deadline_per_turn_s=10,
    )
    result = eternal.run_conversation_durable("hello", session_id="s1")
    assert result["final_text"] == "reply:hello"
    assert result["iterations"] == 1
    assert result["stopped_by"] == "end_turn"

    # Journal recorded the invocation.
    import sqlite3
    db = tmp_path / "rt" / "journal.sqlite3"
    conn = sqlite3.connect(db.as_posix())
    inv = conn.execute("SELECT COUNT(*) FROM invocations").fetchone()[0]
    conn.close()
    assert inv == 1


def test_eternal_agent_loop_quarantines_on_repeated_failure(tmp_path: Path) -> None:
    runtime = LocalRuntime(tmp_path / "rt")
    breaker = CircuitBreaker(after=2)

    class _BoomLoop:
        tools = {}
        llm = None

        def run_conversation(self, user_text: str, *, session_id: str):
            raise RuntimeError("nope")

    eternal = EternalAgentLoop(
        loop=_BoomLoop(), runtime=runtime, breaker=breaker, deadline_per_turn_s=10
    )
    for _ in range(2):
        with pytest.raises(RuntimeError):
            eternal.run_conversation_durable("x", session_id="s")
    assert breaker.is_quarantined(eternal.workflow_name)

    # Quarantined turn returns a structured response without invoking the loop.
    result = eternal.run_conversation_durable("y", session_id="s")
    assert result["stopped_by"] == "quarantined"


def test_eternal_agent_loop_enforces_deadline(tmp_path: Path) -> None:
    import time as _time

    runtime = LocalRuntime(tmp_path / "rt")
    breaker = CircuitBreaker(after=10)

    class _SlowLoop:
        tools = {}
        llm = None

        def run_conversation(self, user_text: str, *, session_id: str):
            _time.sleep(2.0)
            class TR: ...
            tr = TR()
            tr.final_text = "done"
            tr.iterations = 1
            tr.tool_calls = []
            tr.stopped_by = "end_turn"
            return tr

    eternal = EternalAgentLoop(
        loop=_SlowLoop(), runtime=runtime, breaker=breaker, deadline_per_turn_s=1
    )
    with pytest.raises(TimeoutError) as exc:
        eternal.run_conversation_durable("hi", session_id="s")
    assert "1s deadline" in str(exc.value)


def _make_idempotent_echo():
    def echo(msg: str) -> str:
        return f"echoed:{msg}"

    echo.__eternal_idempotent__ = True
    return echo
