from harness_core.hooks import Hook, HookDecision, HookEvent, HookRegistry
from harness_core.messages import ToolCall


def test_hook_fires_on_event():
    fired = []

    def handler(call, result):
        fired.append(call.name)
        return HookDecision()

    r = HookRegistry()
    r.register(Hook("log", HookEvent.PRE_TOOL_USE, matcher="*", handler=handler))
    r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="foo"))
    assert fired == ["foo"]


def test_hook_matcher_filters_by_tool_name():
    fired = []

    def handler(call, result):
        fired.append(call.name)
        return HookDecision()

    r = HookRegistry()
    r.register(Hook("only-edit", HookEvent.PRE_TOOL_USE, matcher="edit", handler=handler))

    r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="read"))
    r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c2", name="edit"))
    assert fired == ["edit"]


def test_hook_can_block():
    def deny(call, result):
        return HookDecision(block=True, reason="not allowed")

    r = HookRegistry()
    r.register(Hook("deny", HookEvent.PRE_TOOL_USE, matcher="*", handler=deny))
    d = r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="foo"))
    assert d.block is True
    assert "not allowed" in d.reason


def test_registering_hook_without_handler_raises():
    r = HookRegistry()
    try:
        r.register(Hook("bad", HookEvent.PRE_TOOL_USE))
    except ValueError as e:
        assert "no handler" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_hook_event_is_scoped():
    calls = []

    def h(call, result):
        calls.append(call.name)
        return HookDecision()

    r = HookRegistry()
    r.register(Hook("post", HookEvent.POST_TOOL_USE, matcher="*", handler=h))

    r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="x"))  # wrong event
    r.run(HookEvent.POST_TOOL_USE, ToolCall(id="c2", name="x"))
    assert calls == ["x"]
