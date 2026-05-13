"""Per-session token and cost accumulator.

Reads usage data from hook event payloads (PostToolUse carries token counts
in Claude Code hooks) and from session JSONL files as fallback.
"""
from __future__ import annotations

import json

from .event_store import EventStore
from .models import SessionCost


# Claude pricing (USD per 1M tokens) — May 2026 snapshot
_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-7":    {"in": 15.0, "out": 75.0, "cache_read": 1.5,  "cache_write": 18.75},
    "claude-sonnet-4-6":  {"in": 3.0,  "out": 15.0, "cache_read": 0.3,  "cache_write": 3.75},
    "claude-haiku-4-5":   {"in": 0.8,  "out": 4.0,  "cache_read": 0.08, "cache_write": 1.0},
}
_DEFAULT_PRICE = {"in": 3.0, "out": 15.0, "cache_read": 0.3, "cache_write": 3.75}


def _cost_usd(
    tokens_in: int,
    tokens_out: int,
    cache_read: int,
    cache_write: int,
    model: str,
) -> float:
    price = _PRICING.get(model, _DEFAULT_PRICE)
    return (
        tokens_in * price["in"]
        + tokens_out * price["out"]
        + cache_read * price["cache_read"]
        + cache_write * price["cache_write"]
    ) / 1_000_000


class CostAccumulator:
    """Compute per-session token/cost totals from EventStore."""

    def __init__(self, store: EventStore) -> None:
        self._store = store

    def get(self, session_id: str, model: str = "claude-sonnet-4-6") -> SessionCost:
        events = self._store.tail(500, session_id=session_id)
        tokens_in = 0
        tokens_out = 0
        cache_read = 0
        cache_write = 0
        for ev in events:
            if ev.hook_type not in ("PostToolUse", "TurnFinished", "SessionEnd"):
                continue
            try:
                payload = json.loads(ev.payload_json)
                usage = payload.get("usage") or {}
                tokens_in += int(usage.get("input_tokens", 0))
                tokens_out += int(usage.get("output_tokens", 0))
                cache_read += int(usage.get("cache_read_input_tokens", 0))
                cache_write += int(usage.get("cache_creation_input_tokens", 0))
            except Exception:
                continue
        cost = _cost_usd(tokens_in, tokens_out, cache_read, cache_write, model)
        return SessionCost(
            session_id=session_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tokens_cache_read=cache_read,
            tokens_cache_write=cache_write,
            cost_usd=cost,
        )

    def get_total(self, model: str = "claude-sonnet-4-6") -> SessionCost:
        sessions = self._store.active_sessions()
        totals = SessionCost("__total__", 0, 0, 0, 0, 0.0)
        for sid in sessions:
            sc = self.get(sid, model)
            totals = SessionCost(
                session_id="__total__",
                tokens_in=totals.tokens_in + sc.tokens_in,
                tokens_out=totals.tokens_out + sc.tokens_out,
                tokens_cache_read=totals.tokens_cache_read + sc.tokens_cache_read,
                tokens_cache_write=totals.tokens_cache_write + sc.tokens_cache_write,
                cost_usd=totals.cost_usd + sc.cost_usd,
            )
        return totals
