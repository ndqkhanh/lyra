"""OpenTelemetry GenAI span exporter for transparency hook events.

Converts HookEvent records into OTel GenAI spans and exports them via
OTLP gRPC/HTTP. Disabled by default — must be explicitly enabled.
No message content or tool args are exported unless opted in.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from .models import HookEvent


_LOG = logging.getLogger(__name__)

# OTel GenAI semantic convention operation names
_HOOK_TO_OPERATION: dict[str, str] = {
    "SessionStart":  "create_agent",
    "SessionEnd":    "create_agent",
    "SubagentStart": "invoke_agent",
    "SubagentStop":  "invoke_agent",
    "PreToolUse":    "execute_tool",
    "PostToolUse":   "execute_tool",
    "PostToolUseFailure": "execute_tool",
}


@dataclass(frozen=True)
class OtelConfig:
    """Configuration for the OTel exporter."""
    enabled: bool = False
    endpoint: str = "http://localhost:4317"
    export_prompt_text: bool = False   # privacy-off by default
    export_tool_args: bool = False     # privacy-off by default
    service_name: str = "lyra"


def _build_span_attributes(event: HookEvent, cfg: OtelConfig) -> dict:
    """Build OTel GenAI span attributes from a hook event."""
    attrs: dict = {
        "gen_ai.operation.name": _HOOK_TO_OPERATION.get(event.hook_type, "execute_tool"),
        "gen_ai.provider.name": "anthropic",
        "gen_ai.agent.id": event.session_id,
        "lyra.hook_type": event.hook_type,
    }
    if event.tool_name:
        attrs["gen_ai.tool.name"] = event.tool_name

    if cfg.export_tool_args and event.payload_json:
        try:
            payload = json.loads(event.payload_json)
            usage = payload.get("usage") or {}
            if usage.get("input_tokens"):
                attrs["gen_ai.usage.input_tokens"] = usage["input_tokens"]
            if usage.get("output_tokens"):
                attrs["gen_ai.usage.output_tokens"] = usage["output_tokens"]
        except Exception:
            pass

    return attrs


class OtelExporter:
    """Exports hook events as OTel GenAI spans. No-ops when disabled."""

    def __init__(self, cfg: OtelConfig) -> None:
        self._cfg = cfg
        self._tracer = None
        if cfg.enabled:
            self._tracer = _init_tracer(cfg)

    def export(self, event: HookEvent) -> None:
        if not self._cfg.enabled or self._tracer is None:
            return
        if event.hook_type not in _HOOK_TO_OPERATION:
            return
        try:
            self._export_span(event)
        except Exception as exc:  # never block on export failure
            _LOG.debug("otel export failed for %s: %s", event.hook_type, exc)

    def _export_span(self, event: HookEvent) -> None:
        operation = _HOOK_TO_OPERATION[event.hook_type]
        attrs = _build_span_attributes(event, self._cfg)
        with self._tracer.start_as_current_span(operation, attributes=attrs):
            pass  # span is a point-in-time record


def _init_tracer(cfg: OtelConfig):
    """Initialise OTel tracer. Returns None if opentelemetry is not installed."""
    try:
        from opentelemetry import trace  # type: ignore[import-untyped]
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-untyped]
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore[import-untyped]
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore[import-untyped]
        from opentelemetry.sdk.resources import Resource  # type: ignore[import-untyped]

        resource = Resource({"service.name": cfg.service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=cfg.endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        return trace.get_tracer("lyra.transparency")
    except ImportError:
        _LOG.info(
            "opentelemetry-sdk not installed — OTel export disabled. "
            "pip install opentelemetry-exporter-otlp-proto-grpc to enable."
        )
        return None
