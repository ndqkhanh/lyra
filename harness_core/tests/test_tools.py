import pytest

from harness_core.messages import ToolCall
from harness_core.tools import ToolRegistry
from harness_core.tools_builtin import CalculatorTool, EchoTool


@pytest.fixture
def registry():
    r = ToolRegistry()
    r.register(EchoTool())
    r.register(CalculatorTool())
    return r


def test_registry_register_and_names(registry):
    assert registry.names() == ["calculator", "echo"]
    assert registry.get("echo") is not None


def test_registry_rejects_duplicate_registration(registry):
    with pytest.raises(ValueError, match="already registered"):
        registry.register(EchoTool())


def test_registry_schemas_include_all_tools(registry):
    schemas = registry.schemas()
    names = sorted(s["name"] for s in schemas)
    assert names == ["calculator", "echo"]
    assert all("input_schema" in s for s in schemas)


def test_registry_schemas_can_be_filtered(registry):
    schemas = registry.schemas(allowed={"echo"})
    assert [s["name"] for s in schemas] == ["echo"]


def test_echo_tool_roundtrips():
    registry = ToolRegistry()
    registry.register(EchoTool())
    result = registry.execute(ToolCall(id="c1", name="echo", args={"text": "hi"}))
    assert result.content == "hi"
    assert not result.is_error


def test_calculator_rejects_arbitrary_code():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    result = registry.execute(
        ToolCall(id="c1", name="calculator", args={"expression": "__import__('os')"})
    )
    assert result.is_error
    assert "disallowed" in result.content


def test_calculator_evaluates_math():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    result = registry.execute(
        ToolCall(id="c1", name="calculator", args={"expression": "(2+3)*4"})
    )
    assert result.content == "20"


def test_validation_error_returns_is_error(registry):
    # echo requires `text`; give it something else
    result = registry.execute(ToolCall(id="c1", name="echo", args={"wrong": "x"}))
    assert result.is_error
    assert "validation failed" in result.content


def test_unknown_tool_returns_is_error(registry):
    result = registry.execute(ToolCall(id="c1", name="nope", args={}))
    assert result.is_error
    assert "Unknown tool" in result.content
