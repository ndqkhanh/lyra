from harness_core.messages import Message, StopReason, ToolCall, ToolResult


def test_message_constructors_are_ergonomic():
    assert Message.system("hi").role == "system"
    assert Message.user("q").content == "q"
    tc = ToolCall(id="c1", name="x", args={"a": 1})
    m = Message.assistant("thinking", tool_calls=[tc], stop_reason=StopReason.TOOL_USE)
    assert m.has_tool_calls()
    assert m.tool_calls[0].name == "x"
    assert m.stop_reason == StopReason.TOOL_USE


def test_tool_message_carries_results():
    r = ToolResult(call_id="c1", content="ok")
    m = Message.tool([r])
    assert m.role == "tool"
    assert m.tool_results[0].content == "ok"
    assert not m.has_tool_calls()


def test_stop_reason_is_string_enum():
    assert StopReason.END_TURN.value == "end_turn"
    assert StopReason("tool_use") == StopReason.TOOL_USE
