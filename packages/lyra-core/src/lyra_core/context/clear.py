"""Tool-result clearing (Phase CE.1, P0-2).

Reduction shrinks a tool result at *write* time; clearing replaces it
at *read* time once the agent has extracted everything it needs.

Two surfaces:

* :func:`clear_tool_result` — replace a single matching message with a
  short stub that still points back to the artifact store.
* :func:`clear_stale_tool_results` — bulk-clear any tool result older
  than ``older_than`` turns whose span id isn't in ``cited_span_ids``,
  used by compaction.

The functions are *pure*: they return new lists and never mutate the
caller's transcript.

The "span id" can come from any of three places — :data:`SPAN_ID_KEYS`
lists them in priority order. Anthropic and OpenAI both expose
``tool_call_id`` on tool responses; lyra additionally tags messages
with ``id`` when emitting via the agent loop.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Callable

SPAN_ID_KEYS = ("id", "tool_call_id", "span_id")
TOOL_ROLES = frozenset({"tool", "function", "tool_result"})


def _span_id(msg: dict) -> str | None:
    """First non-empty span-id-shaped key, or None."""
    for key in SPAN_ID_KEYS:
        val = msg.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def _is_tool_message(msg: dict) -> bool:
    return msg.get("role") in TOOL_ROLES


def _stub_content(msg: dict, *, reason: str) -> str:
    """Single-line replacement that preserves the artifact pointer."""
    sid = _span_id(msg) or "?"
    tool = msg.get("name") or msg.get("tool_name") or "tool"
    return f"[cleared: {tool} @ {sid}; {reason}; view artifact to restore]"


def clear_tool_result(
    messages: list[dict], span_id: str, *, reason: str = "no longer needed"
) -> tuple[list[dict], bool]:
    """Replace the tool message whose span id matches with a stub.

    Returns a tuple of (new_messages, cleared). ``cleared`` is False
    when no matching message was found *or* when the matching message
    was already cleared (idempotent).

    Non-tool messages with matching ids are left alone — clearing
    a user turn would corrupt the conversation.
    """
    out: list[dict] = []
    cleared = False
    for msg in messages:
        if (
            not cleared
            and _is_tool_message(msg)
            and _span_id(msg) == span_id
            and not _looks_already_cleared(msg)
        ):
            out.append({**msg, "content": _stub_content(msg, reason=reason)})
            cleared = True
        else:
            out.append(msg)
    return out, cleared


def _looks_already_cleared(msg: dict) -> bool:
    content = msg.get("content")
    return isinstance(content, str) and content.startswith("[cleared:")


def clear_stale_tool_results(
    messages: list[dict],
    *,
    cited_span_ids: Iterable[str] = (),
    older_than: int = 8,
    match: Callable[[dict], bool] | None = None,
) -> tuple[list[dict], list[str]]:
    """Clear tool results past ``older_than`` turns unless cited.

    "Older than" is measured in tool-message position from the tail —
    the most recent ``older_than`` tool messages survive regardless of
    citation status.

    Args:
        messages: Transcript.
        cited_span_ids: Span ids that *later* turns referenced — these
            are kept verbatim even if old.
        older_than: How many recent tool messages to leave alone.
        match: Optional custom predicate; when supplied, must return
            True for a message to be considered for clearing. The
            ``older_than`` and ``cited_span_ids`` rules still apply.

    Returns:
        Tuple of (new_messages, cleared_span_ids).
    """
    if older_than < 0:
        raise ValueError(f"older_than must be >= 0, got {older_than}")
    cited = set(cited_span_ids)
    tool_indexes = [
        i for i, m in enumerate(messages)
        if _is_tool_message(m) and not _looks_already_cleared(m)
    ]
    # Indexes of tool messages we will *not* touch (the freshest ones).
    fresh: set[int] = set(tool_indexes[-older_than:]) if older_than else set()

    cleared_ids: list[str] = []
    out: list[dict] = []
    for i, msg in enumerate(messages):
        if (
            i in tool_indexes
            and i not in fresh
            and (match is None or match(msg))
        ):
            sid = _span_id(msg)
            if sid is None or sid in cited:
                out.append(msg)
                continue
            out.append({**msg, "content": _stub_content(msg, reason="stale")})
            cleared_ids.append(sid)
        else:
            out.append(msg)
    return out, cleared_ids


def collect_cited_span_ids(messages: list[dict]) -> set[str]:
    """Heuristic: any span-id string that appears in a non-tool message
    after that tool message is treated as a citation.

    Cheap and deterministic; missing a real citation only means a stale
    tool result might be cleared earlier than strictly necessary —
    safe, because the artifact store still has the body.
    """
    seen_tool_ids: dict[str, int] = {}
    cited: set[str] = set()
    for i, msg in enumerate(messages):
        if _is_tool_message(msg):
            sid = _span_id(msg)
            if sid is not None:
                seen_tool_ids.setdefault(sid, i)
            continue
        content = msg.get("content")
        if not isinstance(content, str):
            continue
        for sid, tool_idx in seen_tool_ids.items():
            if i > tool_idx and sid in content:
                cited.add(sid)
    return cited


# ────────────────────────────────────────────────────────────────
# Forget(span_id) tool — adapter for whatever tool registry runs this
# ────────────────────────────────────────────────────────────────


FORGET_TOOL_NAME = "Forget"
FORGET_TOOL_DESCRIPTION = (
    "Drop a tool result from context. Use after you have extracted "
    "everything you need from it; the artifact body remains retrievable "
    "via the View tool. Pass the tool result's id as span_id."
)


def forget_tool_handler(
    messages: list[dict], *, span_id: str
) -> dict[str, object]:
    """Apply Forget(span_id) and return a JSON-serialisable status.

    Suitable as a low-risk write-free tool handler — the only effect
    is on the transcript that the caller is about to send back to the
    model. Callers must take the returned ``messages`` and overwrite
    their local copy.
    """
    new_messages, cleared = clear_tool_result(
        messages, span_id, reason="agent-requested clear"
    )
    return {
        "messages": new_messages,
        "cleared": cleared,
        "span_id": span_id,
    }


__all__ = [
    "FORGET_TOOL_DESCRIPTION",
    "FORGET_TOOL_NAME",
    "SPAN_ID_KEYS",
    "TOOL_ROLES",
    "clear_stale_tool_results",
    "clear_tool_result",
    "collect_cited_span_ids",
    "forget_tool_handler",
]
