"""In-REPL tool registry scaffold.

This is the *shape* of the tool registry the v1 Phase 1 kernel will
wire into the agent loop. Today it surfaces through ``/tools`` so users
can see what's coming; each entry carries:

- ``name``:     unique identifier the loop uses to route a tool call.
- ``risk``:     one of ``low`` / ``medium`` / ``high``. ``high`` lands
                behind the PermissionBridge approval flow.
- ``summary``:  one-line blurb for ``/help`` and ``/tools``.
- ``origin``:   ``builtin`` for shipped tools, ``mcp:<server>`` for
                Model-Context-Protocol tools discovered at runtime (v1
                Phase 10), ``user`` for user-registered callables.
- ``planned``:  milestone tag pointing at the roadmap.

We intentionally keep the registry module tiny and data-shaped, so the
real Python implementations can live in ``lyra-core/tools/*.py``
once Phase 1 lands. Keeping it here unblocks the CLI affordance today
without committing to a specific runtime contract yet.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, TypedDict


Risk = Literal["low", "medium", "high"]


class ToolSpec(TypedDict):
    """What ``/tools`` renders and what the loop will dispatch on."""

    name: str
    risk: Risk
    summary: str
    origin: str
    planned: str


_BUILTIN_TOOLS: tuple[ToolSpec, ...] = (
    {
        "name": "Read",
        "risk": "low",
        "summary": "read a file, optionally sliced by line offset / limit",
        "origin": "builtin",
        "planned": "v1 Phase 1",
    },
    {
        "name": "Glob",
        "risk": "low",
        "summary": "glob the repo for files matching a pattern",
        "origin": "builtin",
        "planned": "v1 Phase 1",
    },
    {
        "name": "Grep",
        "risk": "low",
        "summary": "ripgrep across the repo with type + glob filters",
        "origin": "builtin",
        "planned": "v1 Phase 1",
    },
    {
        "name": "Edit",
        "risk": "medium",
        "summary": "string-replace in a single file (tdd-gate-protected)",
        "origin": "builtin",
        "planned": "v1 Phase 1",
    },
    {
        "name": "Write",
        "risk": "medium",
        "summary": "create or overwrite a file (tdd-gate-protected)",
        "origin": "builtin",
        "planned": "v1 Phase 1",
    },
    {
        "name": "Bash",
        "risk": "high",
        "summary": "run a shell command (permission-gated; today use `!cmd`)",
        "origin": "builtin",
        "planned": "v1 Phase 1",
    },
    {
        "name": "TodoWrite",
        "risk": "low",
        "summary": "maintain the in-session task list panel",
        "origin": "builtin",
        "planned": "v1.5",
    },
    {
        "name": "ExecuteCode",
        "risk": "high",
        "summary": "sandboxed Python execution (CodeAct plugin)",
        "origin": "builtin",
        "planned": "v1.5 Phase 14",
    },
    {
        "name": "WebSearch",
        "risk": "low",
        "summary": "search the web and return ranked snippets",
        "origin": "builtin",
        "planned": "v1.5",
    },
    {
        "name": "WebFetch",
        "risk": "low",
        "summary": "fetch and markdown-render a URL",
        "origin": "builtin",
        "planned": "v1.5",
    },
    {
        "name": "Browser",
        "risk": "medium",
        "summary": "headless browser automation (Browserbase/playwright)",
        "origin": "builtin",
        "planned": "v2",
    },
    {
        "name": "Delegate",
        "risk": "medium",
        "summary": "spawn a subagent in a git worktree (DAG + skill-creator)",
        "origin": "builtin",
        "planned": "v1 Phase 7",
    },
    {
        "name": "MCP",
        "risk": "medium",
        "summary": "umbrella tool for MCP-advertised tools (progressive disclosure)",
        "origin": "builtin",
        "planned": "v1 Phase 10",
    },
    {
        "name": "Skill",
        "risk": "low",
        "summary": "invoke a named skill from the router",
        "origin": "builtin",
        "planned": "v1 Phase 6",
    },
)


def registered_tools() -> list[ToolSpec]:
    """Return every known tool, sorted for stable rendering."""
    return sorted(_BUILTIN_TOOLS, key=lambda t: (_risk_rank(t["risk"]), t["name"]))


def tool_by_name(name: str) -> ToolSpec | None:
    for tool in _BUILTIN_TOOLS:
        if tool["name"].lower() == name.lower():
            return tool
    return None


def tools_of_risk(levels: Iterable[Risk]) -> list[ToolSpec]:
    target = set(levels)
    return [t for t in registered_tools() if t["risk"] in target]


def _risk_rank(r: Risk) -> int:
    return {"low": 0, "medium": 1, "high": 2}[r]
