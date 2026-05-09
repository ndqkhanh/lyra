"""L312-8 — autocontinue plugin tests.

Twelve cases covering the four safeguards in the
``docs/306-stop-hook-auto-continue-pattern.md`` decision tree:

1.  No safeguard triggers → re-feed.
2.  ``stop_hook_active=True`` → allow (second-entry break).
3.  Cap reached → allow-cap with warning.
4.  Cost over watermark → allow-watermark with warning.
5.  Verifier returns True → allow-verifier.
6.  Verifier returns False + safeguards quiet → re-feed.
7.  Verifier raises → defaults to allow.
8.  Default user_message is non-empty actionable directive.
9.  AutoContinueState records fires + re_feeds correctly.
10. Composes with the AgentLoop end-to-end (drives a 2-iteration run).
11. Buggy "always-False" verifier still terminates at cap (4 safeguards
    in correct order regression).
12. cost_watermark_pct boundary: ratio == watermark → allow.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from lyra_core.agent.loop import (
    AgentLoop,
    ContinueLoop,
    IterationBudget,
    StopCtx,
)
from lyra_core.plugins.autocontinue import AutoContinuePlugin, AutoContinueState


@dataclass
class _LLM:
    queue: list[dict]

    def generate(self, *, messages, tools=None, **kwargs) -> dict:
        if not self.queue:
            return {"role": "assistant", "content": "done", "stop_reason": "end_turn"}
        return self.queue.pop(0)


@dataclass
class _Store:
    sessions: dict[str, list[dict]] = field(default_factory=dict)

    def start_session(self, *, session_id: str, **_: Any) -> None:
        self.sessions.setdefault(session_id, [])

    def append_message(self, **kwargs: Any) -> None:
        sid = kwargs["session_id"]
        self.sessions.setdefault(sid, []).append(kwargs)


def _ctx(**kwargs) -> StopCtx:
    defaults = dict(
        session_id="s1", iteration=1, final_text="done",
        stop_extensions=0, stop_hook_active=False,
    )
    defaults.update(kwargs)
    return StopCtx(**defaults)


# --- 1. No safeguard fires → ContinueLoop is raised ---------------------- #


def test_re_feeds_when_no_safeguard_fires():
    p = AutoContinuePlugin(verifier=lambda _: False)
    with pytest.raises(ContinueLoop) as ei:
        p.on_stop(_ctx())
    assert "not yet done" in ei.value.reason
    assert p.state.last_decision == "deny"
    assert p.state.re_feeds == 1


# --- 2. stop_hook_active=True → allow (second-entry break) -------------- #


def test_stop_hook_active_breaks_loop():
    p = AutoContinuePlugin(verifier=lambda _: False)
    p.on_stop(_ctx(stop_hook_active=True, stop_extensions=1))  # no raise
    assert p.state.last_decision == "allow"


# --- 3. Cap reached → allow-cap ----------------------------------------- #


def test_extension_cap_triggers_allow():
    p = AutoContinuePlugin(max_extensions=2, verifier=lambda _: False)
    p.on_stop(_ctx(stop_extensions=2))  # no raise
    assert p.state.last_decision == "allow-cap"
    assert any("cap reached" in w for w in p.state.last_warnings)


# --- 4. Cost watermark triggers → allow-watermark ----------------------- #


def test_cost_watermark_triggers_allow():
    cost_holder = [0.91]
    p = AutoContinuePlugin(
        verifier=lambda _: False,
        session_budget_usd=1.00,
        cost_so_far_fn=lambda: cost_holder[0],
        cost_watermark_pct=0.90,
    )
    p.on_stop(_ctx())  # no raise
    assert p.state.last_decision == "allow-watermark"
    assert any("cost watermark" in w for w in p.state.last_warnings)


# --- 5. Verifier True → allow-verifier ---------------------------------- #


def test_verifier_true_allows_stop():
    p = AutoContinuePlugin(verifier=lambda _: True)
    p.on_stop(_ctx())  # no raise
    assert p.state.last_decision == "allow-verifier"


# --- 6. Verifier False + safeguards quiet → re-feed -------------------- #


def test_verifier_false_re_feeds():
    p = AutoContinuePlugin(verifier=lambda _: False)
    with pytest.raises(ContinueLoop):
        p.on_stop(_ctx())
    assert p.state.last_decision == "deny"


# --- 7. Verifier raises → defaults to allow (no strand) ---------------- #


def test_verifier_exception_defaults_to_allow():
    def boom(_):
        raise RuntimeError("buggy verifier")

    p = AutoContinuePlugin(verifier=boom)
    p.on_stop(_ctx())  # no raise; defaults to allow
    assert p.state.last_decision == "allow-verifier"
    assert any("verifier raised" in w for w in p.state.last_warnings)


# --- 8. Default user_message is actionable ----------------------------- #


def test_default_user_message_is_actionable():
    p = AutoContinuePlugin()
    msg = p.user_message.lower()
    assert "continue" in msg
    assert any(w in msg for w in ("verify", "propose", "next step"))


# --- 9. State records fires and re_feeds correctly --------------------- #


def test_state_telemetry():
    p = AutoContinuePlugin(verifier=lambda _: False)
    with pytest.raises(ContinueLoop):
        p.on_stop(_ctx())
    p.on_stop(_ctx(stop_hook_active=True, stop_extensions=1))
    assert p.state.fires == 2
    assert p.state.re_feeds == 1


# --- 10. End-to-end with AgentLoop — drives a 2-iteration run ---------- #


def test_end_to_end_two_iteration_run():
    """The plugin re-feeds once, then the second-entry break terminates."""
    llm = _LLM(queue=[
        {"role": "assistant", "content": "first turn done", "stop_reason": "end_turn"},
        {"role": "assistant", "content": "second turn done", "stop_reason": "end_turn"},
    ])
    p = AutoContinuePlugin(verifier=lambda _: False, max_extensions=10)
    loop = AgentLoop(llm=llm, tools={}, store=_Store(), plugins=[p],
                     budget=IterationBudget(max=10))
    result = loop.run_conversation("go", session_id="s1")

    # First call: stop_hook_active=False, deny → re-feed.
    # Second call: stop_hook_active=True, allow → terminate.
    assert result.iterations == 2
    assert result.stop_extensions == 1
    assert result.stopped_by == "end_turn"


# --- 11. Always-False verifier still bounded by cap (4-safeguard regression) #


def test_always_false_verifier_bounded_by_cap_via_loop():
    """Without ``stop_hook_active`` short-circuit, this would loop until
    AgentLoop.max_stop_extensions kicks in. This is the
    ``claude-mem`` #1288 regression test."""
    llm = _LLM(queue=[
        {"role": "assistant", "content": "x", "stop_reason": "end_turn"}
    ] * 50)
    # Disable safeguard 1 by always returning False; rely on cap (safeguard 2)
    # at the AgentLoop level instead.

    class _NoBreak(AutoContinuePlugin):
        def on_stop(self, ctx: StopCtx) -> None:
            # Simulate a buggy plugin that ignores stop_hook_active.
            if ctx.stop_extensions >= self.max_extensions:
                return
            raise ContinueLoop(user_message="keep")

    p = _NoBreak(max_extensions=100, verifier=lambda _: False)
    loop = AgentLoop(llm=llm, tools={}, store=_Store(), plugins=[p],
                     budget=IterationBudget(max=100), max_stop_extensions=3)
    result = loop.run_conversation("go", session_id="s1")
    assert result.stopped_by == "stop_cap"
    assert result.stop_extensions == 3


# --- 12. Watermark boundary — exact equality triggers allow ------------ #


def test_watermark_boundary_inclusive():
    """ratio >= cost_watermark_pct (inclusive) → allow."""
    p = AutoContinuePlugin(
        verifier=lambda _: False,
        session_budget_usd=1.00,
        cost_so_far_fn=lambda: 0.90,
        cost_watermark_pct=0.90,
    )
    p.on_stop(_ctx())
    assert p.state.last_decision == "allow-watermark"
