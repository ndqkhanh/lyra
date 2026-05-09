"""Token-budget grid renderer for ``/context`` (v1.7.3).

Turns a conversation transcript into a monospaced proportional bar
chart so the user can see — at a glance — which role is eating their
context window.

The renderer is intentionally ANSI-free; the CLI layer may wrap the
output in a Rich ``Panel`` for colour, but the core produces log-safe
text that can be asserted on, stored in transcripts, or piped to a
dumb terminal.
"""
from __future__ import annotations

from typing import Iterable

from .pipeline import _tok_estimate

_GLYPHS: dict[str, str] = {
    "system": "█",
    "user": "▓",
    "assistant": "▒",
    "tool": "░",
}
_UNKNOWN_GLYPH = "·"
_ROLE_ORDER: tuple[str, ...] = ("system", "user", "assistant", "tool")


def _bucket_tokens(messages: Iterable[dict]) -> dict[str, int]:
    buckets: dict[str, int] = {}
    for msg in messages:
        role = str(msg.get("role") or "unknown")
        toks = _tok_estimate(str(msg.get("content") or ""))
        buckets[role] = buckets.get(role, 0) + toks
    return buckets


def render_context_grid(
    messages: list[dict], *, columns: int = 60
) -> str:
    """Render a proportional monospaced token-usage grid.

    Args:
        messages: Ordered transcript. Each entry is ``{"role": str,
            "content": str, ...}``. Tokens are estimated via
            :func:`lyra_core.context.pipeline._tok_estimate`.
        columns: Total output width in monospace cells. Must be > 0.
            All emitted lines are guaranteed <= this width.

    Returns:
        A multi-line string with a per-role row (``row = "<role>  <bar>
        <tok>"``), a legend, and a totals summary. ANSI-free.

    Raises:
        ValueError: when ``columns`` is not positive.
    """
    if columns <= 0:
        raise ValueError(f"columns must be positive, got {columns}")

    buckets = _bucket_tokens(messages)
    total = sum(buckets.values())

    # Reserve space for: "<role:10s> " + "  <tokens>" suffix (up to ~12
    # chars). The bar gets whatever's left, bounded by ``columns``.
    label_width = 10
    suffix_width = 12
    bar_width = max(1, columns - label_width - suffix_width - 2)

    def _row(role: str, toks: int) -> str:
        glyph = _GLYPHS.get(role, _UNKNOWN_GLYPH)
        fill = 0 if total == 0 else max(1 if toks else 0, toks * bar_width // max(total, 1))
        fill = min(fill, bar_width)
        bar = glyph * fill + " " * (bar_width - fill)
        line = f"{role[:label_width]:<{label_width}} {bar} {toks:>6d} tok"
        return line[:columns]

    lines: list[str] = []

    # Stable role order; append any unknown roles we encountered so
    # data-dependent rows never vanish silently.
    seen_roles = list(_ROLE_ORDER) + [
        r for r in buckets if r not in _ROLE_ORDER
    ]
    for role in seen_roles:
        toks = buckets.get(role, 0)
        if role in _ROLE_ORDER or toks > 0:
            lines.append(_row(role, toks))

    # Totals line.
    total_line = f"total: {total} tokens"
    lines.append(total_line[:columns])

    # Legend.
    legend = "legend: " + "  ".join(
        f"{_GLYPHS.get(r, _UNKNOWN_GLYPH)}={r}" for r in _ROLE_ORDER
    )
    lines.append(legend[:columns])

    return "\n".join(lines)
