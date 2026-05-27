"""Lyra MCP server surface (in-process).

Exposes a set of MCP tools for session introspection, plan retrieval,
skill listing, and memory search. Real transports (stdio, HTTP) wrap
this object; the test suite exercises the tool surface directly via
``call_tool``.

Tools:
  - read_session: Return session state by ID
  - get_plan: Return the Markdown plan for a session
  - list_skills: List available skills (ids, descriptions, packs)
  - search_memory: Search the in-process memory fragment store
  - get_stats: Return server-level usage statistics
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
    skills_manifest: list[dict[str, Any]] = field(default_factory=list)
    bearer_token: str = ""
    _tool_call_count: int = 0

    def _tools(self) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        return {
            "read_session": self._tool_read_session,
            "get_plan": self._tool_get_plan,
            "list_skills": self._tool_list_skills,
            "search_memory": self._tool_search_memory,
            "get_stats": self._tool_get_stats,
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

    def _tool_list_skills(self, args: dict[str, Any]) -> dict[str, Any]:
        """List skills available to the server, optionally filtered by pack."""
        pack_filter = args.get("pack") or None
        skills = self.skills_manifest
        if pack_filter:
            skills = [s for s in skills if s.get("pack") == pack_filter]
        return {
            "skills": [
                {"id": s.get("id"), "name": s.get("name"), "pack": s.get("pack")}
                for s in skills
            ],
            "count": len(skills),
        }

    def _tool_search_memory(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search the in-memory fragment store for relevant fragments."""
        query = str(args.get("query", ""))
        limit = int(args.get("limit", 10))
        if not query:
            return {"fragments": [], "count": 0}

        try:
            from lyra_core.memory.mcp_tools import mcp_recall

            result = mcp_recall(query=query, limit=limit)
            return {"fragments": result.get("fragments", []), "count": result.get("count", 0)}
        except Exception as exc:
            return {"fragments": [], "count": 0, "error": str(exc)}

    def _tool_get_stats(self, args: dict[str, Any]) -> dict[str, Any]:
        """Return server usage statistics."""
        return {
            "tool_calls": self._tool_call_count,
            "active_sessions": len(self.sessions),
            "plans_tracked": len(self.plans),
            "skills_loaded": len(self.skills_manifest),
        }

    # ---- dispatch ----
    def call_tool(
        self, name: str, args: dict[str, Any], *, bearer: str = ""
    ) -> dict[str, Any]:
        if self.bearer_token and bearer != self.bearer_token:
            raise UnauthorizedError("bearer token mismatch")
        tools = self._tools()
        if name not in tools:
            raise KeyError(f"unknown tool: {name}")
        self._tool_call_count += 1
        return tools[name](args)


def create_app(
    *,
    sessions: dict[str, dict[str, Any]] | None = None,
    plans: dict[str, str] | None = None,
    skills_manifest: list[dict[str, Any]] | None = None,
    bearer_token: str = "",
) -> LyraMCPApp:
    return LyraMCPApp(
        sessions=dict(sessions or {}),
        plans=dict(plans or {}),
        skills_manifest=list(skills_manifest or []),
        bearer_token=bearer_token,
    )
