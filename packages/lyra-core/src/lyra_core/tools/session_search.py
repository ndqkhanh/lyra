"""``session_search`` tool — FTS5 recall with optional LLM summarize.

Exposes an LLM-callable tool that searches historical session
transcripts for relevant messages and, if a summarizer is wired in,
returns a compressed digest instead of raw transcripts. This avoids
dumping full conversations into the context window — the hermes
``session_search`` recall-tool pattern.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable


def _format_raw_hits(hits: Iterable[dict], *, max_chars: int = 400) -> str:
    """Turn raw FTS5 hits into a compact bulleted digest."""
    lines: list[str] = []
    for hit in hits:
        snippet = (hit.get("content") or "").strip().replace("\n", " ")
        if len(snippet) > max_chars:
            snippet = snippet[: max_chars - 1] + "…"
        lines.append(
            f"- [{hit.get('session_id', '?')} · {hit.get('role', '?')}] {snippet}"
        )
    return "\n".join(lines)


def make_session_search_tool(
    *,
    store: Any,
    summarizer: Callable[[str, str], str] | None = None,
) -> Callable[..., dict]:
    """Factory that binds a ``session_search`` tool to a :class:`SessionStore`.

    Args:
        store: :class:`lyra_core.sessions.store.SessionStore`.
        summarizer: Optional callable ``(query, digest) -> str`` that
            distils raw hits into a short summary. If omitted, the tool
            returns the raw digest.
    """

    def session_search(query: str, *, k: int = 10) -> dict:
        """Recall tool — search historical sessions for context."""
        hits = store.search_messages(query, k=k)
        digest = _format_raw_hits(hits) if hits else "(no matches)"
        summary: str | None = None
        if summarizer and hits:
            try:
                summary = summarizer(query, digest)
            except Exception:
                summary = None
        return {
            "query": query,
            "match_count": len(hits),
            "hits": hits,
            "digest": digest,
            "summary": summary,
        }

    session_search.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "session_search",
        "description": (
            "Search your prior sessions for relevant context. Uses FTS5 "
            "matching; returns bm25-ranked hits plus a compressed digest."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
            },
            "required": ["query"],
        },
    }
    return session_search


__all__ = ["make_session_search_tool"]
