"""Minimal OTLP-shaped exporter + real OpenTelemetry SDK bridge.

v1 shipped a pure-Python in-memory collector so the test suite runs
without the ``opentelemetry`` extra installed. v1.7.3 adds
:class:`OpenTelemetryCollector` that converts HIR span dicts into real
OTel spans on an injected tracer provider — production wiring hands in
an ``OTLPSpanExporter``-backed ``TracerProvider`` so events fan out to
Jaeger / Honeycomb / Datadog.

The real path stays optional: ``opentelemetry-sdk`` is only needed
when no tracer provider is injected. Tests pass a fake provider so
the collector can be covered offline.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ..lsp_backend.errors import FeatureUnavailable
from .hir import HirEvent


@runtime_checkable
class Collector(Protocol):
    def submit(self, span: dict) -> None: ...


@dataclass
class InMemoryCollector:
    spans: list[dict] = field(default_factory=list)

    def submit(self, span: dict) -> None:
        self.spans.append(span)


@dataclass
class OTLPExporter:
    collector: Collector

    def export(self, events: Iterable[HirEvent]) -> None:
        for ev in events:
            span = {
                "session_id": ev.session_id,
                "ts": ev.ts,
                "kind": ev.kind,
                "attributes": ev.payload,
            }
            self.collector.submit(span)


# --- Real OpenTelemetry bridge ------------------------------------- #


_PRIMITIVE_TYPES: tuple[type, ...] = (str, bool, int, float)


def _coerce_attribute(value: Any) -> Any:
    """Coerce an HIR payload value to an OTel-legal attribute type."""
    if value is None:
        return ""
    if isinstance(value, _PRIMITIVE_TYPES):
        return value
    if isinstance(value, (list, tuple)):
        # lists of primitives are legal; coerce nested non-primitives.
        if all(isinstance(x, _PRIMITIVE_TYPES) for x in value):
            return list(value)
        try:
            return json.dumps(list(value), default=str)
        except Exception:
            return repr(list(value))
    try:
        return json.dumps(value, default=str)
    except Exception:
        return repr(value)


class OpenTelemetryCollector:
    """Adapter that submits HIR span dicts as real OTel spans.

    Parameters
    ----------
    tracer_provider:
        Optional injected OTel tracer provider. When ``None``, we try
        to import :mod:`opentelemetry` and use its global provider;
        a missing SDK raises :class:`FeatureUnavailable`.
    tracer_name:
        Instrumentation scope name passed to ``get_tracer``.
    """

    def __init__(
        self,
        *,
        tracer_provider: Any | None = None,
        tracer_name: str = "lyra.events",
    ) -> None:
        if tracer_provider is None:
            try:
                from opentelemetry import trace  # type: ignore[import-not-found]
            except Exception as exc:
                raise FeatureUnavailable(
                    "OpenTelemetryCollector default provider needs "
                    "opentelemetry-sdk. Install with "
                    "`pip install 'lyra[otel]'` or pass a tracer_provider "
                    f"explicitly. (underlying: {exc!r})"
                ) from exc
            tracer_provider = trace.get_tracer_provider()

        self._provider = tracer_provider
        self._tracer = tracer_provider.get_tracer(tracer_name)

    def submit(self, span: dict) -> None:
        kind = str(span.get("kind") or "lyra.event")
        attrs: dict[str, Any] = {}
        session_id = span.get("session_id")
        if session_id:
            attrs["lyra.session_id"] = str(session_id)
        ts = span.get("ts")
        if ts:
            attrs["lyra.ts"] = str(ts)

        for k, v in (span.get("attributes") or {}).items():
            attrs[str(k)] = _coerce_attribute(v)

        ctx = self._tracer.start_as_current_span(kind, attributes=attrs)
        # The fake double + real OTel both support context manager + .end();
        # using ``with`` guarantees ``end()`` is called.
        try:
            with ctx:
                pass
        except AttributeError:
            # Real OTel returns ``_Tracer.Span`` objects that are context
            # managers; the fallback branch only runs for exotic doubles.
            span_obj = ctx
            try:
                span_obj.end()
            except Exception:  # pragma: no cover - best-effort
                pass
