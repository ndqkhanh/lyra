"""L4.1 follow-through — JournaledLLM proxy + mid-turn replay tests."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from harness_eternal.restate import LocalRuntime

from lyra_core.agent.eternal_llm import JournaledLLM


# ---------------------------------------------------------------------------
# JournaledLLM in isolation
# ---------------------------------------------------------------------------


class _StubLLM:
    """Minimal stub. Counts calls, returns sequential responses."""

    def __init__(self, scripted: list[dict] | None = None) -> None:
        self.calls = 0
        self._scripted = scripted or []

    def generate(self, *, messages, **kwargs):
        self.calls += 1
        if self._scripted and self.calls <= len(self._scripted):
            return self._scripted[self.calls - 1]
        return {"content": f"reply-{self.calls}", "tool_calls": []}


def test_journaled_llm_records_each_call(tmp_path: Path) -> None:
    runtime = LocalRuntime(tmp_path / "rt")
    inner = _StubLLM()
    proxy = JournaledLLM(inner=inner, journal=runtime.journal, turn_id="t-1")

    out1 = proxy.generate(messages=[{"role": "user", "content": "hi"}])
    out2 = proxy.generate(messages=[{"role": "user", "content": "again"}])
    assert inner.calls == 2
    assert proxy.call_count == 2
    assert out1["content"] == "reply-1"
    assert out2["content"] == "reply-2"


def test_journaled_llm_replays_on_same_turn_id(tmp_path: Path) -> None:
    """Reconstructing JournaledLLM with the same turn_id replays from journal."""
    runtime = LocalRuntime(tmp_path / "rt")
    inner = _StubLLM()
    p1 = JournaledLLM(inner=inner, journal=runtime.journal, turn_id="t-r")
    out1 = p1.generate(messages=[{"role": "user", "content": "hi"}])
    out2 = p1.generate(messages=[{"role": "user", "content": "again"}])
    assert inner.calls == 2

    # Simulate a crash + restart — fresh proxy, fresh inner LLM, same turn_id.
    inner2 = _StubLLM()
    p2 = JournaledLLM(inner=inner2, journal=runtime.journal, turn_id="t-r")
    replay1 = p2.generate(messages=[{"role": "user", "content": "hi"}])
    replay2 = p2.generate(messages=[{"role": "user", "content": "again"}])
    assert inner2.calls == 0  # never reached the underlying LLM
    assert replay1 == out1
    assert replay2 == out2


def test_journaled_llm_third_call_runs_fresh_after_two_recorded(tmp_path: Path) -> None:
    """The 'kill mid-turn' scenario — calls 1+2 recorded, restart calls 3
    sees calls 1+2 from journal and runs call 3 fresh."""
    runtime = LocalRuntime(tmp_path / "rt")
    inner1 = _StubLLM()
    p1 = JournaledLLM(inner=inner1, journal=runtime.journal, turn_id="t-mid")
    p1.generate(messages=[{"role": "user", "content": "a"}])
    p1.generate(messages=[{"role": "user", "content": "b"}])
    # ... process killed before the 3rd call would have completed.

    inner2 = _StubLLM()
    p2 = JournaledLLM(inner=inner2, journal=runtime.journal, turn_id="t-mid")
    out1 = p2.generate(messages=[{"role": "user", "content": "a"}])  # replay
    out2 = p2.generate(messages=[{"role": "user", "content": "b"}])  # replay
    out3 = p2.generate(messages=[{"role": "user", "content": "c"}])  # fresh
    assert out1["content"] == "reply-1"  # recorded
    assert out2["content"] == "reply-2"  # recorded
    assert out3["content"] == "reply-1"  # inner2 called once → reply-1
    assert inner2.calls == 1


def test_journaled_llm_supports_callable_inner(tmp_path: Path) -> None:
    """Inner LLM can be a bare callable (no .generate method)."""
    runtime = LocalRuntime(tmp_path / "rt")
    calls = {"n": 0}

    def inner(*, messages, **kwargs):
        calls["n"] += 1
        return {"content": f"r-{calls['n']}", "tool_calls": []}

    proxy = JournaledLLM(inner=inner, journal=runtime.journal, turn_id="t-c")
    out = proxy.generate(messages=[{"role": "user", "content": "hi"}])
    assert out["content"] == "r-1"
    assert calls["n"] == 1


def test_journaled_llm_rejects_invalid_inner(tmp_path: Path) -> None:
    runtime = LocalRuntime(tmp_path / "rt")
    with pytest.raises(TypeError, match="must expose .generate"):
        JournaledLLM(inner=42, journal=runtime.journal, turn_id="t")


def test_journaled_llm_rejects_non_mapping_response(tmp_path: Path) -> None:
    runtime = LocalRuntime(tmp_path / "rt")

    def bad_llm(*, messages, **kwargs):
        return "not a mapping"

    proxy = JournaledLLM(inner=bad_llm, journal=runtime.journal, turn_id="t-b")
    with pytest.raises(TypeError, match="expected Mapping"):
        proxy.generate(messages=[])


# ---------------------------------------------------------------------------
# End-to-end: EternalAgentLoop replay across a real AgentLoop-shaped stub
# ---------------------------------------------------------------------------


class _RealAgentLoopShape:
    """Honest stub of AgentLoop.run_conversation that drives a 3-call
    sequence: LLM call → tool dispatch → LLM call → tool dispatch →
    LLM call (final). This is the canonical loop body we want replay
    semantics for."""

    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    def run_conversation(self, user_text: str, *, session_id: str):
        from collections import namedtuple
        TR = namedtuple(
            "TR", ["final_text", "iterations", "tool_calls", "stopped_by"]
        )
        messages = [{"role": "user", "content": user_text}]

        # 1st LLM call — should ask for tool.
        r1 = self.llm.generate(messages=list(messages))
        messages.append({"role": "assistant", "content": r1.get("content", ""),
                         "tool_calls": r1.get("tool_calls", [])})
        tool_calls = list(r1.get("tool_calls", []))
        if tool_calls:
            for tc in tool_calls:
                fn = self.tools[tc["name"]]
                fn(**tc.get("arguments", {}))

        # 2nd LLM call.
        r2 = self.llm.generate(messages=list(messages))
        messages.append({"role": "assistant", "content": r2.get("content", "")})

        # 3rd LLM call — final.
        r3 = self.llm.generate(messages=list(messages))
        messages.append({"role": "assistant", "content": r3.get("content", "")})

        return TR(
            final_text=r3.get("content", ""),
            iterations=3,
            tool_calls=tool_calls,
            stopped_by="end_turn",
        )


def test_eternal_loop_replays_full_turn_deterministically(tmp_path: Path) -> None:
    """Crash mid-turn → restart with same invocation_id → recorded LLM
    results return at each iteration; tool side-effects don't re-fire."""
    from harness_eternal import CircuitBreaker
    from lyra_core.agent.eternal_turn import EternalAgentLoop

    tool_calls = {"n": 0}

    def echo(msg: str) -> str:
        tool_calls["n"] += 1
        return f"echoed:{msg}"

    echo.__eternal_idempotent__ = True

    runtime = LocalRuntime(tmp_path / "rt")
    breaker = CircuitBreaker(after=10)

    inner_llm = _StubLLM(
        scripted=[
            # 1st call: ask for the echo tool.
            {
                "content": "calling echo",
                "tool_calls": [
                    {"id": "t-1", "name": "echo", "arguments": {"msg": "hi"}}
                ],
            },
            # 2nd call: think.
            {"content": "thinking...", "tool_calls": []},
            # 3rd call: final.
            {"content": "DONE", "tool_calls": []},
        ]
    )

    loop = _RealAgentLoopShape(llm=inner_llm, tools={"echo": echo})
    eternal = EternalAgentLoop(
        loop=loop, runtime=runtime, breaker=breaker, deadline_per_turn_s=0,
        workflow_name="lyra.turn.replay",
    )

    # First run — completes naturally.
    result = eternal.run_conversation_durable("hello", session_id="s")
    assert result["final_text"] == "DONE"
    assert inner_llm.calls == 3
    assert tool_calls["n"] == 1

    # Force a "replay" by re-invoking with the same args (same invocation_id
    # is derived inside run_conversation_durable from session_id + ts +
    # text; to force the same id we reach in via the runtime). We instead
    # exploit the fact that the journal's *activity* table is keyed on
    # turn_id which is the invocation_id — and call _invoke_loop directly
    # with the same invocation_id to simulate the replay path.
    inner2 = _StubLLM()  # would never be invoked if replay works
    loop2 = _RealAgentLoopShape(llm=inner2, tools={"echo": echo})
    eternal2 = EternalAgentLoop(
        loop=loop2, runtime=runtime, breaker=breaker, deadline_per_turn_s=0,
        workflow_name="lyra.turn.replay",
    )
    # Pull the original invocation's id and re-invoke.
    import sqlite3
    db = tmp_path / "rt" / "journal.sqlite3"
    conn = sqlite3.connect(db.as_posix())
    inv_ids = [
        row[0] for row in conn.execute("SELECT id FROM invocations")
    ]
    conn.close()
    assert inv_ids
    invocation_id = inv_ids[0]

    # Replay path — call _invoke_loop directly with the recorded invocation_id.
    replay = eternal2._invoke_loop("hello", "s", invocation_id)
    assert replay["final_text"] == "DONE"
    assert inner2.calls == 0           # journal handled all 3 LLM calls
    assert tool_calls["n"] == 1        # echo was idempotent — still 1 call
