"""Red tests for the auto-skip Plan Mode heuristics.

Contract:
    - Trivial tasks: short + low-stakes keywords → skip plan
    - The literal string "plan" in the task force-opts-in → never skip
    - Complex tasks: long or no low-stakes signals → require plan
"""
from __future__ import annotations

import pytest

from lyra_core.plan.heuristics import SkipDecision, plan_skip_decision


def _d(task: str, **kw) -> SkipDecision:
    return plan_skip_decision(task, **kw)


def test_trivial_short_typo_fix_auto_skips() -> None:
    d = _d("fix typo in README", recent_edits_count=0)
    assert d.skip is True
    assert "short_task" in d.signals or "low_stakes_keywords" in d.signals


def test_trivial_rename_variable_auto_skips() -> None:
    d = _d("rename variable x to user_id", recent_edits_count=0)
    assert d.skip is True


def test_trivial_add_log_auto_skips() -> None:
    d = _d("add log line to auth handler", recent_edits_count=0)
    assert d.skip is True


def test_long_task_requires_plan() -> None:
    long = "Refactor authentication to support OIDC, migrate sessions to JWT, " * 5
    d = _d(long, recent_edits_count=0)
    assert d.skip is False


def test_word_plan_forces_plan_mode() -> None:
    d = _d("plan a small fix", recent_edits_count=0)
    assert d.skip is False
    assert d.reason and "plan" in d.reason.lower()


def test_already_in_flow_signal_adds_weight() -> None:
    """Many recent edits in the last 24h → user is deep in a flow; short typo fixes
    are safe to skip."""
    d = _d("fix comment", recent_edits_count=25)
    assert d.skip is True
    assert "already_in_flow" in d.signals


def test_ambiguous_short_task_without_keywords_requires_plan() -> None:
    """Short but no low-stakes keyword: still requires a plan."""
    d = _d("do the thing", recent_edits_count=0)
    assert d.skip is False


def test_skip_decision_records_signals_and_reason() -> None:
    d = _d("fix typo", recent_edits_count=30)
    assert isinstance(d.signals, list)
    assert d.reason


@pytest.mark.parametrize(
    "task",
    [
        "please design a new caching layer for our user service",
        "implement a new feature: export user data as CSV",
        "we need to migrate the database from mysql to postgres",
    ],
)
def test_design_implement_migrate_never_skip(task: str) -> None:
    d = _d(task, recent_edits_count=50)
    assert d.skip is False
