"""
Tests for the Tool Registry (ToolDef, ToolRegistry, validate_parameters).
"""

from __future__ import annotations

import pytest

from lyra.tools.registry import ToolDef, ToolRegistry, validate_parameters


# ---------------------------------------------------------------------------
# ToolDef
# ---------------------------------------------------------------------------


class TestToolDef:
    def test_minimal_tooldef(self) -> None:
        t = ToolDef(name="ping", description="A simple ping tool")
        assert t.name == "ping"
        assert t.description == "A simple ping tool"
        assert t.parameters == {}
        assert t.handler is None
        assert t.capabilities == []
        assert t.sandbox_requirements == {}

    def test_full_tooldef(self) -> None:
        async def my_handler(**kw):  # type: ignore
            return {"output": "ok"}

        params = {"type": "object", "properties": {"x": {"type": "integer"}}}
        t = ToolDef(
            name="full",
            description="Full tool",
            parameters=params,
            handler=my_handler,
            capabilities=["file", "network"],
            sandbox_requirements={"timeout_seconds": 10},
        )
        assert t.name == "full"
        assert t.handler is my_handler
        assert t.capabilities == ["file", "network"]

    def test_immutable(self) -> None:
        t = ToolDef(name="immutable", description="Check frozen")
        with pytest.raises(Exception):
            t.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------


class TestToolRegistry:
    def test_register_and_get(self) -> None:
        reg = ToolRegistry()
        t = ToolDef(name="echo", description="Echo tool")
        reg.register(t)
        assert reg.get("echo") is t
        assert reg.has_tool("echo") is True

    def test_register_duplicate_raises(self) -> None:
        reg = ToolRegistry()
        reg.register(ToolDef(name="dup", description="First"))
        with pytest.raises(ValueError, match="already registered"):
            reg.register(ToolDef(name="dup", description="Second"))

    def test_unregister_returns_tool(self) -> None:
        reg = ToolRegistry()
        t = ToolDef(name="tmp", description="Temporary")
        reg.register(t)
        removed = reg.unregister("tmp")
        assert removed is t
        assert reg.get("tmp") is None

    def test_unregister_nonexistent_returns_none(self) -> None:
        reg = ToolRegistry()
        assert reg.unregister("nosuch") is None

    def test_list_tools(self) -> None:
        reg = ToolRegistry()
        a = ToolDef(name="a", description="A")
        b = ToolDef(name="b", description="B")
        reg.register(a)
        reg.register(b)
        names = {t.name for t in reg.list_tools()}
        assert names == {"a", "b"}

    def test_list_by_capability(self) -> None:
        reg = ToolRegistry()
        t1 = ToolDef(name="read", description="Read", capabilities=["file"])
        t2 = ToolDef(name="write", description="Write", capabilities=["file"])
        t3 = ToolDef(name="search", description="Search", capabilities=["network"])
        reg.register(t1)
        reg.register(t2)
        reg.register(t3)

        file_tools = reg.list_by_capability("file")
        assert {t.name for t in file_tools} == {"read", "write"}

        network_tools = reg.list_by_capability("network")
        assert {t.name for t in network_tools} == {"search"}

    def test_list_by_capability_nonexistent(self) -> None:
        reg = ToolRegistry()
        assert reg.list_by_capability("nosuch") == []

    def test_list_capabilities(self) -> None:
        reg = ToolRegistry()
        reg.register(ToolDef(name="a", description="A", capabilities=["x", "y"]))
        reg.register(ToolDef(name="b", description="B", capabilities=["y", "z"]))
        caps = set(reg.list_capabilities())
        assert caps == {"x", "y", "z"}

    def test_capability_index_cleanup_on_unregister(self) -> None:
        reg = ToolRegistry()
        t = ToolDef(name="tmp", description="Tmp", capabilities=["file"])
        reg.register(t)
        assert "file" in reg.list_capabilities()
        reg.unregister("tmp")
        assert "file" not in reg.list_capabilities()


# ---------------------------------------------------------------------------
# validate_parameters
# ---------------------------------------------------------------------------


class TestValidateParameters:
    def test_valid_inputs(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["name"],
        }
        errors = validate_parameters(schema, {"name": "foo", "count": 3})
        assert errors == []

    def test_missing_required(self) -> None:
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        errors = validate_parameters(schema, {})
        assert len(errors) >= 1
        assert any("name" in e for e in errors)

    def test_wrong_type(self) -> None:
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer"}},
        }
        errors = validate_parameters(schema, {"age": "not-an-int"})
        assert len(errors) >= 1

    def test_empty_schema_accepts_all(self) -> None:
        assert validate_parameters({}, {"anything": "goes"}) == []

    def test_no_properties_accepts_all(self) -> None:
        assert validate_parameters({"type": "object"}, {"x": 1}) == []

    def test_extra_fields_ok(self) -> None:
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string"}},
        }
        errors = validate_parameters(schema, {"a": "ok", "extra": 42})
        assert errors == []
