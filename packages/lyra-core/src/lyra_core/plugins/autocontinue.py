"""L312-8 — autocontinue plugin (Stop-hook auto-continue).

Anchor: ``docs/306-stop-hook-auto-continue-pattern.md``. Ports the
Anthropic-blessed Stop-hook auto-continue pattern with the four
2026-best-practice safeguards baked in:

1. ``stop_hook_active`` second-entry break — strict, no recursion.
2. ``max_extensions`` extension cap — bounds total work.
3. Cost watermark at ``cost_watermark_pct`` of the session budget — soft
   stop before the contract's hard ``VIOLATED`` triggers.
4. Verifier predicate — if it returns ``True``, the loop terminates
   cleanly because the hook *agrees* the work is done.

Order matters: safeguards are evaluated in the order above. A buggy
predicate (safeguard 4) returning ``False`` forever cannot dominate the
other three because they run first.

The plugin is **opt-in by default** — Lyra's autonomy default is
"stop and ask" exactly like Claude Code. Auto-continue is a deliberate
user choice, installed and enabled explicitly.

Reference incident: ``thedotmack/claude-mem`` issue #1288 — a buggy
``{"continue": true}`` Stop hook without ``stop_hook_active`` parity
ran a tight infinite loop for 4.5 hours and burned ~$280. The
``stop_hook_active`` check on the first line of :meth:`on_stop` is the
canonical fix.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from lyra_core.agent.loop import ContinueLoop, StopCtx


__all__ = ["AutoContinuePlugin", "AutoContinueState"]


VerifierFn = Callable[[StopCtx], bool]
"""Returns True iff the work is genuinely done — the loop should terminate."""

CostFn = Callable[[], float]
"""Returns the session's cumulative cost in USD."""


@dataclass
class AutoContinueState:
    """Per-plugin telemetry — what the plugin observed and decided."""

    fires: int = 0
    re_feeds: int = 0
    last_decision: str = ""           # "allow" | "allow-cap" | "allow-watermark"
                                       # | "allow-verifier" | "deny"
    last_warnings: list[str] = field(default_factory=list)


@dataclass
class AutoContinuePlugin:
    """Stop-hook plugin that re-feeds the loop until done.

    Configure with::

        plugin = AutoContinuePlugin(
            max_extensions=3,
            cost_watermark_pct=0.90,
            session_budget_usd=5.00,
            cost_so_far_fn=lambda: session.cost_usd,
            verifier=lambda ctx: tests_pass(),
            user_message="Continue. Verify and propose the next step.",
        )
        loop = AgentLoop(..., plugins=[plugin])
    """

    max_extensions: int = 3
    cost_watermark_pct: float = 0.90
    session_budget_usd: Optional[float] = None
    cost_so_far_fn: Optional[CostFn] = None
    verifier: Optional[VerifierFn] = None
    user_message: str = (
        "Continue. Verify the previous step actually completed; if it did, "
        "propose the next step from the plan and execute it."
    )
    state: AutoContinueState = field(default_factory=AutoContinueState)

    def on_stop(self, ctx: StopCtx) -> None:
        """The four-safeguard Stop-hook decision tree."""
        self.state.fires += 1

        # Safeguard 1 — second-entry break.
        # Even with a buggy verifier, the loop terminates because the
        # *next* fire after a re-feed has stop_hook_active=True.
        if ctx.stop_hook_active:
            self.state.last_decision = "allow"
            return

        # Safeguard 2 — extension cap.
        if ctx.stop_extensions >= self.max_extensions:
            self.state.last_decision = "allow-cap"
            self.state.last_warnings.append(
                f"auto-continue cap reached (extensions={ctx.stop_extensions})"
            )
            return

        # Safeguard 3 — cost watermark.
        if (self.session_budget_usd is not None
                and self.cost_so_far_fn is not None):
            try:
                cost = float(self.cost_so_far_fn())
                ratio = cost / max(self.session_budget_usd, 1e-9)
            except Exception:
                ratio = 0.0
            if ratio >= self.cost_watermark_pct:
                self.state.last_decision = "allow-watermark"
                self.state.last_warnings.append(
                    f"cost watermark — auto-stopping at {ratio:.0%} of budget"
                )
                return

        # Safeguard 4 — verifier predicate.
        if self.verifier is not None:
            try:
                done = bool(self.verifier(ctx))
            except Exception:
                # A throwing verifier defaults to allow — never strand
                # the loop on a buggy callback. Reference: ``vercel-labs``
                # `verifyCompletion` exception handling.
                done = True
                self.state.last_warnings.append("verifier raised; defaulting to allow")
            if done:
                self.state.last_decision = "allow-verifier"
                return

        # All four safeguards say "keep going" → re-feed the loop.
        self.state.last_decision = "deny"
        self.state.re_feeds += 1
        raise ContinueLoop(
            user_message=self.user_message,
            reason="auto-continue: not yet done",
        )
