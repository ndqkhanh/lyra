"""Structured log lines — Trace events → line-per-event log records.

Format: each line is a JSON object with a flat schema, parseable by Datadog
/ Splunk / journalctl / any line-oriented log search engine.
"""
from __future__ import annotations

import json
from typing import Iterable

from ..replay import Trace


def structured_log_lines(
    trace: Trace,
    *,
    extra_fields: dict | None = None,
) -> list[str]:
    """Render a :class:`Trace` as a list of JSON log lines.

    Each event becomes one line. Fields are flattened: kind, timestamp,
    event_id, issued_by, namespace_id, plus a stringified payload preview.
    ``extra_fields`` are merged into every line — useful for tagging with
    ``service``, ``environment``, ``region``.

    >>> from harness_core.replay import TraceBuilder, ReplayEventKind
    >>> b = TraceBuilder(trace_id="t1")
    >>> b.add_event(kind=ReplayEventKind.AGENT_DECISION, issued_by="a",
    ...              timestamp=1.0, event_id="e1")
    >>> lines = structured_log_lines(b.build())
    >>> '"trace_id": "t1"' in lines[0]
    True
    """
    extra = dict(extra_fields or {})
    out: list[str] = []
    for e in trace.events:
        record = {
            "trace_id": trace.trace_id,
            "event_id": e.event_id,
            "kind": e.kind.value,
            "timestamp": e.timestamp,
            "issued_by": e.issued_by,
            "namespace_id": e.namespace_id or None,
            "payload_preview": _payload_preview(e.payload),
            **extra,
        }
        out.append(json.dumps(record, sort_keys=True, default=str))
    return out


def _payload_preview(payload: dict, *, max_chars: int = 200) -> str:
    """Compact string preview of a payload for log lines."""
    if not payload:
        return ""
    parts: list[str] = []
    for k, v in payload.items():
        if isinstance(v, (list, tuple)):
            parts.append(f"{k}=[{len(v)}]")
        elif isinstance(v, dict):
            parts.append(f"{k}={{{len(v)}}}")
        else:
            v_repr = str(v)
            if len(v_repr) > 30:
                v_repr = v_repr[:27] + "..."
            parts.append(f"{k}={v_repr}")
    rendered = " ".join(parts)
    if len(rendered) > max_chars:
        rendered = rendered[: max_chars - 3] + "..."
    return rendered


__all__ = ["structured_log_lines"]
