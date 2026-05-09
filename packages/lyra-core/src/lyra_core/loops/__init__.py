"""L312-3 + L312-5 — `/loop` slash + `lyra loop` CLI substrate.

Anchor: ``docs/308-autonomy-loop-synthesis.md`` layer 4–5.

A :class:`LoopSession` wraps any inner driver (``AgentLoop``,
subprocess Ralph runner, or a callable) with iteration accounting,
cache-aware interval enforcement (the 270 s cache-warm default; 300 s
rejected as worst-of-both), and a ``until_pred`` predicate that lets
the caller decide when to stop.

Composition:

- L312-3 owns ``LoopSession`` + interval validation.
- L312-4 owns the :class:`AgentContract` envelope; ``LoopSession``
  always carries one (default trivial contract if not specified).
- L312-5 owns :class:`HumanDirective` (a separate module here under
  ``directive``); ``LoopSession`` checks it at iteration boundaries.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from lyra_core.contracts import (
    AgentContract,
    BudgetEnvelope,
    ContractObservation,
    ContractState,
)
from .directive import HumanDirective


__all__ = [
    "LoopSession",
    "LoopState",
    "validate_interval",
    "InvalidInterval",
    "HumanDirective",
]


# --- Cache-aware interval validation ---------------------------------- #


CACHE_TTL_SECONDS = 300.0
CACHE_WARM_RECOMMEND_SECONDS = 270.0
CACHE_COLD_RECOMMEND_SECONDS = 1200.0


class InvalidInterval(ValueError):
    """Raised when ``--interval`` lands in the worst-of-both window.

    Specifically: any value in ``[300, 1199]`` pays the prompt-cache
    miss without amortising it. Reject and hint to the operator.
    """


def validate_interval(seconds: float) -> float:
    """Validate a loop interval per the cache-window rule.

    The Anthropic prompt cache has a 5-minute (300 s) TTL. Sleeping
    past it means the next wake-up reads the full conversation context
    uncached. So:

    - ``[60, 300)`` is fine — cache stays warm.
    - ``[300, 1200)`` is the worst-of-both — pay the cache miss without
      amortising. Rejected with a hint.
    - ``[1200, 3600]`` is fine — one cache miss buys a much longer wait.

    Hard floor at 60 s; hard ceiling at 3600 s (matches the runtime
    clamp in ``ScheduleWakeup`` skill).
    """
    if seconds < 60:
        raise InvalidInterval(
            f"interval={seconds}s below the 60s hard floor; "
            f"shorter intervals burn cache and rate-limit"
        )
    if seconds > 3600:
        raise InvalidInterval(
            f"interval={seconds}s above the 3600s ceiling; "
            f"use a cron schedule for hour+ horizons"
        )
    if 300 <= seconds < 1200:
        raise InvalidInterval(
            f"interval={seconds}s lands in the worst-of-both cache window "
            f"[300, 1200); drop to {CACHE_WARM_RECOMMEND_SECONDS:.0f} (cache-warm) "
            f"or raise to {CACHE_COLD_RECOMMEND_SECONDS:.0f} (cache-cold). "
            f"See docs/308-autonomy-loop-synthesis.md."
        )
    return float(seconds)


# --- LoopSession ------------------------------------------------------- #


PredicateFn = Callable[[Any], bool]
"""Caller-supplied 'are we done?' check; True = stop the loop."""

DriverFn = Callable[[str], dict]
"""Inner driver — given a prompt, returns one iteration's observation dict
with at least ``cost_usd: float`` and ``elapsed_s: float``. Optional:
``tool_calls: list``, ``content: str`` (last assistant text)."""


@dataclass
class LoopState:
    """Mutable telemetry the loop builds up across iterations."""

    iteration: int = 0
    last_content: str = ""
    last_directive_text: str = ""
    final_state: ContractState = ContractState.PENDING
    history: list[dict] = field(default_factory=list)


@dataclass
class LoopSession:
    """A self-paced or fixed-interval re-execution loop.

    - ``interval_s=None`` → self-paced (drive once per call to
      :meth:`step`; the caller decides cadence).
    - ``interval_s=270`` → cache-warm fixed interval; the loop sleeps
      between iterations.
    - ``until_pred`` → optional caller predicate that, given the last
      iteration's observation dict, returns True when work is done.
    """

    prompt: str
    driver: DriverFn
    contract: AgentContract = field(default_factory=AgentContract)
    interval_s: Optional[float] = None
    until_pred: Optional[PredicateFn] = None
    max_iter: int = 100
    directive: Optional[HumanDirective] = None
    sleep_fn: Callable[[float], None] = time.sleep
    state: LoopState = field(default_factory=LoopState)

    def __post_init__(self) -> None:
        if self.interval_s is not None:
            self.interval_s = validate_interval(self.interval_s)
        if self.contract.state == ContractState.PENDING:
            self.contract.start()

    def run(self) -> ContractState:
        """Drive the loop until a terminal state is reached."""
        for _ in range(self.max_iter):
            outcome = self.step()
            if outcome.is_terminal():
                break
            if self.interval_s is not None:
                self.sleep_fn(self.interval_s)
        else:
            # Reached max_iter without terminal — mark EXPIRED via contract.
            self.contract.terminate(cause="loop-max-iter")
        self.state.final_state = self.contract.state
        return self.contract.state

    def step(self) -> ContractState:
        """Drive one iteration; return the contract state after the step."""
        if self.contract.state.is_terminal():
            return self.contract.state

        # L312-5 — consume any pending HUMAN_DIRECTIVE.md before driving.
        prompt = self.prompt
        if self.directive is not None:
            text = self.directive.consume_if_changed()
            if text is not None:
                self.state.last_directive_text = text
                if "STOP" in text.upper().split():
                    self.contract.terminate(cause="human-directive-stop")
                    return self.contract.state
                prompt = (
                    f'<directive priority="high">\n{text.strip()}\n</directive>\n\n'
                    f"{self.prompt}"
                )

        self.state.iteration += 1
        try:
            obs_dict = self.driver(prompt)
        except KeyboardInterrupt:
            self.contract.terminate(cause="external-cancel")
            return self.contract.state

        self.state.last_content = str(obs_dict.get("content", ""))
        self.state.history.append(dict(obs_dict))

        observation = ContractObservation(
            cost_usd=float(obs_dict.get("cost_usd", 0.0) or 0.0),
            elapsed_s=float(obs_dict.get("elapsed_s", 0.0) or 0.0),
            tool_calls=tuple(obs_dict.get("tool_calls") or ()),
            external_signal=bool(obs_dict.get("external_signal", False)),
        )
        outcome = self.contract.step(observation)
        if outcome.is_terminal():
            return outcome

        # Caller-supplied done predicate.
        if self.until_pred is not None:
            try:
                if self.until_pred(obs_dict):
                    self.contract.terminate(cause="until-pred-satisfied")
                    return self.contract.state
            except Exception:
                # Predicate errors are non-fatal; continue running.
                pass

        return self.contract.state
