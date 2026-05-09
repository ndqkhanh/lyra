"""Tests for ``lyra_mcp.client.toolspec`` (Phase C.3).

Covers the round-trip from raw ``tools/list`` payloads to chat-loop
schemas and back, including the dispatcher and result rendering.
"""
from __future__ import annotations

from typing import Any

import pytest

from lyra_mcp.client.toolspec import (
    MCPToolDispatcher,
    MCPToolEntry,
    normalise_mcp_tools,
    parse_lyra_mcp_name,
    render_mcp_result_for_chat,
)


def test_normalise_creates_lyra_prefixed_name() -> None:
    raw = [
        {
            "name": "read_file",
            "description": "Read a file from disk.",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
        }
    ]
    entries = normalise_mcp_tools("filesystem", raw)
    assert len(entries) == 1
    e = entries[0]
    assert isinstance(e, MCPToolEntry)
    assert e.lyra_name == "mcp__filesystem__read_file"
    assert e.schema["name"] == "mcp__filesystem__read_file"
    assert e.schema["description"] == "Read a file from disk."
    assert e.schema["input_schema"]["properties"]["path"]["type"] == "string"


def test_normalise_handles_missing_description() -> None:
    raw = [{"name": "ping", "inputSchema": None}]
    [entry] = normalise_mcp_tools("net", raw)
    assert "ping" in entry.schema["description"]
    assert entry.schema["input_schema"] == {
        "type": "object",
        "properties": {},
        "additionalProperties": True,
    }


def test_normalise_skips_invalid_entries() -> None:
    raw = [
        {"name": "ok"},
        {"description": "no name"},
        "not-a-dict",
        {"name": ""},
    ]
    entries = normalise_mcp_tools("svr", raw)
    assert [e.original_name for e in entries] == ["ok"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("mcp__filesystem__read_file", ("filesystem", "read_file")),
        ("mcp__a__b", ("a", "b")),
        ("mcp__server__tool_with_underscores", ("server", "tool_with_underscores")),
        ("mcp__svr__a__b", ("svr", "a__b")),
        ("Read", None),
        ("mcp__only", None),
        ("mcp____tool", None),
        ("mcp__svr__", None),
    ],
)
def test_parse_lyra_mcp_name_round_trip(name: str, expected: Any) -> None:
    assert parse_lyra_mcp_name(name) == expected


class _FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, Any]] = []
        self.next_result: dict = {"content": [{"type": "text", "text": "ok"}]}

    def call_tool(self, name, args, *, timeout=None):
        self.calls.append((name, dict(args), timeout))
        return self.next_result


def test_dispatcher_routes_to_correct_transport() -> None:
    fs = _FakeTransport()
    git = _FakeTransport()
    disp = MCPToolDispatcher(transports={"filesystem": fs, "git": git})
    out = disp.call("mcp__filesystem__read", {"path": "/tmp/x"}, timeout=5.0)
    assert out is fs.next_result
    assert fs.calls == [("read", {"path": "/tmp/x"}, 5.0)]
    assert git.calls == []


def test_dispatcher_raises_for_unknown_server() -> None:
    disp = MCPToolDispatcher(transports={"a": _FakeTransport()})
    with pytest.raises(KeyError):
        disp.call("mcp__b__x", {})


def test_dispatcher_raises_for_non_mcp_name() -> None:
    disp = MCPToolDispatcher(transports={"a": _FakeTransport()})
    with pytest.raises(KeyError):
        disp.call("Read", {})


def test_render_text_only_result() -> None:
    result = {
        "content": [
            {"type": "text", "text": "hello "},
            {"type": "text", "text": "world"},
        ]
    }
    assert render_mcp_result_for_chat(result) == "hello \nworld"


def test_render_error_marker_prefixes_text() -> None:
    result = {
        "isError": True,
        "content": [{"type": "text", "text": "tool blew up"}],
    }
    out = render_mcp_result_for_chat(result)
    assert out.startswith("[mcp error]")
    assert "tool blew up" in out


def test_render_falls_back_to_json_for_unknown_part_types() -> None:
    result = {"content": [{"type": "image", "data": "abc"}]}
    out = render_mcp_result_for_chat(result)
    assert "image" in out
    assert "abc" in out


def test_render_handles_non_dict_input() -> None:
    out = render_mcp_result_for_chat([1, 2, 3])  # type: ignore[arg-type]
    assert "[" in out  # JSON list
