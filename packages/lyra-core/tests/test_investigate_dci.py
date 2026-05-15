"""Tests for the DCI investigate-mode primitives (Bundle DCI-1/2/3).

Cite: arXiv:2605.05242 — *Beyond Semantic Similarity: Rethinking
Retrieval for Agentic Search via Direct Corpus Interaction*; reference
impl ``github.com/DCI-Agent/DCI-Agent-Lite``.

These tests pin the *contracts* — pure value objects, no LLM, no
filesystem outside ``tmp_path``. The integration with the agent loop
lives in a later bundle and has its own tests.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from lyra_core.investigate import (
    INVESTIGATE_PROMPT_BODY,
    BudgetExceeded,
    ContextLevel,
    ContextLevelPlan,
    CorpusMount,
    CorpusMountError,
    InvestigationBudget,
    build_system_prompt,
    plan_for_level,
)

# ---------------------------------------------------------------------------
# InvestigationBudget
# ---------------------------------------------------------------------------


class _FakeClock:
    """Monotonic clock that advances only via ``tick``."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def tick(self, dt: float) -> None:
        self.now += dt


class TestInvestigationBudget:
    def test_default_caps_match_dci_lite(self) -> None:
        b = InvestigationBudget()
        assert b.max_turns == 300                  # DCI-Agent-Lite default
        assert b.max_bash_calls == 200
        assert b.max_bytes_read == 100_000_000
        assert b.wall_clock_s == 1800.0

    def test_record_turn_within_cap(self) -> None:
        b = InvestigationBudget(max_turns=3)
        for _ in range(3):
            b.record_turn()
        assert b.turns_used == 3

    def test_record_turn_exceeds_cap_raises(self) -> None:
        b = InvestigationBudget(max_turns=2)
        b.record_turn()
        b.record_turn()
        with pytest.raises(BudgetExceeded) as exc:
            b.record_turn()
        assert exc.value.axis == "turns"
        assert exc.value.cap == 2

    def test_record_bash_call_exceeds_cap_raises(self) -> None:
        b = InvestigationBudget(max_bash_calls=1)
        b.record_bash_call()
        with pytest.raises(BudgetExceeded) as exc:
            b.record_bash_call()
        assert exc.value.axis == "bash_calls"

    def test_record_bytes_accumulates(self) -> None:
        b = InvestigationBudget(max_bytes_read=100)
        b.record_bytes(40)
        b.record_bytes(50)
        assert b.bytes_read_used == 90
        with pytest.raises(BudgetExceeded) as exc:
            b.record_bytes(20)
        assert exc.value.axis == "bytes_read"

    def test_record_bytes_rejects_negative(self) -> None:
        b = InvestigationBudget()
        with pytest.raises(ValueError):
            b.record_bytes(-1)

    def test_wall_clock_uses_injected_clock(self) -> None:
        clock = _FakeClock()
        b = InvestigationBudget(wall_clock_s=10.0, clock=clock)
        b.start()
        clock.tick(5.0)
        b.check_wall_clock()              # within budget
        assert b.wall_clock_used == 5.0
        clock.tick(6.0)
        with pytest.raises(BudgetExceeded) as exc:
            b.check_wall_clock()
        assert exc.value.axis == "wall_clock_s"

    def test_check_wall_clock_no_op_before_start(self, tmp_path: Path) -> None:
        _ = tmp_path  # silence unused-fixture lint; conftest provides it
        b = InvestigationBudget(wall_clock_s=0.0)
        b.check_wall_clock()              # never started — no crash

    def test_start_is_idempotent(self) -> None:
        clock = _FakeClock()
        b = InvestigationBudget(clock=clock)
        b.start()
        clock.tick(7.0)
        b.start()                          # second call must not reset
        assert b.wall_clock_used == 7.0


# ---------------------------------------------------------------------------
# CorpusMount
# ---------------------------------------------------------------------------


class TestCorpusMount:
    def test_rejects_relative_root(self, tmp_path: Path) -> None:
        with pytest.raises(CorpusMountError):
            CorpusMount(root=Path("relative/path"))

    def test_rejects_non_path_root(self) -> None:
        with pytest.raises(CorpusMountError):
            CorpusMount(root="/string/not/path")     # type: ignore[arg-type]

    def test_rejects_zero_max_file_bytes(self, tmp_path: Path) -> None:
        with pytest.raises(CorpusMountError):
            CorpusMount(root=tmp_path, max_file_bytes=0)

    def test_default_is_read_only(self, tmp_path: Path) -> None:
        m = CorpusMount(root=tmp_path)
        assert m.read_only is True

    def test_contains_inside(self, tmp_path: Path) -> None:
        m = CorpusMount(root=tmp_path)
        inside = tmp_path / "a" / "b.txt"
        inside.parent.mkdir()
        inside.write_text("hi")
        assert m.contains(inside) is True

    def test_contains_outside(self, tmp_path: Path) -> None:
        m = CorpusMount(root=tmp_path / "deep")
        (tmp_path / "deep").mkdir()
        outside = tmp_path / "shallow.txt"
        outside.write_text("hi")
        assert m.contains(outside) is False

    def test_is_excluded_matches_glob(self, tmp_path: Path) -> None:
        m = CorpusMount(root=tmp_path)
        assert m.is_excluded(".git/HEAD") is True
        assert m.is_excluded("node_modules/foo/bar.js") is True
        assert m.is_excluded("src/main.py") is False

    def test_assert_readable_inside_passes(self, tmp_path: Path) -> None:
        m = CorpusMount(root=tmp_path)
        f = tmp_path / "doc.txt"
        f.write_text("ok")
        resolved = m.assert_readable(f)
        assert resolved == f.resolve()

    def test_assert_readable_rejects_outside(self, tmp_path: Path) -> None:
        inner = tmp_path / "inside"
        inner.mkdir()
        outer = tmp_path / "outside.txt"
        outer.write_text("nope")
        m = CorpusMount(root=inner)
        with pytest.raises(CorpusMountError, match="escapes mount"):
            m.assert_readable(outer)

    def test_assert_readable_rejects_too_large(self, tmp_path: Path) -> None:
        m = CorpusMount(root=tmp_path, max_file_bytes=10)
        big = tmp_path / "big.txt"
        big.write_bytes(b"x" * 100)
        with pytest.raises(CorpusMountError, match="max_file_bytes"):
            m.assert_readable(big)

    def test_assert_readable_rejects_missing(self, tmp_path: Path) -> None:
        m = CorpusMount(root=tmp_path)
        with pytest.raises(CorpusMountError, match="does not exist"):
            m.assert_readable(tmp_path / "ghost.txt")


# ---------------------------------------------------------------------------
# ContextLevel + plan_for_level
# ---------------------------------------------------------------------------


class TestContextLevel:
    def test_off_is_no_op(self) -> None:
        plan = plan_for_level(ContextLevel.OFF)
        assert plan.is_no_op is True

    def test_level1_only_truncates(self) -> None:
        plan = plan_for_level(ContextLevel.TRUNCATE_LIGHT)
        assert plan.truncate_oldest_tool_outputs is True
        assert plan.relevance_filter_tool_outputs is False
        assert plan.ngc_running_summary is False
        assert plan.per_window_summary is False

    def test_level2_adds_relevance(self) -> None:
        plan = plan_for_level(ContextLevel.TRUNCATE_HARD)
        assert plan.truncate_oldest_tool_outputs is True
        assert plan.relevance_filter_tool_outputs is True
        assert plan.ngc_running_summary is False

    def test_level3_adds_ngc(self) -> None:
        """Headline 62.9% BCP run uses level3."""
        plan = plan_for_level(ContextLevel.TRUNCATE_PLUS_COMPACT)
        assert plan.truncate_oldest_tool_outputs is True
        assert plan.relevance_filter_tool_outputs is True
        assert plan.ngc_running_summary is True
        assert plan.per_window_summary is False

    def test_level4_adds_window_summary(self) -> None:
        plan = plan_for_level(ContextLevel.FULL)
        assert all(
            (
                plan.truncate_oldest_tool_outputs,
                plan.relevance_filter_tool_outputs,
                plan.ngc_running_summary,
                plan.per_window_summary,
            )
        )

    def test_plans_are_frozen(self) -> None:
        plan = plan_for_level(ContextLevel.OFF)
        with pytest.raises(FrozenInstanceError):
            plan.truncate_oldest_tool_outputs = True   # type: ignore[misc]

    def test_levels_are_int_ordered(self) -> None:
        assert int(ContextLevel.OFF) == 0
        assert int(ContextLevel.FULL) == 4

    def test_plan_for_unknown_level_raises(self) -> None:
        class _Bogus:
            pass

        with pytest.raises(KeyError):
            plan_for_level(_Bogus())                    # type: ignore[arg-type]

    def test_plan_returned_is_typed(self) -> None:
        assert isinstance(plan_for_level(ContextLevel.OFF), ContextLevelPlan)


# ---------------------------------------------------------------------------
# build_system_prompt
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_body_advertises_three_tools(self) -> None:
        for tool in ("codesearch", "read_file", "execute_code"):
            assert tool in INVESTIGATE_PROMPT_BODY

    def test_body_enforces_path_line_citations(self) -> None:
        assert "path:line" in INVESTIGATE_PROMPT_BODY

    def test_body_has_no_react_scaffold(self) -> None:
        """The paper's whole point: skip the ReAct theatre."""
        forbidden = ("Thought:", "Action:", "Observation:", "ReAct")
        for token in forbidden:
            assert token not in INVESTIGATE_PROMPT_BODY

    def test_build_prompt_includes_root(self, tmp_path: Path) -> None:
        m = CorpusMount(root=tmp_path)
        prompt = build_system_prompt(m)
        assert str(tmp_path) in prompt
        assert "Read-only: yes" in prompt

    def test_build_prompt_marks_writable_mount(self, tmp_path: Path) -> None:
        m = CorpusMount(root=tmp_path, read_only=False)
        prompt = build_system_prompt(m)
        assert "Read-only: no" in prompt
