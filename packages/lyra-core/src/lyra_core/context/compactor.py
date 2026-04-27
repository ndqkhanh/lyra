"""Context compaction — two surfaces.

1. :func:`compact` (v1) — item-level compaction for the 5-layer
   context pipeline. Collapses a run of DYNAMIC items into a single
   COMPACTED item. Preserves any item with ``pin=True`` verbatim.

2. :func:`compact_messages` (v1.7.3) — transcript-level compaction
   backed by an LLM summariser. Keeps the last ``keep_last`` turns
   raw and summarises everything before into a single system-role
   message. Returns a :class:`CompactResult` carrying BOTH the kept-
   raw turns AND the summary so the caller can archive the dropped
   raw turns side-channel (this is what enables a future
   ``/uncompact`` rollback). SOUL / system-role messages at the head
   of the transcript ride through verbatim and do not count against
   ``keep_last``.

Both live here because they share the ``_tok_estimate`` heuristic and
the same conceptual goal (reduce token spend without losing safety-
critical anchors).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .pipeline import ContextItem, ContextLayer, _tok_estimate


def _summarise(items: list[ContextItem]) -> str:
    preview = " | ".join(
        (it.content[:40] + "…") if len(it.content) > 40 else it.content
        for it in items[:10]
    )
    return f"<compacted: {len(items)} items> {preview}"


def compact(
    items: list[ContextItem], *, target_tokens: int
) -> list[ContextItem]:
    """Return a compacted list whose total token estimate is < original and
    ideally <= ``target_tokens``. Pinned items survive verbatim.
    """
    if not items:
        return []
    pinned = [it for it in items if it.pin]
    dynamic = [it for it in items if not it.pin]
    pinned_tokens = sum(it.estimated_tokens() for it in pinned)

    summary_text = _summarise(dynamic) if dynamic else ""
    summary_tokens = _tok_estimate(summary_text) if summary_text else 0

    out: list[ContextItem] = []
    if dynamic:
        out.append(
            ContextItem(
                layer=ContextLayer.COMPACTED,
                content=summary_text,
                pin=False,
            )
        )
    # Pinned items keep their original content but land in COMPACTED layer
    # so callers can treat them uniformly. Pin flag preserved.
    for p in pinned:
        out.append(
            ContextItem(
                layer=ContextLayer.COMPACTED,
                content=p.content,
                pin=True,
            )
        )

    # Safety: force at least one token reduction vs original total.
    original_total = sum(it.estimated_tokens() for it in items)
    new_total = sum(it.estimated_tokens() for it in out)
    if new_total >= original_total and dynamic:
        # Reduce the summary aggressively.
        out[0] = ContextItem(
            layer=ContextLayer.COMPACTED,
            content=f"<compacted: {len(dynamic)} items>",
        )
    # target_tokens is advisory; we emit what we can.
    _ = target_tokens, pinned_tokens, summary_tokens
    return out


# --------------------------------------------------------------------- #
# v1.7.3 — transcript-level compaction via injected LLM                 #
# --------------------------------------------------------------------- #


_SUMMARY_MARKER = "[compacted"
_DEFAULT_SYSTEM_PROMPT = (
    "You are a conversation compaction assistant. Produce a concise, "
    "faithful summary of the conversation block below. Preserve user "
    "intent, decisions made, open questions, and any tool-call outcomes "
    "that later turns may need. Target at most {max_summary_tokens} "
    "tokens."
)


@dataclass
class CompactResult:
    """Outcome of a :func:`compact_messages` call.

    Attributes:
        kept_raw: The last ``keep_last`` non-system messages, verbatim.
        summary: The LLM-produced summary text (empty string when the
            transcript was too short to compact — caller can branch on
            ``dropped_count == 0``).
        dropped_count: Number of non-system messages folded into the
            summary (``0`` when no compaction occurred).
        summary_tokens: ``_tok_estimate`` of ``summary``; ``0`` when
            ``summary`` is empty.
        summarised_messages: The compacted transcript ready to drop
            into live context — ``[*system_head, summary_message,
            *kept_raw]`` when compaction happened, otherwise the
            original ``messages`` list.
    """

    kept_raw: list[dict] = field(default_factory=list)
    summary: str = ""
    dropped_count: int = 0
    summary_tokens: int = 0
    summarised_messages: list[dict] = field(default_factory=list)


def _split_system_head(messages: list[dict]) -> tuple[list[dict], list[dict]]:
    """Peel leading ``role=system`` messages off the front.

    SOUL / system instructions at the head are always preserved
    verbatim — they are the persona/contract of the conversation and
    must never be summarised.
    """
    head: list[dict] = []
    idx = 0
    while idx < len(messages) and messages[idx].get("role") == "system":
        head.append(messages[idx])
        idx += 1
    return head, messages[idx:]


def compact_messages(
    messages: list[dict],
    *,
    llm: Callable[..., Any],
    keep_last: int = 4,
    max_summary_tokens: int = 800,
) -> CompactResult:
    """Compact a conversation transcript via an LLM summariser.

    Args:
        messages: Ordered list of ``{"role": str, "content": str, ...}``
            message dicts. The first run of ``role=="system"`` messages
            is treated as the SOUL/static header and preserved verbatim.
        llm: Callable matching ``AgentLoop._invoke_llm`` — either a
            bare callable ``(**kwargs) -> Mapping`` or an object with a
            ``generate`` method. Must return a mapping with at least a
            ``content`` key.
        keep_last: Number of trailing non-system messages to keep raw.
            Must be strictly positive.
        max_summary_tokens: Advisory ceiling the summariser surfaces to
            the LLM. Also appears in the system prompt so the LLM can
            size its output.

    Returns:
        A :class:`CompactResult`. When the compactable tail is no
        longer than ``keep_last`` the LLM is NOT invoked and the
        transcript is returned unchanged (``dropped_count == 0``).

    Raises:
        ValueError: when ``keep_last <= 0``.
    """
    if keep_last <= 0:
        raise ValueError("keep_last must be > 0")

    system_head, body = _split_system_head(messages)

    if len(body) <= keep_last:
        # Nothing to compact — short-circuit without calling the LLM.
        return CompactResult(
            kept_raw=list(body[-keep_last:]) if body else [],
            summary="",
            dropped_count=0,
            summary_tokens=0,
            summarised_messages=list(messages),
        )

    head_block = body[:-keep_last]
    tail_block = body[-keep_last:]

    system_prompt = {
        "role": "system",
        "content": _DEFAULT_SYSTEM_PROMPT.format(
            max_summary_tokens=max_summary_tokens
        ),
    }
    llm_input = [system_prompt, *head_block]

    generate = getattr(llm, "generate", None)
    if generate is None and callable(llm):
        generate = llm
    if generate is None:
        raise RuntimeError(
            "compact_messages.llm must expose .generate(...) or be callable"
        )
    response = generate(messages=llm_input, max_summary_tokens=max_summary_tokens)

    content = ""
    if isinstance(response, dict):
        content = str(response.get("content", "") or "")
    elif isinstance(response, str):
        content = response

    if not content:
        content = f"{_SUMMARY_MARKER}: {len(head_block)} messages condensed>"

    labelled = f"{_SUMMARY_MARKER}: {len(head_block)} messages condensed]\n{content}"

    summary_message = {"role": "system", "content": labelled}
    out_messages: list[dict] = [*system_head, summary_message, *tail_block]

    return CompactResult(
        kept_raw=list(tail_block),
        summary=labelled,
        dropped_count=len(head_block),
        summary_tokens=_tok_estimate(labelled),
        summarised_messages=out_messages,
    )
