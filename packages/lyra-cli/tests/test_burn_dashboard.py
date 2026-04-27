"""Phase M.4 - dashboard renderer (data -> Rich Renderable)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from rich.console import Console

from lyra_cli.observatory.aggregator import (
    BurnReport, ModelBreakdown, CategoryBreakdown, SessionRow,
)
from lyra_cli.observatory.dashboard import render_dashboard


@pytest.fixture
def report():
    return BurnReport(
        period_start=1.0, period_end=2.0,
        total_cost_usd=Decimal("4.82"),
        total_tokens_in=1_200_000, total_tokens_out=384_000,
        total_turns=142,
        by_model=(
            ModelBreakdown("deepseek-v4-pro", Decimal("3.10"),
                           800_000, 200_000, 90, 0.78),
            ModelBreakdown("deepseek-v4-flash", Decimal("1.20"),
                           300_000, 130_000, 40, 0.92),
        ),
        by_category=(
            CategoryBreakdown("coding", Decimal("2.41"), 70),
            CategoryBreakdown("debugging", Decimal("1.05"), 30),
        ),
        by_session=(
            SessionRow("20260427-141000-aaa", 1.0, 2.0, 12,
                       Decimal("0.42"), "coding", "deepseek-v4-pro"),
        ),
        one_shot_rate=0.78, retry_rate=0.22,
    )


def _render(rep) -> str:
    c = Console(record=True, width=100)
    c.print(render_dashboard(rep, console=c))
    return c.export_text()


def test_render_includes_total_spend(report):
    assert "$4.82" in _render(report)


def test_render_includes_total_turns(report):
    assert "142" in _render(report)


def test_render_shows_one_shot_rate_as_percent(report):
    out = _render(report)
    assert "78" in out and "%" in out


def test_render_lists_top_model(report):
    assert "deepseek-v4-pro" in _render(report)


def test_render_lists_top_category(report):
    assert "coding" in _render(report)


def test_render_lists_recent_session(report):
    assert "20260427-141000-aaa" in _render(report)


def test_render_handles_empty_report():
    rep = BurnReport(
        0, 0, Decimal("0"), 0, 0, 0, (), (), (), 1.0, 0.0,
    )
    out = _render(rep)
    assert "no data" in out.lower() or "$0" in out
