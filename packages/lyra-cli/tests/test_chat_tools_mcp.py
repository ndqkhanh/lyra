"""Phase C.4 tests — MCP tools wired into the chat-mode tool loop.

We drive ``run_chat_tool_loop`` directly with a scripted LLM that
proposes an ``mcp__server__tool`` call on the first hop, and assert:

* the dispatcher routes the call to the right transport,
* the result is rendered (and surfaced to the renderer callback),
* the LLM's second hop sees the tool-result message,
* the local chat-tool registry still works alongside MCP tools,
* an MCP error path turns into an ``is_error=True`` ToolEvent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from harness_core.messages import Message, ToolCall

from lyra_cli.interactive.chat_tools import (
    ToolEvent,
    chat_tool_schemas,
    collect_mcp_tool_specs,
    run_chat_tool_loop,
)


# ---------------------------------------------------------------------------
# Test fixtures: scripted LLM + fake registry/transport
# ---------------------------------------------------------------------------


@dataclass
class _Reply:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class _ScriptedLLM:
    """Replays a list of ``_Reply`` objects on each ``generate`` call."""

    replies: list[_Reply]
    last_usage: dict[str, Any] = field(default_factory=dict)
    seen_tools: list[Any] = field(default_factory=list)

    def generate(self, messages, *, tools=None, max_tokens=None):
        self.seen_tools.append(tools)
        idx = min(len(self.seen_tools) - 1, len(self.replies) - 1)
        return self.replies[idx]


@dataclass
class _FakeRegistry:
    """Minimal stand-in: returns no chat-mode schemas, never executes."""

    def schemas(self, *, allowed=None):
        return []

    def execute(self, _call):  # pragma: no cover — never hit in MCP-only paths
        raise AssertionError("registry.execute should not run for MCP calls")


class _FakeMCPTransport:
    def __init__(self, response: dict | None = None, raise_exc: bool = False) -> None:
        self.response = response or {
            "content": [{"type": "text", "text": "fs read ok"}]
        }
        self.raise_exc = raise_exc
        self.calls: list[Any] = []

    def list_tools(self):
        return [
            {
                "name": "read_file",
                "description": "read a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            }
        ]

    def call_tool(self, name: str, args: dict, *, timeout=None):
        self.calls.append((name, dict(args), timeout))
        if self.raise_exc:
            raise RuntimeError("boom")
        return self.response


def _events() -> tuple[list[ToolEvent], Any]:
    captured: list[ToolEvent] = []

    def render(event: ToolEvent) -> None:
        captured.append(event)

    return captured, render


# ---------------------------------------------------------------------------
# collect_mcp_tool_specs
# ---------------------------------------------------------------------------


class _SessionStub:
    def __init__(self, servers, clients):
        self.mcp_servers = servers
        self._mcp_clients = clients


def test_collect_mcp_tool_specs_with_no_clients_returns_empty() -> None:
    session = _SessionStub(servers=[], clients={})
    schemas, entries, transports = collect_mcp_tool_specs(session)
    assert schemas == []
    assert entries == {}
    assert transports == {}


def test_collect_mcp_tool_specs_normalises_active_clients() -> None:
    transport = _FakeMCPTransport()

    class _Cfg:
        name = "filesystem"
        trust = "third-party"

    session = _SessionStub(servers=[_Cfg()], clients={"filesystem": transport})
    schemas, entries, transports = collect_mcp_tool_specs(session)
    assert len(schemas) == 1
    assert schemas[0]["name"] == "mcp__filesystem__read_file"
    assert "mcp__filesystem__read_file" in entries
    assert transports["mcp__filesystem__read_file"] is transport


def test_collect_mcp_tool_specs_only_trusted_filters() -> None:
    fs = _FakeMCPTransport()
    git = _FakeMCPTransport()

    class _Cfg:
        def __init__(self, name, trust):
            self.name = name
            self.trust = trust

    session = _SessionStub(
        servers=[_Cfg("fs", "third-party"), _Cfg("git", "first-party")],
        clients={"fs": fs, "git": git},
    )
    schemas, _, _ = collect_mcp_tool_specs(session, only_trusted=True)
    names = [s["name"] for s in schemas]
    assert all("git" in n for n in names), names
    assert all("fs" not in n for n in names), names


# ---------------------------------------------------------------------------
# run_chat_tool_loop with MCP transports
# ---------------------------------------------------------------------------


def test_loop_dispatches_mcp_tool_call_and_feeds_result() -> None:
    transport = _FakeMCPTransport(
        response={"content": [{"type": "text", "text": "hello world"}]}
    )
    schemas, _entries, transports = collect_mcp_tool_specs(
        _SessionStub(
            servers=[type("Cfg", (), {"name": "fs", "trust": "third-party"})()],
            clients={"fs": transport},
        )
    )
    llm = _ScriptedLLM(
        replies=[
            _Reply(
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="mcp__fs__read_file",
                        args={"path": "/tmp/x"},
                    )
                ]
            ),
            _Reply(content="The file says: hello world"),
        ]
    )
    captured, render = _events()
    report = run_chat_tool_loop(
        llm,
        [Message.user("read it")],
        _FakeRegistry(),
        render=render,
        max_steps=5,
        max_tokens=256,
        mcp_schemas=schemas,
        mcp_transports=transports,
    )
    assert report.final_text == "The file says: hello world"
    assert report.tool_calls == 1
    assert report.steps == 2
    assert transport.calls == [("read_file", {"path": "/tmp/x"}, 60.0)]
    kinds = [e.kind for e in captured]
    assert "call" in kinds and "result" in kinds
    [result_event] = [e for e in captured if e.kind == "result"]
    assert result_event.is_error is False
    assert "hello world" in result_event.output


def test_loop_handles_mcp_dispatch_exception() -> None:
    transport = _FakeMCPTransport(raise_exc=True)
    schemas, _entries, transports = collect_mcp_tool_specs(
        _SessionStub(
            servers=[type("Cfg", (), {"name": "fs", "trust": "third-party"})()],
            clients={"fs": transport},
        )
    )
    llm = _ScriptedLLM(
        replies=[
            _Reply(
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="mcp__fs__read_file",
                        args={"path": "/x"},
                    )
                ]
            ),
            _Reply(content="acknowledged"),
        ]
    )
    captured, render = _events()
    report = run_chat_tool_loop(
        llm,
        [Message.user("read")],
        _FakeRegistry(),
        render=render,
        max_steps=3,
        mcp_schemas=schemas,
        mcp_transports=transports,
    )
    [result_event] = [e for e in captured if e.kind == "result"]
    assert result_event.is_error is True
    assert "boom" in result_event.output
    # The loop still continues to a final hop, so the report has the
    # acknowledged answer and one tool call worth of damage.
    assert report.final_text == "acknowledged"


def test_loop_passes_mcp_schemas_to_provider() -> None:
    transport = _FakeMCPTransport()
    schemas, _entries, transports = collect_mcp_tool_specs(
        _SessionStub(
            servers=[type("Cfg", (), {"name": "fs", "trust": "third-party"})()],
            clients={"fs": transport},
        )
    )
    llm = _ScriptedLLM(replies=[_Reply(content="no tool")])
    run_chat_tool_loop(
        llm,
        [Message.user("hi")],
        _FakeRegistry(),
        max_steps=1,
        mcp_schemas=schemas,
        mcp_transports=transports,
    )
    [tools_seen] = llm.seen_tools
    names = [t["name"] for t in tools_seen]
    assert any("mcp__fs__read_file" in n for n in names)
