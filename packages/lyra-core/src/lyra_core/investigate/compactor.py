"""Message compaction for investigate mode — the level0..4 thermostat made live.

:func:`compact_messages` reads a :class:`ContextLevelPlan` and rewrites
a message list before each LLM call. The four strategies named in the
plan map onto concrete passes here:

* ``truncate_oldest_tool_outputs`` — keep only the N most recent
  ``role=="tool"`` messages.
* ``relevance_filter_tool_outputs`` — drop tool outputs whose body
  shares no token with the most recent user / assistant message.
* ``ngc_running_summary`` — replace dropped middle-of-conversation
  tool outputs with one synthetic ``"[N tool outputs elided]"``
  marker, so the LLM still knows work happened.
* ``per_window_summary`` — every ``window`` turns, hand the elided
  block to an optional ``summarizer`` callable that returns a short
  text digest; when no summarizer is provided, the marker stands in.

System messages and the most recent user message are always
preserved. The function is pure (no I/O, no LLM); the summarizer is
the only injected side effect, and it is optional.

Cite: arXiv:2605.05242 §4.5 (RQ5 — context management); DCI-Agent-Lite
README "Context Management Levels".
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from .levels import ContextLevelPlan


@dataclass(frozen=True)
class CompactionReport:
    """Telemetry from one compaction pass.

    The runner attaches this to its trajectory ledger so the eval
    harness can reproduce RQ5 ablations on Lyra's own benchmarks.
    """

    messages_before: int
    messages_after: int
    bytes_before: int
    bytes_after: int
    tool_outputs_dropped: int
    summary_injected: bool


Summarizer = Callable[[list[dict]], str]


def compact_messages(
    messages: list[dict],
    plan: ContextLevelPlan,
    *,
    max_tool_outputs_kept: int = 6,
    summarizer: Summarizer | None = None,
) -> tuple[list[dict], CompactionReport]:
    """Return ``(compacted, report)`` for *messages* under *plan*.

    The input is not mutated; ``compacted`` is a new list.
    """
    bytes_before = _byte_size(messages)
    before_count = len(messages)

    if plan.is_no_op:
        return list(messages), CompactionReport(
            messages_before=before_count,
            messages_after=before_count,
            bytes_before=bytes_before,
            bytes_after=bytes_before,
            tool_outputs_dropped=0,
            summary_injected=False,
        )

    kept: list[dict] = []
    dropped_tool_outputs: list[dict] = []

    # Walk from newest to oldest so we keep the *recent* tool outputs.
    rev: list[dict] = []
    seen_tool_outputs = 0
    keyword_set = _query_keywords(messages)

    for msg in reversed(messages):
        if msg.get("role") != "tool":
            rev.append(msg)
            continue

        # Decision pipeline for one tool output.
        if plan.relevance_filter_tool_outputs and not _is_relevant(msg, keyword_set):
            dropped_tool_outputs.append(msg)
            continue

        seen_tool_outputs += 1
        if (
            plan.truncate_oldest_tool_outputs
            and seen_tool_outputs > max_tool_outputs_kept
        ):
            dropped_tool_outputs.append(msg)
            continue

        rev.append(msg)

    kept = list(reversed(rev))

    summary_injected = False
    if dropped_tool_outputs and (plan.ngc_running_summary or plan.per_window_summary):
        marker = _build_summary_marker(
            dropped_tool_outputs,
            use_summarizer=plan.per_window_summary,
            summarizer=summarizer,
        )
        # Insert summary right after the first system / user message
        # so the LLM sees it as "early context", before recent turns.
        insert_at = _first_non_setup_index(kept)
        kept.insert(insert_at, {"role": "system", "content": marker})
        summary_injected = True

    return kept, CompactionReport(
        messages_before=before_count,
        messages_after=len(kept),
        bytes_before=bytes_before,
        bytes_after=_byte_size(kept),
        tool_outputs_dropped=len(dropped_tool_outputs),
        summary_injected=summary_injected,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _byte_size(messages: list[dict]) -> int:
    total = 0
    for msg in messages:
        c = msg.get("content")
        if isinstance(c, str):
            total += len(c.encode("utf-8"))
        elif isinstance(c, (bytes, bytearray)):
            total += len(c)
        elif c is not None:
            total += len(str(c).encode("utf-8"))
    return total


def _query_keywords(messages: list[dict]) -> frozenset[str]:
    """Token-bag of the most recent user message — used for relevance."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return frozenset(_tokenize(str(msg.get("content", ""))))
    return frozenset()


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^A-Za-z0-9_]+", text.lower()) if len(t) >= 3]


def _is_relevant(tool_msg: dict, keywords: frozenset[str]) -> bool:
    """A tool output is relevant iff it shares any keyword with the query.

    Empty-keyword queries pass everything through (no filter signal).
    """
    if not keywords:
        return True
    body = str(tool_msg.get("content", ""))
    body_tokens = frozenset(_tokenize(body))
    return bool(body_tokens & keywords)


def _build_summary_marker(
    dropped: list[dict], *, use_summarizer: bool, summarizer: Summarizer | None,
) -> str:
    """Build the synthetic system message that stands in for elided turns."""
    if use_summarizer and summarizer is not None:
        try:
            return f"[compacted {len(dropped)} tool outputs] {summarizer(dropped)}"
        except Exception as exc:  # summarizer failure must not kill the loop
            return f"[compacted {len(dropped)} tool outputs; summarizer failed: {exc}]"
    return f"[compacted {len(dropped)} tool outputs from earlier turns]"


def _first_non_setup_index(messages: list[dict]) -> int:
    """First index after the leading system/user setup turn."""
    for i, msg in enumerate(messages):
        if msg.get("role") not in ("system", "user"):
            return i
    return len(messages)


__all__ = [
    "CompactionReport",
    "Summarizer",
    "compact_messages",
]
