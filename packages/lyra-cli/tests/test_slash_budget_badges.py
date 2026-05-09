"""Wave-C Task 5: ``/budget set`` enforcement + ``/badges`` from disk.

The v1 stubs only stored a number on the session and printed slash
counts. Wave-C ships:

* :mod:`lyra_cli.interactive.budget` — a tiny dataclass + ``enforce()``
  helper that classifies cumulative cost into ``ok / alert / exceeded``.
* ``/budget set <usd>`` — the verbose form that explicitly *sets* the
  cap (the bare ``/budget`` form keeps working for back-compat).
* ``/badges`` — reads ``~/.lyra/badges.json`` (or
  ``<repo_root>/.lyra/badges.json``) and renders any earned achievement
  chips. Falls back to the original "slash usage" view when no
  on-disk badge file is present.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_cli.interactive.budget import BudgetCap, BudgetStatus, enforce
from lyra_cli.interactive.session import InteractiveSession


# ---- BudgetCap.enforce ------------------------------------------------

def test_enforce_ok_below_80_pct() -> None:
    cap = BudgetCap(limit_usd=10.0, alert_pct=80.0)
    assert enforce(cap, current_usd=4.99).status == BudgetStatus.OK


def test_enforce_alert_at_or_above_80_pct() -> None:
    cap = BudgetCap(limit_usd=10.0, alert_pct=80.0)
    rep = enforce(cap, current_usd=8.0)
    assert rep.status == BudgetStatus.ALERT
    # The user-facing message must mention the percentage so the chip
    # is meaningful in the renderable.
    assert "80" in rep.message


def test_enforce_exceeded_at_100_pct() -> None:
    cap = BudgetCap(limit_usd=10.0)
    rep = enforce(cap, current_usd=10.01)
    assert rep.status == BudgetStatus.EXCEEDED
    assert "exceeded" in rep.message.lower() or "over" in rep.message.lower()


# ---- /budget set ------------------------------------------------------

def test_slash_budget_set_persists_cap_on_session(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    res = s.dispatch("/budget set 12.50")
    assert s.budget_cap_usd == pytest.approx(12.50)
    assert "12.50" in res.output


# ---- /badges from disk -----------------------------------------------

def test_slash_badges_reads_disk_file(tmp_path: Path) -> None:
    badges_path = tmp_path / ".lyra" / "badges.json"
    badges_path.parent.mkdir(parents=True)
    badges_path.write_text(
        json.dumps(
            [
                {"name": "first-prompt", "earned_at": "2026-04-24"},
                {"name": "tdd-streak-3", "earned_at": "2026-04-25"},
            ]
        ),
        encoding="utf-8",
    )
    s = InteractiveSession(repo_root=tmp_path)
    res = s.dispatch("/badges")
    assert "first-prompt" in res.output
    assert "tdd-streak-3" in res.output
