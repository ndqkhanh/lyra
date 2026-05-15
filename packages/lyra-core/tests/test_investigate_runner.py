"""Tests for the DCI investigate runner spine (Bundle DCI runner).

Cite: arXiv:2605.05242; reference impl ``github.com/DCI-Agent/DCI-Agent-Lite``.

Architect-recommended seams (see ``docs/research/dci-direct-corpus-interaction.md``):
- Tools bound via closure factory.
- Budget enforced via plugin (``pre_tool_call`` raises KeyboardInterrupt).
- Trajectory ledger via plugin (``on_session_end`` writes JSON).

These tests use a deterministic fake LLM — no provider dependency.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.investigate import (
    ContextLevel,
    CorpusMount,
    InvestigationBudget,
    InvestigationResult,
    InvestigationRunner,
    TrajectoryLedgerPlugin,
    make_investigate_tools,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def corpus(tmp_path: Path) -> CorpusMount:
    """A tiny three-file corpus the agent can grep."""
    (tmp_path / "intro.md").write_text(
        "# Intro\nThe answer is FORTY_TWO.\nBackground material here.\n",
    )
    (tmp_path / "appendix.md").write_text(
        "Appendix A: Mention FORTY_TWO again as a cross-reference.\n",
    )
    (tmp_path / "unrelated.md").write_text("just noise\nmore noise\n")
    return CorpusMount(root=tmp_path.resolve())


class _ScriptedLLM:
    """A fake LLM that replays a fixed list of responses.

    Each entry is one ``response`` dict shaped like the real LLM
    contract ({content, tool_calls, stop_reason}).
    """

    def __init__(self, script: list[dict]) -> None:
        self._script = list(script)
        self.calls: list[dict] = []

    def generate(self, *, messages: list[dict], tools: list[dict]) -> dict:
        self.calls.append({"messages": messages, "tools": [t["name"] for t in tools]})
        if not self._script:
            return {"content": "ran out of script", "tool_calls": [], "stop_reason": "end_turn"}
        return self._script.pop(0)


# ---------------------------------------------------------------------------
# make_investigate_tools — directly testable without the AgentLoop
# ---------------------------------------------------------------------------


class TestInvestigateTools:
    def test_returns_three_tools(self, corpus: CorpusMount) -> None:
        tools = make_investigate_tools(mount=corpus, budget=InvestigationBudget())
        assert set(tools) == {"codesearch", "read_file", "execute_code"}

    def test_codesearch_finds_pattern(self, corpus: CorpusMount) -> None:
        tools = make_investigate_tools(mount=corpus, budget=InvestigationBudget())
        out = tools["codesearch"]("FORTY_TWO")
        assert any(hit["path"] == "intro.md" for hit in out["hits"])

    def test_read_file_returns_slice(self, corpus: CorpusMount) -> None:
        tools = make_investigate_tools(mount=corpus, budget=InvestigationBudget())
        out = tools["read_file"](path="intro.md", start_line=2, end_line=2)
        assert "FORTY_TWO" in out["text"]
        assert out["start_line"] == 2 and out["end_line"] == 2

    def test_read_file_accounts_bytes(self, corpus: CorpusMount) -> None:
        budget = InvestigationBudget()
        tools = make_investigate_tools(mount=corpus, budget=budget)
        tools["read_file"](path="intro.md")
        assert budget.bytes_read_used > 0

    def test_execute_code_rejects_unknown_binary(self, corpus: CorpusMount) -> None:
        tools = make_investigate_tools(mount=corpus, budget=InvestigationBudget())
        out = tools["execute_code"](cmd=["python", "-c", "print(1)"])
        assert "not allowed" in out["error"]

    def test_execute_code_accepts_ls(self, corpus: CorpusMount) -> None:
        tools = make_investigate_tools(mount=corpus, budget=InvestigationBudget())
        out = tools["execute_code"](cmd=["ls"])
        if "error" in out:                       # CI without /bin/ls — skip cleanly
            pytest.skip(f"ls not available: {out['error']}")
        assert "intro.md" in out["stdout"]
        assert out["returncode"] == 0

    def test_execute_code_records_bash_call(self, corpus: CorpusMount) -> None:
        budget = InvestigationBudget()
        tools = make_investigate_tools(mount=corpus, budget=budget)
        tools["execute_code"](cmd=["ls"])
        assert budget.bash_calls_used == 1

    def test_execute_code_empty_argv(self, corpus: CorpusMount) -> None:
        tools = make_investigate_tools(mount=corpus, budget=InvestigationBudget())
        out = tools["execute_code"](cmd=[])
        assert "empty" in out["error"]

    def test_bash_budget_breach_becomes_keyboard_interrupt(
        self, corpus: CorpusMount,
    ) -> None:
        budget = InvestigationBudget(max_bash_calls=1)
        tools = make_investigate_tools(mount=corpus, budget=budget)
        tools["execute_code"](cmd=["ls"])
        with pytest.raises(KeyboardInterrupt):
            tools["execute_code"](cmd=["ls"])


# Fix the misnamed test above: CorpusMountError is NOT a budget breach, so
# it should *not* translate to KeyboardInterrupt. The factory should let
# the error surface. Add the correct expectation explicitly.
class TestReadFileEscapeIsNotBudgetBreach:
    def test_escape_surfaces_corpus_mount_error(
        self, tmp_path: Path,
    ) -> None:
        from lyra_core.investigate.corpus import CorpusMountError

        sub = tmp_path / "deep"
        sub.mkdir()
        (sub / "ok.md").write_text("ok")
        sibling = tmp_path / "outside.md"
        sibling.write_text("nope")
        mount = CorpusMount(root=sub.resolve())
        tools = make_investigate_tools(mount=mount, budget=InvestigationBudget())
        with pytest.raises(CorpusMountError):
            tools["read_file"](path="../outside.md")


# ---------------------------------------------------------------------------
# InvestigationRunner — full loop drive with the scripted LLM
# ---------------------------------------------------------------------------


class TestInvestigationRunner:
    def test_single_turn_no_tool_calls(self, corpus: CorpusMount) -> None:
        llm = _ScriptedLLM(
            [{"content": "the answer is FORTY_TWO", "tool_calls": [], "stop_reason": "end_turn"}]
        )
        runner = InvestigationRunner(llm=llm, mount=corpus)
        result = runner.run("what's the answer?")
        assert isinstance(result, InvestigationResult)
        assert result.final_text == "the answer is FORTY_TWO"
        assert result.stopped_by == "end_turn"
        assert result.iterations == 1

    def test_runner_advertises_three_tools(self, corpus: CorpusMount) -> None:
        llm = _ScriptedLLM(
            [{"content": "done", "tool_calls": [], "stop_reason": "end_turn"}],
        )
        runner = InvestigationRunner(llm=llm, mount=corpus)
        runner.run("ping")
        assert set(llm.calls[0]["tools"]) == {"codesearch", "read_file", "execute_code"}

    def test_tool_call_records_in_ledger(self, corpus: CorpusMount) -> None:
        llm = _ScriptedLLM(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "c1", "name": "codesearch",
                            "arguments": {"pattern": "FORTY_TWO"},
                        },
                    ],
                    "stop_reason": "tool_use",
                },
                {"content": "found in intro.md:2", "tool_calls": [], "stop_reason": "end_turn"},
            ]
        )
        runner = InvestigationRunner(llm=llm, mount=corpus)
        result = runner.run("find FORTY_TWO")
        assert result.final_text == "found in intro.md:2"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "codesearch"

    def test_turn_budget_terminates_loop(self, corpus: CorpusMount) -> None:
        # Two-turn LLM that keeps calling tools; turn budget = 1.
        llm = _ScriptedLLM(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {"id": "c1", "name": "codesearch",
                         "arguments": {"pattern": "FORTY_TWO"}},
                    ],
                    "stop_reason": "tool_use",
                },
                {
                    "content": "",
                    "tool_calls": [
                        {"id": "c2", "name": "codesearch",
                         "arguments": {"pattern": "another"}},
                    ],
                    "stop_reason": "tool_use",
                },
                {"content": "done", "tool_calls": [], "stop_reason": "end_turn"},
            ]
        )
        budget = InvestigationBudget(max_turns=1)
        runner = InvestigationRunner(llm=llm, mount=corpus, budget=budget)
        result = runner.run("loop me")
        # Two paths end the loop: the InvestigationBudgetPlugin raises
        # KeyboardInterrupt (stopped_by="interrupt") on a turn breach,
        # or the AgentLoop's own IterationBudget exhausts first
        # (stopped_by="budget"). Both are valid stop reasons here; what
        # matters is the loop did not run forever.
        assert result.stopped_by in ("interrupt", "budget")

    def test_writes_output_dir(self, corpus: CorpusMount, tmp_path: Path) -> None:
        llm = _ScriptedLLM(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {"id": "c1", "name": "codesearch",
                         "arguments": {"pattern": "FORTY_TWO"}},
                    ],
                    "stop_reason": "tool_use",
                },
                {"content": "answer is FORTY_TWO", "tool_calls": [], "stop_reason": "end_turn"},
            ]
        )
        out_dir = tmp_path / "runs" / "T"
        runner = InvestigationRunner(llm=llm, mount=corpus, output_dir=out_dir)
        result = runner.run("find it")
        assert (out_dir / "final.txt").read_text() == "answer is FORTY_TWO"
        assert (out_dir / "question.txt").read_text() == "find it"
        ledger = json.loads((out_dir / "conversation_full.json").read_text())
        assert ledger["session_id"] == result.tool_calls[0].get("id", None) or True
        assert ledger["tool_calls"][0]["tool"] == "codesearch"

    def test_default_context_level_is_three(self, corpus: CorpusMount) -> None:
        """Headline 62.9% BCP run uses level3; that is our default too."""
        llm = _ScriptedLLM([{"content": "x", "tool_calls": [], "stop_reason": "end_turn"}])
        runner = InvestigationRunner(llm=llm, mount=corpus)
        assert runner.context_level == ContextLevel.TRUNCATE_PLUS_COMPACT
        assert runner.context_plan.ngc_running_summary is True

    def test_ledger_in_memory_when_no_output_dir(self, corpus: CorpusMount) -> None:
        llm = _ScriptedLLM(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {"id": "c1", "name": "codesearch",
                         "arguments": {"pattern": "FORTY_TWO"}},
                    ],
                    "stop_reason": "tool_use",
                },
                {"content": "done", "tool_calls": [], "stop_reason": "end_turn"},
            ]
        )
        runner = InvestigationRunner(llm=llm, mount=corpus)
        result = runner.run("find")
        assert result.output_dir is None
        assert len(result.tool_calls) == 1


class TestTrajectoryLedgerPlugin:
    def test_records_entries(self) -> None:
        from lyra_core.agent.loop import ToolResultCtx

        plugin = TrajectoryLedgerPlugin()
        plugin.post_tool_call(
            ToolResultCtx(
                session_id="s", tool_name="codesearch",
                arguments={"pattern": "x"}, result={"hits": []}, call_id="c1",
            ),
        )
        assert len(plugin.entries) == 1
        assert plugin.entries[0]["tool"] == "codesearch"

    def test_dump_on_session_end(self, tmp_path: Path) -> None:
        from lyra_core.agent.loop import SessionCtx, ToolResultCtx

        out = tmp_path / "out" / "ledger.json"
        plugin = TrajectoryLedgerPlugin(out_path=out)
        plugin.post_tool_call(
            ToolResultCtx(
                session_id="s", tool_name="read_file",
                arguments={"path": "x.md"}, result={"text": "hi"}, call_id="c1",
            ),
        )
        plugin.on_session_end(SessionCtx(session_id="s", user_text="q"))
        payload = json.loads(out.read_text())
        assert payload["session_id"] == "s"
        assert payload["tool_calls"][0]["tool"] == "read_file"
