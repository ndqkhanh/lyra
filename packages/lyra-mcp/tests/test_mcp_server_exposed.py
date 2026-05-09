"""Red tests for Lyra-as-MCP-server (read_session, get_plan)."""
from __future__ import annotations

from lyra_mcp.server.app import (
    UnauthorizedError,
    create_app,
)


def test_read_session_requires_auth() -> None:
    app = create_app(sessions={"s1": {"id": "s1", "events": []}}, plans={}, bearer_token="secret")
    try:
        app.call_tool("read_session", {"session_id": "s1"}, bearer="wrong")
    except UnauthorizedError:
        pass
    else:
        raise AssertionError("should reject wrong bearer")


def test_read_session_returns_payload() -> None:
    app = create_app(
        sessions={"s1": {"id": "s1", "events": [{"kind": "tool.call"}]}},
        plans={},
        bearer_token="secret",
    )
    payload = app.call_tool("read_session", {"session_id": "s1"}, bearer="secret")
    assert payload["id"] == "s1"
    assert len(payload["events"]) == 1


def test_get_plan_returns_markdown() -> None:
    app = create_app(
        sessions={},
        plans={"s1": "# plan contents"},
        bearer_token="secret",
    )
    out = app.call_tool("get_plan", {"session_id": "s1"}, bearer="secret")
    assert "# plan contents" in out["markdown"]


def test_unknown_tool_errors() -> None:
    app = create_app(sessions={}, plans={}, bearer_token="secret")
    try:
        app.call_tool("bogus", {}, bearer="secret")
    except KeyError:
        pass
    else:
        raise AssertionError("should raise KeyError on unknown tool")
