"""Relevance-scored active compaction (Phase CE.2, P1-1).

Vanilla compaction keeps the last K turns and summarises everything
older. That's safe but loses signal — an older turn that pinned down a
critical file anchor or a deny reason gets bulldozed.

This module adds a deterministic, dependency-free relevance score per
message and a wrapper around :func:`compact_messages` that keeps any
older turn whose score clears a threshold.

Signals (all char-cheap):

* **file_overlap**       — message references a file path that appears
                           in the current task description.
* **signal_keywords**    — failure / blocker / must-do words.
* **citation_inbound**   — a later turn mentioned this message's
                           span id.
* **invariant_density**  — count of file:line anchors, test names,
                           and deny reasons (reuses the regexes from
                           :mod:`.compact_validate`).

Weights are exposed as :class:`RelevanceWeights` so callers can
override per-task. The defaults are tuned so a score >= 0.5 means
"keep this through compaction".
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable

from .clear import _is_tool_message, _span_id
from .compact_validate import (
    _DENY_RE,
    _FILE_ANCHOR_RE,
    _TEST_NAME_RE,
    _msg_text,
)
from .compactor import CompactResult, compact_messages

# Words that historically correlate with "you don't want to forget this".
SIGNAL_KEYWORDS = (
    "fail", "failed", "error", "deny", "denied", "blocker",
    "must", "regression", "TODO", "FIXME", "BUG",
)


@dataclass(frozen=True)
class RelevanceWeights:
    """Per-signal weights. Each is a flat 0..1 contribution to the
    aggregate score, clamped to [0, 1] at the end."""

    file_overlap: float = 0.35
    signal_keywords: float = 0.20
    citation_inbound: float = 0.20
    invariant_density: float = 0.25


DEFAULT_WEIGHTS = RelevanceWeights()


_PATH_LIKE_RE = re.compile(r"[\w./\-]+\.[A-Za-z]{1,5}\b")


def _paths_in(text: str) -> set[str]:
    return {m.group(0) for m in _PATH_LIKE_RE.finditer(text)}


def _signal_keyword_hits(text: str) -> int:
    lowered = text.lower()
    return sum(1 for kw in SIGNAL_KEYWORDS if kw.lower() in lowered)


def _invariant_count(text: str) -> int:
    return (
        sum(1 for _ in _FILE_ANCHOR_RE.finditer(text))
        + sum(1 for _ in _TEST_NAME_RE.finditer(text))
        + sum(1 for _ in _DENY_RE.finditer(text))
    )


@dataclass(frozen=True)
class RelevanceBreakdown:
    """How a message earned its score — for explainability and tests."""

    score: float
    file_overlap: float
    signal_keywords: float
    citation_inbound: float
    invariant_density: float


def score_message(
    message: dict,
    *,
    task: str,
    later_messages: Iterable[dict] = (),
    weights: RelevanceWeights = DEFAULT_WEIGHTS,
) -> RelevanceBreakdown:
    """Return a 0..1 relevance score for ``message`` against ``task``.

    ``later_messages`` is used for the citation-inbound signal — pass
    the messages that come after this one so we can detect references.
    """
    text = _msg_text(message)
    if not text:
        return RelevanceBreakdown(0.0, 0.0, 0.0, 0.0, 0.0)

    task_paths = _paths_in(task)
    msg_paths = _paths_in(text)
    file_overlap = 1.0 if (task_paths & msg_paths) else 0.0

    kw_hits = _signal_keyword_hits(text)
    keyword_signal = min(1.0, kw_hits / 3.0)  # saturates at 3 hits

    sid = _span_id(message)
    if sid:
        cited = any(
            sid in _msg_text(later) and not _is_tool_message(later)
            for later in later_messages
        )
        citation_signal = 1.0 if cited else 0.0
    else:
        citation_signal = 0.0

    invariants = _invariant_count(text)
    invariant_signal = min(1.0, invariants / 4.0)  # saturates at 4 anchors

    aggregate = (
        weights.file_overlap * file_overlap
        + weights.signal_keywords * keyword_signal
        + weights.citation_inbound * citation_signal
        + weights.invariant_density * invariant_signal
    )
    return RelevanceBreakdown(
        score=min(1.0, max(0.0, aggregate)),
        file_overlap=weights.file_overlap * file_overlap,
        signal_keywords=weights.signal_keywords * keyword_signal,
        citation_inbound=weights.citation_inbound * citation_signal,
        invariant_density=weights.invariant_density * invariant_signal,
    )


# ────────────────────────────────────────────────────────────────
# Relevance-aware compaction
# ────────────────────────────────────────────────────────────────


@dataclass
class RelevanceCompactResult:
    """Wraps :class:`CompactResult` with the rescued-turn audit trail."""

    result: CompactResult
    rescued_indices: tuple[int, ...] = ()
    scores: tuple[RelevanceBreakdown, ...] = ()


def _system_head_len(messages: list[dict]) -> int:
    n = 0
    while n < len(messages) and messages[n].get("role") == "system":
        n += 1
    return n


def compact_messages_relevance(
    messages: list[dict],
    *,
    llm: Callable[..., Any],
    task: str,
    keep_last: int = 4,
    max_summary_tokens: int = 800,
    threshold: float = 0.5,
    weights: RelevanceWeights = DEFAULT_WEIGHTS,
) -> RelevanceCompactResult:
    """Compact, but rescue any older non-system message scoring ``>=
    threshold``.

    Algorithm:
      1. Split out the system head (never touched).
      2. Score every body message against ``task`` using ``later_messages``
         set to the messages that follow it.
      3. Identify the *compact window* — body messages before the
         keep-last tail.
      4. Within the compact window, peel rescued messages back out so
         they ride the post-compaction transcript verbatim.
      5. Run :func:`compact_messages` on the survivors only.
      6. Splice the rescued messages back at their original positions
         in front of the kept-raw tail.
    """
    head_len = _system_head_len(messages)
    head, body = messages[:head_len], messages[head_len:]

    # Score every body message; later_messages excludes the scored msg.
    scores: list[RelevanceBreakdown] = []
    for i, msg in enumerate(body):
        scores.append(
            score_message(
                msg,
                task=task,
                later_messages=body[i + 1 :],
                weights=weights,
            )
        )

    if len(body) <= keep_last:
        # Nothing to compact — short-circuit, score is still emitted.
        result = compact_messages(
            messages,
            llm=llm,
            keep_last=keep_last,
            max_summary_tokens=max_summary_tokens,
        )
        return RelevanceCompactResult(
            result=result,
            rescued_indices=(),
            scores=tuple(scores),
        )

    compact_window_end = len(body) - keep_last
    rescued_local: list[int] = [
        i for i in range(compact_window_end) if scores[i].score >= threshold
    ]
    rescued_msgs = [body[i] for i in rescued_local]

    # Drop rescued messages from the input the LLM sees so they aren't
    # summarised. We splice them back in afterwards.
    drop_set = set(rescued_local)
    pruned_body = [m for i, m in enumerate(body) if i not in drop_set]
    pruned = list(head) + pruned_body

    result = compact_messages(
        pruned,
        llm=llm,
        keep_last=keep_last,
        max_summary_tokens=max_summary_tokens,
    )

    # If compaction actually happened, surface the rescued messages
    # between the summary system-message and the kept-raw tail.
    if result.dropped_count > 0 and rescued_msgs:
        new_messages = list(result.summarised_messages)
        # The kept-raw tail sits at the end; rescued messages slot in
        # right before it so their original ordering is preserved.
        kept_count = len(result.kept_raw)
        insert_at = len(new_messages) - kept_count
        spliced = new_messages[:insert_at] + rescued_msgs + new_messages[insert_at:]
        result = CompactResult(
            kept_raw=result.kept_raw,
            summary=result.summary,
            dropped_count=result.dropped_count,
            summary_tokens=result.summary_tokens,
            summarised_messages=spliced,
        )

    # Translate rescued indices from body-local back to messages-global.
    rescued_global = tuple(head_len + i for i in rescued_local)
    return RelevanceCompactResult(
        result=result,
        rescued_indices=rescued_global,
        scores=tuple(scores),
    )


# ────────────────────────────────────────────────────────────────
# Compact(now=True) tool — agent-initiated boundary compaction
# ────────────────────────────────────────────────────────────────


COMPACT_TOOL_NAME = "Compact"
COMPACT_TOOL_DESCRIPTION = (
    "Trigger compaction now, at a logical task boundary. Pass the "
    "current task description so older turns can be scored for "
    "relevance and high-signal turns rescued verbatim. Use this when "
    "you have just completed a sub-task and want to free context for "
    "the next one."
)


@dataclass
class CompactToolResult:
    ok: bool
    dropped_count: int = 0
    rescued_count: int = 0
    summary_tokens: int = 0
    error: str = ""


def agent_compact_now(
    messages: list[dict],
    *,
    llm: Callable[..., Any],
    task: str,
    keep_last: int = 4,
    threshold: float = 0.5,
) -> tuple[list[dict], CompactToolResult]:
    """Adapter for the ``Compact(now=True)`` tool.

    Returns ``(new_messages, status)``. The caller overwrites its
    transcript with ``new_messages`` and may surface ``status`` to the
    operator (or feed it back to the model as the tool result).
    """
    try:
        out = compact_messages_relevance(
            messages,
            llm=llm,
            task=task,
            keep_last=keep_last,
            threshold=threshold,
        )
    except Exception as exc:  # surface, don't swallow
        return messages, CompactToolResult(ok=False, error=str(exc))

    status = CompactToolResult(
        ok=True,
        dropped_count=out.result.dropped_count,
        rescued_count=len(out.rescued_indices),
        summary_tokens=out.result.summary_tokens,
    )
    return out.result.summarised_messages, status


__all__ = [
    "COMPACT_TOOL_DESCRIPTION",
    "COMPACT_TOOL_NAME",
    "CompactToolResult",
    "DEFAULT_WEIGHTS",
    "RelevanceBreakdown",
    "RelevanceCompactResult",
    "RelevanceWeights",
    "SIGNAL_KEYWORDS",
    "agent_compact_now",
    "compact_messages_relevance",
    "score_message",
]
