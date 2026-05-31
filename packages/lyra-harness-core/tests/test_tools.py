import pytest
from lyra_harness_core.messages import ToolCall
from lyra_harness_core.tools import (
    RiskLevel,
    ToolAnnotation,
    ToolCategory,
    ToolPermissionGate,
    ToolRegistry,
)
from lyra_harness_core.tools_builtin import CalculatorTool, EchoTool


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


# ---------------------------------------------------------------------------
# ToolAnnotation
# ---------------------------------------------------------------------------


def test_annotation_defaults():
    ann = ToolAnnotation()
    assert ann.read_only is False
    assert ann.requires_approval is True
    assert ann.sandboxed is False
    assert ann.network_access is False
    assert ann.mutates_filesystem is False
    assert ann.mutates_state is False
    assert ann.risk_level == RiskLevel.LOW
    assert ann.category == ToolCategory.ANALYSIS
    assert ann.tags == ()


def test_annotation_custom():
    ann = ToolAnnotation(
        read_only=True,
        requires_approval=False,
        sandboxed=True,
        risk_level=RiskLevel.HIGH,
        category=ToolCategory.FILE,
        tags=("filesystem", "read"),
    )
    assert ann.read_only is True
    assert ann.requires_approval is False
    assert ann.sandboxed is True
    assert ann.risk_level == RiskLevel.HIGH
    assert ann.category == ToolCategory.FILE
    assert ann.tags == ("filesystem", "read")


def test_annotation_is_frozen():
    ann = ToolAnnotation()
    with pytest.raises(Exception):
        ann.risk_level = RiskLevel.CRITICAL  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tool properties (is_read_only, is_destructive, needs_approval)
# ---------------------------------------------------------------------------


def test_tool_default_annotations():
    """A tool without explicit annotations gets the safe defaults."""
    tool = EchoTool()
    assert tool.is_read_only is False
    assert tool.is_destructive is False
    assert tool.needs_approval is True


def test_tool_destructive_detection():
    """HIGH and CRITICAL risk tools are destructive."""

    class DestructiveTool(EchoTool):
        annotations = ToolAnnotation(risk_level=RiskLevel.HIGH)

    assert DestructiveTool().is_destructive is True

    class CriticalTool(EchoTool):
        annotations = ToolAnnotation(risk_level=RiskLevel.CRITICAL)

    assert CriticalTool().is_destructive is True


# ---------------------------------------------------------------------------
# ToolPermissionGate
# ---------------------------------------------------------------------------


class ReadOnlyTool(EchoTool):
    annotations = ToolAnnotation(read_only=True, risk_level=RiskLevel.LOW)


class WriteTool(EchoTool):
    annotations = ToolAnnotation(
        mutates_filesystem=True, risk_level=RiskLevel.MEDIUM
    )


class DestructiveTool(EchoTool):
    annotations = ToolAnnotation(risk_level=RiskLevel.HIGH)


class CriticalTool(EchoTool):
    annotations = ToolAnnotation(risk_level=RiskLevel.CRITICAL)


def test_permission_gate_default_allows_read_only():
    gate = ToolPermissionGate(mode="default")
    allowed, reason = gate.can_execute(ReadOnlyTool())
    assert allowed
    assert "read-only" in reason


def test_permission_gate_default_allows_low_risk():
    gate = ToolPermissionGate(mode="default")
    allowed, _ = gate.can_execute(EchoTool())  # LOW risk
    assert allowed


def test_permission_gate_default_blocks_medium_write():
    gate = ToolPermissionGate(mode="default")
    allowed, reason = gate.can_execute(WriteTool())
    assert not allowed
    assert "requires approval" in reason


def test_permission_gate_default_blocks_high():
    gate = ToolPermissionGate(mode="default")
    allowed, _ = gate.can_execute(DestructiveTool())
    assert not allowed


def test_permission_gate_blocks_critical_in_all_modes_except_bypass():
    # plan mode blocks everything (before risk check), so critical is blocked
    gate = ToolPermissionGate(mode="plan")
    allowed, _ = gate.can_execute(CriticalTool())
    assert not allowed

    # default and accept_edits explicitly block critical
    for mode in ("default", "accept_edits"):
        gate = ToolPermissionGate(mode=mode)
        allowed, reason = gate.can_execute(CriticalTool())
        assert not allowed, f"mode={mode} should block critical"
        assert "critical" in reason


def test_permission_gate_bypass_allows_everything():
    gate = ToolPermissionGate(mode="bypass")
    for tool in (ReadOnlyTool(), WriteTool(), DestructiveTool(), CriticalTool()):
        allowed, _ = gate.can_execute(tool)
        assert allowed, f"bypass should allow {tool.__class__.__name__}"


def test_permission_gate_plan_denies_all():
    gate = ToolPermissionGate(mode="plan")
    for tool in (ReadOnlyTool(), EchoTool(), WriteTool()):
        allowed, reason = gate.can_execute(tool)
        assert not allowed
        assert "plan mode" in reason


def test_permission_gate_accept_edits_allows_non_destructive():
    gate = ToolPermissionGate(mode="accept_edits")
    for tool in (ReadOnlyTool(), EchoTool(), WriteTool()):
        allowed, _ = gate.can_execute(tool)
        assert allowed, f"accept_edits should allow {tool.__class__.__name__}"


def test_permission_gate_accept_edits_blocks_destructive():
    gate = ToolPermissionGate(mode="accept_edits")
    allowed, _ = gate.can_execute(DestructiveTool())
    assert not allowed


# ---------------------------------------------------------------------------
# ToolRegistry — names_by_category & names_by_risk
# ---------------------------------------------------------------------------


def test_names_by_category():
    reg = ToolRegistry()
    reg.register(EchoTool())  # default ANALYSIS
    reg.register(CalculatorTool())  # default ANALYSIS

    class FileReader(EchoTool):
        name = "file_reader"
        annotations = ToolAnnotation(
            read_only=True, category=ToolCategory.FILE
        )

    reg.register(FileReader())

    analysis = reg.names_by_category(ToolCategory.ANALYSIS)
    assert "echo" in analysis
    assert "calculator" in analysis
    assert "file_reader" not in analysis

    file_tools = reg.names_by_category(ToolCategory.FILE)
    assert file_tools == ["file_reader"]


def test_names_by_risk():
    reg = ToolRegistry()
    reg.register(EchoTool())  # LOW

    class RiskyTool(EchoTool):
        name = "risky"
        annotations = ToolAnnotation(risk_level=RiskLevel.MEDIUM)

    reg.register(RiskyTool())

    low = reg.names_by_risk(RiskLevel.LOW)
    assert "echo" in low
    assert "risky" not in low

    medium = reg.names_by_risk(RiskLevel.MEDIUM)
    assert "echo" in medium
    assert "risky" in medium


# ---------------------------------------------------------------------------
# ToolRegistry — permission-gated execute
# ---------------------------------------------------------------------------


def test_execute_with_permission_gate_allows_safe_tool():
    reg = ToolRegistry()
    reg.register(EchoTool())
    gate = ToolPermissionGate(mode="default")

    result = reg.execute(
        ToolCall(id="c1", name="echo", args={"text": "hello"}),
        permission_gate=gate,
    )
    assert not result.is_error
    assert result.content == "hello"


def test_execute_with_permission_gate_blocks_unsafe_tool():
    reg = ToolRegistry()
    reg.register(WriteTool())
    gate = ToolPermissionGate(mode="default")

    result = reg.execute(
        ToolCall(id="c1", name="echo", args={"text": "x"}),
        permission_gate=gate,
    )
    assert result.is_error
    assert "Permission denied" in result.content


def test_execute_with_bypass_allows_everything():
    reg = ToolRegistry()
    reg.register(DestructiveTool())
    gate = ToolPermissionGate(mode="bypass")

    result = reg.execute(
        ToolCall(id="c1", name="echo", args={"text": "x"}),
        permission_gate=gate,
    )
    assert not result.is_error


def test_to_schema_includes_annotations_for_non_low_risk():
    """Tools with non-LOW risk emit annotation metadata in their schema."""

    class AnnotatedTool(EchoTool):
        name = "annotated"
        annotations = ToolAnnotation(
            read_only=True,
            risk_level=RiskLevel.MEDIUM,
            requires_approval=True,
        )

    tool = AnnotatedTool()
    schema = tool.to_schema()
    assert schema["name"] == "annotated"
    assert "annotations" in schema
    assert schema["annotations"]["read_only"] is True
    assert schema["annotations"]["risk_level"] == "medium"


def test_to_schema_omits_annotations_for_low_risk():
    """LOW-risk tools do not include annotations in schema (default behavior)."""
    schema = EchoTool().to_schema()
    assert "annotations" not in schema
