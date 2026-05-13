"""Unit tests for OtelExporter — no actual OTel SDK required."""
from __future__ import annotations

import pytest

from lyra_core.transparency.otel_exporter import (
    OtelConfig,
    OtelExporter,
    _build_span_attributes,
)
from lyra_core.transparency.event_store import make_event


@pytest.mark.unit
def test_disabled_exporter_is_noop() -> None:
    cfg = OtelConfig(enabled=False)
    exp = OtelExporter(cfg)
    ev = make_event("PreToolUse", session_id="s1", tool_name="Bash")
    exp.export(ev)  # must not raise


@pytest.mark.unit
def test_span_attributes_include_required_fields() -> None:
    cfg = OtelConfig(enabled=False)
    ev = make_event("PreToolUse", session_id="sess-abc", tool_name="Edit")
    attrs = _build_span_attributes(ev, cfg)
    assert attrs["gen_ai.operation.name"] == "execute_tool"
    assert attrs["gen_ai.provider.name"] == "anthropic"
    assert attrs["gen_ai.agent.id"] == "sess-abc"
    assert attrs["gen_ai.tool.name"] == "Edit"


@pytest.mark.unit
def test_span_attributes_session_start_maps_to_create_agent() -> None:
    cfg = OtelConfig(enabled=False)
    ev = make_event("SessionStart", session_id="s1")
    attrs = _build_span_attributes(ev, cfg)
    assert attrs["gen_ai.operation.name"] == "create_agent"


@pytest.mark.unit
def test_export_privacy_off_by_default() -> None:
    cfg = OtelConfig(enabled=False, export_tool_args=False)
    ev = make_event("PostToolUse", session_id="s1",
                    payload={"usage": {"input_tokens": 1000}})
    attrs = _build_span_attributes(ev, cfg)
    assert "gen_ai.usage.input_tokens" not in attrs


@pytest.mark.unit
def test_export_tool_args_includes_usage() -> None:
    cfg = OtelConfig(enabled=False, export_tool_args=True)
    ev = make_event("PostToolUse", session_id="s1",
                    payload={"usage": {"input_tokens": 1000, "output_tokens": 500}})
    attrs = _build_span_attributes(ev, cfg)
    assert attrs.get("gen_ai.usage.input_tokens") == 1000
    assert attrs.get("gen_ai.usage.output_tokens") == 500


@pytest.mark.unit
def test_unknown_hook_type_still_exports() -> None:
    cfg = OtelConfig(enabled=False)
    ev = make_event("UnknownHook", session_id="s1")
    attrs = _build_span_attributes(ev, cfg)
    assert "gen_ai.operation.name" in attrs
