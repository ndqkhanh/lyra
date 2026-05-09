"""Wave-D Task 14: agent-loop plugin that wires :func:`preflight` in.

The Wave-A estimator answers "would this prompt fit?". This plugin
turns the answer into an enforceable check: the agent loop calls
``pre_llm_call`` before every LLM round, and the plugin runs the
estimator. If the prompt would exceed the configured model's
context window the plugin raises :class:`ContextWindowExceeded` so
the caller never bills a request the provider would reject.

Why a plugin (and not direct loop wiring)?

* Keeps :class:`AgentLoop` agnostic of provider specifics — the
  loop already exposes ``pre_llm_call`` for exactly this kind of
  side-channel veto.
* Lets the REPL (or eval harness) opt in/out per session — a
  scratch test can skip the plugin without touching the loop.
* Emits HIR events on both the happy and reject paths so ``/trace``
  surfaces a "preflight refused" event for the user.

Why raise instead of returning a value? :class:`AgentLoop` doesn't
inspect plugin return values; the only way for a plugin to stop a
turn is to raise. ``ContextWindowExceeded`` is a typed exception
subclassing :class:`RuntimeError`, so any caller that wraps
``run_conversation`` can match on it and render a clear "/compact"
hint without parsing strings.
"""
from __future__ import annotations

from typing import Any, Mapping

from lyra_core.hir.events import emit
from lyra_core.providers.preflight import (
    ContextWindowExceeded,
    PreflightReport,
    preflight,
)


class PreflightPlugin:
    """:class:`AgentLoop` plugin that estimates and gates LLM calls."""

    def __init__(
        self,
        *,
        model: str,
        max_output: int = 0,
        system: str = "",
    ) -> None:
        self.model = model
        self.max_output = max(int(max_output), 0)
        self.system = system or ""

    # ---- agent loop hook --------------------------------------------

    def pre_llm_call(self, ctx: Any) -> None:
        """Run :func:`preflight` over ``ctx.messages``.

        Raises :class:`ContextWindowExceeded` when the estimate would
        blow the model's window. Emits HIR events on both paths so
        ``/trace`` reflects the decision.
        """
        messages: list[Mapping[str, Any]] = list(getattr(ctx, "messages", []) or [])
        try:
            report: PreflightReport = preflight(
                model=self.model,
                messages=messages,
                system=self.system,
                tools=(),
                max_output=self.max_output,
            )
        except ContextWindowExceeded as exc:
            emit(
                "preflight.exceeded",
                model=self.model,
                max_output=self.max_output,
                reason=str(exc),
            )
            raise
        emit(
            "preflight.ok",
            model=self.model,
            estimated_input_tokens=report.estimated_input_tokens,
            max_output_tokens=report.max_output_tokens,
            context_window=report.context_window,
        )


__all__ = ["PreflightPlugin"]
