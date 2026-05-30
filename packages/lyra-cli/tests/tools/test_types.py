"""Tests for extended tools package."""

from __future__ import annotations

import pytest

from lyra_cli.tools.types import (
    ToolCategory,
    ToolDefinition,
    ToolExecution,
    ToolParameter,
    ToolPermission,
    ToolResult,
    ToolRisk,
)


class TestToolDefinition:
    def test_minimal_definition(self):
        td = ToolDefinition(name="test_tool", description="A test", category=ToolCategory.CUSTOM)
        assert td.name == "test_tool"
        assert td.risk_level == ToolRisk.LOW
        assert td.timeout_ms == 30000
        assert td.idempotent is False

    def test_full_definition(self):
        td = ToolDefinition(
            name="file_read",
            description="Read a file",
            category=ToolCategory.FILE,
            permissions=(ToolPermission.READ_ONLY,),
            risk_level=ToolRisk.LOW,
            parameters=(ToolParameter(name="path", type_hint="str", description="File path"),),
            returns="str",
        )
        assert len(td.parameters) == 1
        assert td.permissions == (ToolPermission.READ_ONLY,)

    def test_definition_immutability(self):
        td = ToolDefinition(name="t", description="d", category=ToolCategory.CUSTOM)
        with pytest.raises(Exception):
            td.name = "new_name"

    def test_definition_with_tags(self):
        td = ToolDefinition(
            name="search",
            description="Search files",
            category=ToolCategory.SEARCH,
            tags=("fast", "read-only"),
        )
        assert "fast" in td.tags


class TestToolResult:
    def test_success_result(self):
        r = ToolResult(success=True, data="output", tool_name="test")
        assert r.success
        assert r.data == "output"
        assert not r.error

    def test_error_result(self):
        r = ToolResult(success=False, error="Something broke", tool_name="test")
        assert not r.success
        assert r.error == "Something broke"

    def test_result_immutability(self):
        r = ToolResult(success=True, data="ok", tool_name="t")
        with pytest.raises(Exception):
            r.success = False


class TestToolExecution:
    def test_execution_creation(self):
        td = ToolDefinition(name="run", description="Run", category=ToolCategory.SHELL)
        ex = ToolExecution(
            execution_id="exec-001",
            tool=td,
            inputs={"cmd": "ls"},
        )
        assert ex.status == "pending"
        assert ex.result is None
        assert ex.started_at == 0.0


class TestToolParameter:
    def test_required_default(self):
        p = ToolParameter(name="input", type_hint="str")
        assert p.required is True

    def test_optional_parameter(self):
        p = ToolParameter(name="verbose", type_hint="bool", required=False, default="False")
        assert not p.required
        assert p.default == "False"


class TestEnums:
    def test_tool_category_values(self):
        assert ToolCategory.FILE == "file"
        assert ToolCategory.WEB == "web"
        assert ToolCategory.SHELL == "shell"
        assert ToolCategory.GIT == "git"

    def test_tool_permission_values(self):
        assert ToolPermission.READ_ONLY == "read_only"
        assert ToolPermission.EXECUTE == "execute"

    def test_tool_risk_values(self):
        assert ToolRisk.LOW == "low"
        assert ToolRisk.CRITICAL == "critical"
