"""Wave-D Task 13: ``BudgetMeter`` — live token → USD deduction.

The Wave-C ``BudgetCap`` / :func:`enforce` pair was a *classifier*:
"given a current spend, where do I sit relative to the cap?". That
left the missing piece — *who updates the spend?* — to whoever
called the agent loop. The meter closes that gap:

* :meth:`record_usage` takes ``prompt_tokens``, ``completion_tokens``,
  and a ``model`` name; multiplies through a price table; and
  appends the dollar delta to ``current_usd``.
* :meth:`gate` returns ``BudgetStatus.EXCEEDED`` early when the meter
  is already over the cap, so the caller can skip the LLM round-trip
  entirely.
* :meth:`reset` zeros the spend (``/budget reset``).

Six RED tests:

1. Empty meter is at $0 with status ``OK``.
2. Recording a known model accumulates the priced cost (``gpt-4o-mini``
   prompt/completion rates).
3. Unknown models fall back to a documented default rate without
   blowing up.
4. Crossing the alert threshold flips the report status to ``ALERT``.
5. Crossing the cap flips the report status to ``EXCEEDED`` and
   :meth:`gate` short-circuits.
6. :meth:`reset` zeros the spend back to ``OK``.
"""
from __future__ import annotations


def test_empty_meter_is_ok() -> None:
    from lyra_cli.interactive.budget import BudgetCap, BudgetMeter, BudgetStatus

    meter = BudgetMeter(cap=BudgetCap(limit_usd=1.0))
    assert meter.current_usd == 0.0
    assert meter.report().status == BudgetStatus.OK


def test_record_usage_known_model() -> None:
    from lyra_cli.interactive.budget import BudgetCap, BudgetMeter

    meter = BudgetMeter(cap=BudgetCap(limit_usd=10.0))
    delta = meter.record_usage(
        model="gpt-4o-mini",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )
    # Default table prices gpt-4o-mini at $0.15 / $0.60 per 1M tokens.
    assert delta > 0
    assert meter.current_usd == delta
    assert round(meter.current_usd, 4) == 0.75


def test_record_usage_unknown_model_uses_default() -> None:
    from lyra_cli.interactive.budget import BudgetCap, BudgetMeter

    meter = BudgetMeter(cap=BudgetCap(limit_usd=10.0))
    delta = meter.record_usage(
        model="acme-llm-v999",
        prompt_tokens=1_000_000,
        completion_tokens=0,
    )
    # Default fallback is $1 / $3 per 1M tokens — generous enough to
    # alert even for cheap unknown models.
    assert delta > 0


def test_alert_threshold_crossed() -> None:
    from lyra_cli.interactive.budget import (
        BudgetCap,
        BudgetMeter,
        BudgetStatus,
    )

    cap = BudgetCap(limit_usd=1.0, alert_pct=80.0)
    meter = BudgetMeter(cap=cap)
    meter.record_usage(model="gpt-4o-mini", prompt_tokens=0, completion_tokens=0)
    meter._current_usd = 0.85  # type: ignore[attr-defined]
    assert meter.report().status == BudgetStatus.ALERT


def test_cap_exceeded_blocks_via_gate() -> None:
    from lyra_cli.interactive.budget import (
        BudgetCap,
        BudgetMeter,
        BudgetStatus,
    )

    cap = BudgetCap(limit_usd=1.0)
    meter = BudgetMeter(cap=cap)
    meter._current_usd = 1.5  # type: ignore[attr-defined]
    decision = meter.gate()
    assert decision.status == BudgetStatus.EXCEEDED


def test_reset_zeros_spend() -> None:
    from lyra_cli.interactive.budget import (
        BudgetCap,
        BudgetMeter,
        BudgetStatus,
    )

    meter = BudgetMeter(cap=BudgetCap(limit_usd=1.0))
    meter._current_usd = 0.42  # type: ignore[attr-defined]
    meter.reset()
    assert meter.current_usd == 0.0
    assert meter.report().status == BudgetStatus.OK
