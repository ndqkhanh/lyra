"""Wave-D Task 14: ``PreflightPlugin`` — wire the estimator into the loop.

Wave-A shipped :func:`preflight` as a library helper. This task wires
it into the agent loop as a real plugin so an oversized prompt is
rejected *before* the provider bills it.

Contract:

* The plugin is duck-typed against :class:`AgentLoop`'s plugin
  protocol (it implements ``pre_llm_call``).
* When the estimate fits the model window, the plugin returns
  silently and emits an HIR event ``preflight.ok``.
* When the estimate exceeds the window, the plugin raises
  :class:`ContextWindowExceeded` (so the REPL sees a clean stop with
  a ``/compact`` hint instead of a half-billed provider call).
* Unknown models pass through without raising.

Six RED tests:

1. Plugin instantiates from a model name + max_output.
2. ``pre_llm_call`` is silent for an in-budget prompt.
3. ``pre_llm_call`` emits an HIR event for in-budget.
4. ``pre_llm_call`` raises :class:`ContextWindowExceeded` for an
   oversized prompt.
5. ``pre_llm_call`` emits an HIR ``preflight.exceeded`` event before
   raising.
6. Unknown models do not raise (defer to provider error handling).
"""
from __future__ import annotations

import pytest


def test_plugin_constructs_from_model_and_max_output() -> None:
    from lyra_core.providers.preflight_plugin import PreflightPlugin

    p = PreflightPlugin(model="gpt-4o-mini", max_output=512)
    assert p.model == "gpt-4o-mini"
    assert p.max_output == 512


def test_pre_llm_call_silent_for_in_budget() -> None:
    from lyra_core.agent.loop import LLMCtx
    from lyra_core.providers.preflight_plugin import PreflightPlugin

    p = PreflightPlugin(model="gpt-4o-mini", max_output=128)
    ctx = LLMCtx(
        session_id="s",
        iteration=0,
        messages=[{"role": "user", "content": "hello"}],
    )
    p.pre_llm_call(ctx)  # should not raise


def test_pre_llm_call_emits_hir_for_in_budget() -> None:
    from lyra_core.agent.loop import LLMCtx
    from lyra_core.hir.events import RingBuffer
    from lyra_core.providers.preflight_plugin import PreflightPlugin

    ring = RingBuffer(cap=8)
    try:
        p = PreflightPlugin(model="gpt-4o-mini", max_output=128)
        ctx = LLMCtx(
            session_id="s",
            iteration=0,
            messages=[{"role": "user", "content": "hi"}],
        )
        p.pre_llm_call(ctx)
        events = [e for e in ring.snapshot() if e["name"] == "preflight.ok"]
        assert events, "preflight.ok event should be emitted"
    finally:
        ring.detach()


def test_pre_llm_call_raises_for_oversized() -> None:
    from lyra_core.agent.loop import LLMCtx
    from lyra_core.providers.preflight import ContextWindowExceeded
    from lyra_core.providers.preflight_plugin import PreflightPlugin

    huge = "x" * 1_000_000  # ~250k tokens at len/4
    p = PreflightPlugin(model="gpt-4o-mini", max_output=1024)
    ctx = LLMCtx(
        session_id="s",
        iteration=0,
        messages=[{"role": "user", "content": huge}],
    )
    with pytest.raises(ContextWindowExceeded):
        p.pre_llm_call(ctx)


def test_pre_llm_call_emits_hir_before_raising() -> None:
    from lyra_core.agent.loop import LLMCtx
    from lyra_core.hir.events import RingBuffer
    from lyra_core.providers.preflight import ContextWindowExceeded
    from lyra_core.providers.preflight_plugin import PreflightPlugin

    ring = RingBuffer(cap=8)
    try:
        huge = "x" * 1_000_000
        p = PreflightPlugin(model="gpt-4o-mini", max_output=1024)
        ctx = LLMCtx(
            session_id="s",
            iteration=0,
            messages=[{"role": "user", "content": huge}],
        )
        try:
            p.pre_llm_call(ctx)
        except ContextWindowExceeded:
            pass
        events = [e for e in ring.snapshot() if e["name"] == "preflight.exceeded"]
        assert events
    finally:
        ring.detach()


def test_unknown_model_does_not_raise() -> None:
    from lyra_core.agent.loop import LLMCtx
    from lyra_core.providers.preflight_plugin import PreflightPlugin

    p = PreflightPlugin(model="acme-llm-v999", max_output=128)
    ctx = LLMCtx(
        session_id="s",
        iteration=0,
        messages=[{"role": "user", "content": "x" * 1_000_000}],
    )
    p.pre_llm_call(ctx)  # unknown model passes through
