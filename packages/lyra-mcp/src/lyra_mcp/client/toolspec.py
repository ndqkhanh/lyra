"""Translate MCP ``tools/list`` output into Lyra's chat tool schema.

MCP servers advertise tools as ``{name, description?, inputSchema?}``
records, where ``inputSchema`` is a JSON Schema object the model is
expected to populate. Lyra's chat-tool registry (``chat_tools.py``)
takes Anthropic-style ``{name, description, input_schema}`` dicts —
same shape, just different key. This module bridges the two and
also folds the server name into the tool name as
``mcp__<server>__<tool>`` (the convention Claude Code / Codex /
open-claw all use, so the LLM's mental model carries over).

Also exposes :class:`MCPToolDispatcher`, a tiny callable that
takes the Lyra-side tool name and arguments and routes them to the
right MCP transport's ``call_tool``. The chat loop (Phase C.4) uses
this when the model proposes a tool call whose name starts with
``mcp__``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

_MCP_PREFIX = "mcp__"


@dataclass(frozen=True)
class MCPToolEntry:
    """One advertised MCP tool, normalised to Lyra's chat-loop shape."""

    server: str
    original_name: str
    schema: dict[str, Any]
    raw: dict[str, Any]

    @property
    def lyra_name(self) -> str:
        return f"{_MCP_PREFIX}{self.server}__{self.original_name}"


def _coerce_input_schema(raw: Any) -> dict[str, Any]:
    """Return a Lyra-compatible ``input_schema`` dict.

    MCP servers occasionally emit ``inputSchema=null`` for
    parameter-less tools. Lyra's renderer expects an object schema, so
    we substitute the empty-object schema in that case.
    """
    if isinstance(raw, dict):
        return raw
    return {"type": "object", "properties": {}, "additionalProperties": True}


def normalise_mcp_tools(
    server_name: str,
    tools: Iterable[Mapping[str, Any]],
) -> list[MCPToolEntry]:
    """Convert one server's ``tools/list`` response into entries."""
    out: list[MCPToolEntry] = []
    for t in tools or []:
        if not isinstance(t, Mapping):
            continue
        name = t.get("name")
        if not isinstance(name, str) or not name:
            continue
        original_name = name
        description = (t.get("description") or "").strip()
        input_schema = _coerce_input_schema(
            t.get("inputSchema") or t.get("input_schema")
        )
        schema = {
            "name": f"{_MCP_PREFIX}{server_name}__{original_name}",
            "description": description
            or f"Tool {original_name!r} from MCP server {server_name!r}",
            "input_schema": input_schema,
        }
        out.append(
            MCPToolEntry(
                server=server_name,
                original_name=original_name,
                schema=schema,
                raw=dict(t),
            )
        )
    return out


def parse_lyra_mcp_name(lyra_name: str) -> Optional[tuple[str, str]]:
    """Split ``mcp__<server>__<tool>`` back into ``(server, tool)``.

    Returns ``None`` for any name that doesn't match the convention,
    so the dispatcher can fall through to the regular chat tools.
    """
    if not lyra_name.startswith(_MCP_PREFIX):
        return None
    rest = lyra_name[len(_MCP_PREFIX):]
    sep = rest.find("__")
    if sep < 1:
        return None
    server = rest[:sep]
    tool = rest[sep + 2:]
    if not server or not tool:
        return None
    return (server, tool)


@dataclass
class MCPToolDispatcher:
    """Routes ``mcp__<server>__<tool>`` calls to the right transport.

    ``transports`` maps server name → transport with ``call_tool``.
    Anything not in the map (or with a non-mcp prefix) raises
    :class:`KeyError` so the chat loop knows to delegate elsewhere.
    """

    transports: dict[str, Any] = field(default_factory=dict)

    def call(
        self,
        lyra_name: str,
        arguments: Mapping[str, Any],
        *,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        parsed = parse_lyra_mcp_name(lyra_name)
        if parsed is None:
            raise KeyError(f"not an MCP tool name: {lyra_name!r}")
        server, tool = parsed
        transport = self.transports.get(server)
        if transport is None:
            raise KeyError(f"no live transport for MCP server {server!r}")
        return transport.call_tool(tool, dict(arguments), timeout=timeout)


def render_mcp_result_for_chat(result: Mapping[str, Any]) -> str:
    """Flatten an MCP ``tools/call`` result into a chat-mode string.

    MCP results carry a ``content`` array of typed parts
    (``text`` / ``image`` / ``resource``). The chat tool loop only
    speaks plain strings today, so this helper concatenates the
    text parts and pretty-prints anything else as compact JSON.
    """
    if not isinstance(result, Mapping):
        return json.dumps(result, ensure_ascii=False, default=str)
    content = result.get("content")
    if not isinstance(content, list):
        return json.dumps(result, ensure_ascii=False, default=str)
    pieces: list[str] = []
    for part in content:
        if isinstance(part, Mapping) and part.get("type") == "text":
            pieces.append(str(part.get("text", "")))
        else:
            pieces.append(json.dumps(part, ensure_ascii=False, default=str))
    flat = "\n".join(p for p in pieces if p).strip()
    if not flat:
        return json.dumps(result, ensure_ascii=False, default=str)
    if result.get("isError"):
        return f"[mcp error] {flat}"
    return flat


__all__ = [
    "MCPToolDispatcher",
    "MCPToolEntry",
    "normalise_mcp_tools",
    "parse_lyra_mcp_name",
    "render_mcp_result_for_chat",
]
