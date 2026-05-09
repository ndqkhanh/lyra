"""Minimal Lyra MCP server surface (in-process).

Real transports (stdio, HTTP) will wrap this object. The test suite exercises
the tool surface directly via ``call_tool``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class UnauthorizedError(Exception):
    pass


@dataclass
class LyraMCPApp:
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    plans: dict[str, str] = field(default_factory=dict)
    bearer_token: str = ""

    def _tools(self) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        return {
            "read_session": self._tool_read_session,
            "get_plan": self._tool_get_plan,
        }

    # ---- tools ----
    def _tool_read_session(self, args: dict[str, Any]) -> dict[str, Any]:
        sid = str(args.get("session_id", ""))
        if sid not in self.sessions:
            raise KeyError(f"unknown session_id: {sid}")
        return dict(self.sessions[sid])

    def _tool_get_plan(self, args: dict[str, Any]) -> dict[str, Any]:
        sid = str(args.get("session_id", ""))
        return {"markdown": self.plans.get(sid, "")}

    # ---- dispatch ----
    def call_tool(
        self, name: str, args: dict[str, Any], *, bearer: str = ""
    ) -> dict[str, Any]:
        if self.bearer_token and bearer != self.bearer_token:
            raise UnauthorizedError("bearer token mismatch")
        tools = self._tools()
        if name not in tools:
            raise KeyError(f"unknown tool: {name}")
        return tools[name](args)


def create_app(
    *,
    sessions: dict[str, dict[str, Any]],
    plans: dict[str, str],
    bearer_token: str,
) -> LyraMCPApp:
    return LyraMCPApp(
        sessions=dict(sessions), plans=dict(plans), bearer_token=bearer_token
    )
