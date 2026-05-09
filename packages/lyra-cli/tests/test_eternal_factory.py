"""Eternal-factory + spawn_skill_review integration."""
from __future__ import annotations

from pathlib import Path

from harness_eternal.restate import LocalRuntime

from lyra_cli.eternal_factory import make_eternal_loop


class _NoopStore:
    def append_message(self, **_) -> None:
        return None


class _StubLLM:
    """Returns a single end-turn response — enough to drive a real AgentLoop."""

    def generate(self, *, messages, **kwargs):
        return {"content": "reviewed:ok", "tool_calls": [], "stop_reason": "end_turn"}


# AgentLoop-shaped stub for the make_eternal_loop tests (it doesn't run the
# real loop body, only its surface).
class _StubLoop:
    def __init__(self, llm=None, tools=None, store=None):
        self.llm = llm if llm is not None else _StubLLM()
        self.tools = tools if tools is not None else {}
        self.store = store if store is not None else _NoopStore()

    def run_conversation(self, user_text: str, *, session_id: str):
        class TR:
            final_text = f"reviewed:{user_text[:10]}"
            iterations = 1
            tool_calls = []
            stopped_by = "end_turn"

        return TR()


def test_make_eternal_loop_creates_journal_in_state_dir(tmp_path: Path) -> None:
    loop = _StubLoop()
    eternal = make_eternal_loop(
        loop, state_dir=tmp_path, workflow_name="lyra.test"
    )
    assert eternal.workflow_name == "lyra.test"
    assert (tmp_path / "restate" / "journal.sqlite3").exists()


def test_make_eternal_loop_runs_a_durable_turn(tmp_path: Path) -> None:
    loop = _StubLoop()
    eternal = make_eternal_loop(
        loop, state_dir=tmp_path, workflow_name="lyra.test",
        deadline_per_turn_s=10,
    )
    result = eternal.run_conversation_durable("hello", session_id="s")
    assert result["final_text"].startswith("reviewed:")

    # Verify journal recorded the invocation.
    import sqlite3
    db = tmp_path / "restate" / "journal.sqlite3"
    conn = sqlite3.connect(db.as_posix())
    workflows = [
        row[0] for row in conn.execute("SELECT DISTINCT workflow_name FROM invocations")
    ]
    conn.close()
    assert workflows == ["lyra.test"]


def test_make_eternal_loop_shared_runtime_across_calls(tmp_path: Path) -> None:
    """Two factories pointing at the same state_dir share the journal."""
    loop1 = _StubLoop()
    loop2 = _StubLoop()
    e1 = make_eternal_loop(loop1, state_dir=tmp_path, workflow_name="lyra.a")
    e2 = make_eternal_loop(loop2, state_dir=tmp_path, workflow_name="lyra.b")
    e1.run_conversation_durable("x", session_id="s1")
    e2.run_conversation_durable("y", session_id="s2")

    import sqlite3
    db = tmp_path / "restate" / "journal.sqlite3"
    conn = sqlite3.connect(db.as_posix())
    inv_count = conn.execute("SELECT COUNT(*) FROM invocations").fetchone()[0]
    conn.close()
    assert inv_count == 2


def test_spawn_skill_review_back_compat_when_state_dir_absent(tmp_path: Path) -> None:
    """When eternal_state_dir is None, spawn_skill_review behaves as before
    (no journal, no Restate dependency exercised)."""
    from lyra_skills.review.background import spawn_skill_review

    parent = _StubLoop(llm=_StubLLM(), tools={}, store=_NoopStore())
    out = spawn_skill_review(parent, session_id="parent-s")
    assert out == "reviewed:ok"


def test_spawn_skill_review_journals_when_state_dir_set(tmp_path: Path) -> None:
    from lyra_skills.review.background import spawn_skill_review

    parent = _StubLoop(llm=_StubLLM(), tools={}, store=_NoopStore())
    eternal_dir = tmp_path / "eternal"
    out = spawn_skill_review(
        parent, session_id="parent-s", eternal_state_dir=eternal_dir
    )
    assert out == "reviewed:ok"

    # Journal must contain a lyra.skill_review invocation.
    import sqlite3
    db = eternal_dir / "restate" / "journal.sqlite3"
    assert db.exists()
    conn = sqlite3.connect(db.as_posix())
    workflows = [
        row[0] for row in conn.execute("SELECT DISTINCT workflow_name FROM invocations")
    ]
    conn.close()
    assert "lyra.skill_review" in workflows
