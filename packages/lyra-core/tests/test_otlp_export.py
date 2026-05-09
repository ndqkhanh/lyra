"""Red tests for OTLP-shaped exporter (minimal in-memory collector)."""
from __future__ import annotations

from lyra_core.observability.hir import HirEvent
from lyra_core.observability.otel_export import InMemoryCollector, OTLPExporter


def _ev(kind: str) -> HirEvent:
    return HirEvent.from_dict(
        {
            "schema_version": "1.0",
            "session_id": "01HSID00000000000000000000",
            "ts": "2025-01-01T00:00:00Z",
            "kind": kind,
            "payload": {},
        }
    )


def test_exporter_sends_all_events_to_collector() -> None:
    coll = InMemoryCollector()
    exp = OTLPExporter(collector=coll)
    exp.export([_ev("tool.call"), _ev("tool.result"), _ev("session.end")])
    assert len(coll.spans) == 3
    assert [s["kind"] for s in coll.spans] == [
        "tool.call",
        "tool.result",
        "session.end",
    ]


def test_exporter_marks_session_span() -> None:
    coll = InMemoryCollector()
    OTLPExporter(collector=coll).export([_ev("session.start"), _ev("session.end")])
    kinds = [s["kind"] for s in coll.spans]
    assert "session.start" in kinds
    assert "session.end" in kinds
