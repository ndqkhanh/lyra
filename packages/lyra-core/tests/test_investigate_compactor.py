"""Tests for :func:`compact_messages` — the level0..4 thermostat made live.

Cite: arXiv:2605.05242 §4.5 (RQ5 — context management).

These tests pin the *behavioural contract* of each level: which tool
outputs get dropped, which get kept, when the summary marker is
injected. The runner-level integration (LLM shim → compaction → real
model) is exercised separately in ``test_investigate_runner.py``.
"""
from __future__ import annotations

import pytest

from lyra_core.investigate import (
    CompactionReport,
    ContextLevel,
    compact_messages,
    plan_for_level,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _msg(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def _trajectory(n_tool: int) -> list[dict]:
    """A typical investigation transcript: user, then n alternating turns."""
    msgs: list[dict] = [
        _msg("system", "you are an investigator"),
        _msg("user", "find FORTY_TWO across the corpus"),
    ]
    for i in range(n_tool):
        msgs.append(_msg("assistant", f"running tool call {i}"))
        msgs.append(_msg("tool", f"hit {i}: FORTY_TWO mentioned in file_{i}.md"))
    msgs.append(_msg("assistant", "drafting answer"))
    return msgs


# ---------------------------------------------------------------------------
# Level 0 — no-op
# ---------------------------------------------------------------------------


class TestLevelOff:
    def test_returns_input_unchanged(self) -> None:
        msgs = _trajectory(3)
        plan = plan_for_level(ContextLevel.OFF)
        out, report = compact_messages(msgs, plan)
        assert out == msgs
        assert report.messages_before == report.messages_after
        assert report.tool_outputs_dropped == 0
        assert report.summary_injected is False

    def test_returns_new_list_not_alias(self) -> None:
        msgs = _trajectory(1)
        out, _ = compact_messages(msgs, plan_for_level(ContextLevel.OFF))
        assert out is not msgs                 # safe to mutate the result


# ---------------------------------------------------------------------------
# Level 1 — truncate oldest tool outputs
# ---------------------------------------------------------------------------


class TestLevelTruncateLight:
    def test_keeps_n_most_recent_tool_outputs(self) -> None:
        msgs = _trajectory(10)
        plan = plan_for_level(ContextLevel.TRUNCATE_LIGHT)
        out, report = compact_messages(msgs, plan, max_tool_outputs_kept=3)
        tool_msgs = [m for m in out if m["role"] == "tool"]
        assert len(tool_msgs) == 3
        # The most recent three must survive.
        assert tool_msgs[-1]["content"] == "hit 9: FORTY_TWO mentioned in file_9.md"
        assert tool_msgs[0]["content"] == "hit 7: FORTY_TWO mentioned in file_7.md"
        assert report.tool_outputs_dropped == 7

    def test_no_drop_when_under_threshold(self) -> None:
        msgs = _trajectory(2)
        plan = plan_for_level(ContextLevel.TRUNCATE_LIGHT)
        out, report = compact_messages(msgs, plan, max_tool_outputs_kept=10)
        assert report.tool_outputs_dropped == 0
        tool_msgs = [m for m in out if m["role"] == "tool"]
        assert len(tool_msgs) == 2

    def test_preserves_system_and_user_messages(self) -> None:
        msgs = _trajectory(8)
        plan = plan_for_level(ContextLevel.TRUNCATE_LIGHT)
        out, _ = compact_messages(msgs, plan, max_tool_outputs_kept=2)
        roles = [m["role"] for m in out]
        assert roles[0] == "system"
        assert "user" in roles
        # No summary at level 1 — only drop, never inject.
        assert all("compacted" not in str(m.get("content", "")) for m in out)

    def test_summary_not_injected_at_level1(self) -> None:
        msgs = _trajectory(10)
        plan = plan_for_level(ContextLevel.TRUNCATE_LIGHT)
        _, report = compact_messages(msgs, plan, max_tool_outputs_kept=2)
        assert report.summary_injected is False


# ---------------------------------------------------------------------------
# Level 2 — relevance filter on tool outputs
# ---------------------------------------------------------------------------


class TestLevelTruncateHard:
    def test_drops_irrelevant_tool_outputs(self) -> None:
        msgs = [
            _msg("system", "investigator"),
            _msg("user", "find FORTY_TWO"),
            _msg("tool", "hit: FORTY_TWO in intro.md"),
            _msg("tool", "hit: completely unrelated content about cats"),
            _msg("tool", "hit: FORTY_TWO again in appendix.md"),
        ]
        plan = plan_for_level(ContextLevel.TRUNCATE_HARD)
        out, report = compact_messages(msgs, plan, max_tool_outputs_kept=10)
        tool_contents = [m["content"] for m in out if m["role"] == "tool"]
        assert all("FORTY_TWO" in c for c in tool_contents)
        assert report.tool_outputs_dropped == 1

    def test_relevance_passes_when_no_query_keywords(self) -> None:
        msgs = [
            _msg("user", "x"),                          # too short — no tokens >= 3
            _msg("tool", "anything goes"),
        ]
        plan = plan_for_level(ContextLevel.TRUNCATE_HARD)
        out, report = compact_messages(msgs, plan)
        # With no usable keywords, the relevance filter is a no-op.
        assert any(m["role"] == "tool" for m in out)
        assert report.tool_outputs_dropped == 0


# ---------------------------------------------------------------------------
# Level 3 — NGC running summary injected
# ---------------------------------------------------------------------------


class TestLevelTruncatePlusCompact:
    def test_injects_summary_marker_when_anything_dropped(self) -> None:
        msgs = _trajectory(10)
        plan = plan_for_level(ContextLevel.TRUNCATE_PLUS_COMPACT)
        out, report = compact_messages(msgs, plan, max_tool_outputs_kept=2)
        assert report.summary_injected is True
        marker = next(m for m in out if "compacted" in str(m.get("content", "")))
        assert "tool outputs" in marker["content"]

    def test_no_marker_when_nothing_dropped(self) -> None:
        msgs = _trajectory(1)
        plan = plan_for_level(ContextLevel.TRUNCATE_PLUS_COMPACT)
        _, report = compact_messages(msgs, plan, max_tool_outputs_kept=10)
        assert report.summary_injected is False


# ---------------------------------------------------------------------------
# Level 4 — per-window summarizer
# ---------------------------------------------------------------------------


class TestLevelFull:
    def test_summarizer_called_when_provided(self) -> None:
        seen: list[int] = []

        def summarizer(dropped: list[dict]) -> str:
            seen.append(len(dropped))
            return "digest of dropped turns"

        msgs = _trajectory(5)
        plan = plan_for_level(ContextLevel.FULL)
        out, _ = compact_messages(
            msgs, plan, max_tool_outputs_kept=1, summarizer=summarizer,
        )
        assert seen, "summarizer should have been invoked"
        marker = next(m for m in out if "digest" in str(m.get("content", "")))
        assert "digest of dropped turns" in marker["content"]

    def test_summarizer_failure_does_not_crash(self) -> None:
        def broken(_dropped: list[dict]) -> str:
            raise RuntimeError("oops")

        msgs = _trajectory(5)
        plan = plan_for_level(ContextLevel.FULL)
        out, report = compact_messages(
            msgs, plan, max_tool_outputs_kept=1, summarizer=broken,
        )
        assert report.summary_injected is True
        # The marker reports the failure inline — never raises.
        marker = next(m for m in out if "summarizer failed" in str(m.get("content", "")))
        assert "oops" in marker["content"]

    def test_no_summarizer_falls_back_to_marker(self) -> None:
        msgs = _trajectory(5)
        plan = plan_for_level(ContextLevel.FULL)
        out, report = compact_messages(msgs, plan, max_tool_outputs_kept=1)
        assert report.summary_injected is True
        marker = next(m for m in out if "compacted" in str(m.get("content", "")))
        assert "compacted" in marker["content"]


# ---------------------------------------------------------------------------
# CompactionReport — bytes accounting
# ---------------------------------------------------------------------------


class TestCompactionReport:
    def test_bytes_after_less_than_before_when_dropping(self) -> None:
        msgs = _trajectory(10)
        plan = plan_for_level(ContextLevel.TRUNCATE_PLUS_COMPACT)
        _, report = compact_messages(msgs, plan, max_tool_outputs_kept=2)
        assert report.bytes_after < report.bytes_before
        assert report.messages_after < report.messages_before + 1  # +1 for marker

    def test_returns_compaction_report_instance(self) -> None:
        msgs = _trajectory(1)
        _, report = compact_messages(msgs, plan_for_level(ContextLevel.OFF))
        assert isinstance(report, CompactionReport)

    def test_report_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        msgs = _trajectory(1)
        _, report = compact_messages(msgs, plan_for_level(ContextLevel.OFF))
        with pytest.raises(FrozenInstanceError):
            report.messages_before = 0   # type: ignore[misc]


# ---------------------------------------------------------------------------
# Integration with the runner's LLM shim — via the public InvestigationRunner
# ---------------------------------------------------------------------------


class TestRunnerCompactsBetweenTurns:
    def test_runner_collects_compaction_reports(self, tmp_path) -> None:
        """End-to-end: runner wires the compactor into every LLM call."""
        from lyra_core.investigate import (
            ContextLevel as CL,
        )
        from lyra_core.investigate import (
            CorpusMount,
            InvestigationBudget,
            InvestigationRunner,
        )

        (tmp_path / "doc.md").write_text("FORTY_TWO\n")
        mount = CorpusMount(root=tmp_path.resolve())

        class _ToolThenStop:
            def __init__(self) -> None:
                self.calls = 0

            def generate(self, *, messages, tools) -> dict:
                self.calls += 1
                if self.calls == 1:
                    return {
                        "content": "",
                        "tool_calls": [
                            {"id": "c1", "name": "codesearch",
                             "arguments": {"pattern": "FORTY_TWO"}},
                        ],
                        "stop_reason": "tool_use",
                    }
                return {
                    "content": "found at doc.md:1",
                    "tool_calls": [],
                    "stop_reason": "end_turn",
                }

        runner = InvestigationRunner(
            llm=_ToolThenStop(),
            mount=mount,
            budget=InvestigationBudget(),
            context_level=CL.TRUNCATE_PLUS_COMPACT,
        )
        result = runner.run("FORTY_TWO?")
        assert result.stopped_by == "end_turn"
        # One compaction report per LLM call (two calls → two reports).
        assert len(result.compaction_reports) == 2
        assert all(isinstance(r, CompactionReport) for r in result.compaction_reports)
