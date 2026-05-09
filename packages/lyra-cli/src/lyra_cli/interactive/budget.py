"""Budget enforcement for the REPL.

A tiny, pure dataclass + classifier that the agent loop and the
``/budget`` slash both consume. Keeping the helper *outside*
:mod:`lyra_cli.interactive.session` lets the Wave-D agent loop import
it without dragging the REPL machinery along.

Three statuses (matches claw-code's "ok / warn / kill" tri-state):

* ``OK`` — current spend below ``alert_pct`` of the cap.
* ``ALERT`` — at-or-above ``alert_pct`` but below 100%.
* ``EXCEEDED`` — at-or-above the cap. Caller should refuse new
  expensive work until the user explicitly raises the cap.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BudgetStatus(str, Enum):
    OK = "ok"
    ALERT = "alert"
    EXCEEDED = "exceeded"


@dataclass(frozen=True)
class BudgetCap:
    """Hard-cap configuration."""

    limit_usd: float
    alert_pct: float = 80.0  # percent of ``limit_usd`` to start warning at


@dataclass(frozen=True)
class BudgetReport:
    status: BudgetStatus
    current_usd: float
    limit_usd: float
    pct: float
    message: str


def enforce(cap: BudgetCap, *, current_usd: float) -> BudgetReport:
    """Classify *current_usd* against *cap* and return a friendly report.

    Pure function — does no I/O and never raises. Callers decide what
    to *do* with the result (block a tool call, render a chip,
    summarise in a status bar). The split keeps unit tests trivial and
    lets the agent loop short-circuit without importing render code.
    """
    limit = max(cap.limit_usd, 0.0)
    if limit <= 0.0:
        return BudgetReport(
            status=BudgetStatus.OK,
            current_usd=current_usd,
            limit_usd=0.0,
            pct=0.0,
            message="no budget cap set",
        )
    pct = (current_usd / limit) * 100.0
    if current_usd >= limit:
        return BudgetReport(
            status=BudgetStatus.EXCEEDED,
            current_usd=current_usd,
            limit_usd=limit,
            pct=pct,
            message=f"budget exceeded: ${current_usd:.2f} > ${limit:.2f}",
        )
    if pct >= cap.alert_pct:
        return BudgetReport(
            status=BudgetStatus.ALERT,
            current_usd=current_usd,
            limit_usd=limit,
            pct=pct,
            message=(
                f"approaching budget: ${current_usd:.2f} of ${limit:.2f} "
                f"({pct:.0f}% — alert at {cap.alert_pct:.0f}%)"
            ),
        )
    return BudgetReport(
        status=BudgetStatus.OK,
        current_usd=current_usd,
        limit_usd=limit,
        pct=pct,
        message=(
            f"on budget: ${current_usd:.2f} of ${limit:.2f} ({pct:.0f}%)"
        ),
    )


# ---------------------------------------------------------------------------
# Wave-D Task 13: live deduction.
#
# The classifier above is pure; the agent loop needs *somewhere* to
# accumulate dollars across LLM rounds. ``BudgetMeter`` is that
# somewhere — a thin wrapper that converts ``(model, prompt_tokens,
# completion_tokens)`` tuples into a running USD total against a
# :class:`BudgetCap`. The price table is intentionally hand-curated
# (USD per 1M tokens) and easy to override per-call.
# ---------------------------------------------------------------------------


# Per-million-token rates as of the v1.8 ship date. Where vendors
# publish "input/output" pairs we use those; for proxy models we
# pick the closest published rate. Unknown models fall back to the
# generous default at the bottom so the meter never silently
# under-counts a missing entry.
_DEFAULT_PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    # ---- OpenAI ------------------------------------------------------
    "gpt-4o": (5.00, 15.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-5": (10.00, 30.00),
    "gpt-5-mini": (3.00, 12.00),
    "o4-mini": (3.00, 12.00),
    "o3": (15.00, 60.00),
    "o3-mini": (3.00, 12.00),
    "o1": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    # ---- Anthropic ---------------------------------------------------
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-7-sonnet": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-opus-4-1": (15.00, 75.00),
    "claude-opus-4-5": (15.00, 75.00),
    # ---- DeepSeek ----------------------------------------------------
    # Public list price as of 2026-04. Coder models price the same as
    # the chat models on the V3 / V4 lines; the Reasoner tier is more
    # expensive but defaults to opt-in.
    "deepseek-chat": (0.27, 1.10),
    "deepseek-coder": (0.27, 1.10),
    "deepseek-v3": (0.27, 1.10),
    "deepseek-v4": (0.40, 1.60),
    "deepseek-v4-pro": (0.55, 2.19),
    "deepseek-reasoner": (0.55, 2.19),
    # ---- Qwen / Alibaba DashScope ------------------------------------
    "qwen-3-coder-plus": (0.50, 2.00),
    "qwen-3-coder": (0.50, 2.00),
    "qwen-3-max": (1.20, 4.80),
    "qwen-2.5-coder-32b": (0.30, 1.20),
    # v2.3.0 fill-in: chat-tier Qwen models hit by the public
    # OpenRouter / DashScope routes. Without these the audit found
    # ``qwen-plus`` / ``qwen-turbo`` cost-rolled at the unknown-model
    # fallback ($1 / $3 per Mtok), which materially over-billed cheap
    # Qwen calls and confused users staring at "$3 / 100k tokens" on
    # a model whose published rate is 1/15th of that.
    "qwen-plus": (0.40, 1.20),
    "qwen-turbo": (0.05, 0.20),
    "qwen-max": (1.60, 6.40),
    "qwen-vl-plus": (0.50, 1.50),
    # ---- Gemini ------------------------------------------------------
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-2.5-flash-lite": (0.04, 0.15),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.0-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
    # ---- xAI Grok ----------------------------------------------------
    # Public list price as of 2026-04 from x.ai/api. Grok-4 is
    # multi-modal flagship; mini variants drop both costs roughly 4×.
    "grok-4": (5.00, 15.00),
    "grok-4-mini": (1.00, 4.00),
    "grok-3": (3.00, 15.00),
    "grok-3-mini": (0.30, 1.50),
    "grok-2": (2.00, 10.00),
    "grok-2-mini": (0.50, 2.50),
    # ---- Mistral / Codestral -----------------------------------------
    "codestral-latest": (0.30, 0.90),
    "codestral-2405": (0.30, 0.90),
    "mistral-large-latest": (2.00, 6.00),
    "mistral-large": (2.00, 6.00),
    "mistral-medium-latest": (0.40, 2.00),
    "mistral-small-latest": (0.20, 0.60),
    "mistral-nemo": (0.15, 0.15),
    "open-mistral-nemo": (0.15, 0.15),
    "ministral-3b-latest": (0.04, 0.04),
    "ministral-8b-latest": (0.10, 0.10),
    # ---- Groq (Llama / Llama-3 / Mixtral hosted) --------------------
    # Groq prices "per Mtok" public rates — output is typically the
    # same as input for Llama; we copy that.
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.3-70b": (0.59, 0.79),
    "llama-3.1-405b-reasoning": (1.79, 1.79),
    "llama-3.1-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "llama-3-70b": (0.59, 0.79),
    "llama-3-8b": (0.05, 0.08),
    "mixtral-8x7b-32768": (0.24, 0.24),
    # ---- Cerebras (Llama hosted on Wafer-Scale) ----------------------
    "llama-3.3-70b-cerebras": (0.85, 1.20),
    "llama3.1-8b-cerebras": (0.10, 0.10),
    # ---- OpenRouter aggregator (per-model pricing flows through) -----
    # No fixed entry — :func:`price_for` already does substring lookup
    # for ``openrouter/<vendor>/<model>`` slugs, so e.g.
    # ``openrouter/anthropic/claude-3-5-sonnet`` resolves to the
    # Anthropic entry above without an explicit row here.
    # ---- Open-source / self-hosted -----------------------------------
    # Effectively free; users who want a non-zero local cost
    # (electricity, depreciation) can override via :func:`set_price`.
    "llama-3.1-8b-instruct": (0.0, 0.0),
    "llama-3.2-3b-instruct": (0.0, 0.0),
    "qwen-2.5-coder-7b": (0.0, 0.0),
    "qwen-2.5-coder-1.5b": (0.0, 0.0),
    "qwen2.5-coder:1.5b": (0.0, 0.0),
}


_FALLBACK_PRICE_PER_MTOK: tuple[float, float] = (1.0, 3.0)


def price_for(model: str) -> tuple[float, float]:
    """Return ``(prompt_per_mtok, completion_per_mtok)`` for ``model``.

    Lookup is case-insensitive and substring-aware so canonical
    entries like ``"gpt-4o-mini"`` cover provider-prefixed variants
    like ``"openai/gpt-4o-mini"`` or version-suffixed
    ``"gpt-4o-mini-2024-07-18"`` without exploding the table.
    Unknown models fall back to :data:`_FALLBACK_PRICE_PER_MTOK`.
    """
    key = (model or "").lower()
    if not key:
        return _FALLBACK_PRICE_PER_MTOK
    if key in _DEFAULT_PRICES_PER_MTOK:
        return _DEFAULT_PRICES_PER_MTOK[key]
    for canon, rate in _DEFAULT_PRICES_PER_MTOK.items():
        if canon in key:
            return rate
    return _FALLBACK_PRICE_PER_MTOK


@dataclass
class BudgetMeter:
    """Live spend ledger that wraps a :class:`BudgetCap`.

    Stateful by design — the agent loop holds one per session and
    bumps it after every LLM round. The meter is *not* threadsafe;
    parallel subagents each carry their own meter and roll up to the
    parent at join time (Wave-E).
    """

    cap: BudgetCap | None = None
    _current_usd: float = 0.0
    _prices: dict[str, tuple[float, float]] = field(default_factory=dict)

    # ---- read --------------------------------------------------------

    @property
    def current_usd(self) -> float:
        return self._current_usd

    def report(self) -> BudgetReport:
        """Classify the running spend (no-cap → always OK)."""
        if self.cap is None:
            return BudgetReport(
                status=BudgetStatus.OK,
                current_usd=self._current_usd,
                limit_usd=0.0,
                pct=0.0,
                message="no budget cap set",
            )
        return enforce(self.cap, current_usd=self._current_usd)

    def gate(self) -> BudgetReport:
        """Convenience for the loop: same as :meth:`report`.

        The split exists so the agent loop reads as
        ``decision = meter.gate(); if decision.status is EXCEEDED: …``
        — communicating that the call is a *check*, not just a snapshot.
        """
        return self.report()

    # ---- write -------------------------------------------------------

    def set_price(
        self,
        model: str,
        *,
        prompt_per_mtok: float,
        completion_per_mtok: float,
    ) -> None:
        """Override the price table for ``model`` (e.g., self-hosted)."""
        self._prices[model.lower()] = (prompt_per_mtok, completion_per_mtok)

    def record_usage(
        self,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Convert token counts to dollars and add to ``current_usd``.

        Returns the *delta* that was added so the caller can include
        it in a per-turn telemetry event.
        """
        prompt_per, completion_per = self._prices.get(
            model.lower(), price_for(model)
        )
        delta = (
            (max(prompt_tokens, 0) / 1_000_000) * prompt_per
            + (max(completion_tokens, 0) / 1_000_000) * completion_per
        )
        if delta < 0:
            delta = 0.0
        self._current_usd += delta
        return delta

    def reset(self) -> None:
        self._current_usd = 0.0


__all__ = [
    "BudgetCap",
    "BudgetMeter",
    "BudgetReport",
    "BudgetStatus",
    "enforce",
    "price_for",
]
