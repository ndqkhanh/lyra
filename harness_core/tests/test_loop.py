"""End-to-end tests of the agent loop with scripted MockLLM."""
from harness_core.hooks import Hook, HookDecision, HookEvent, HookRegistry
from harness_core.loop import AgentLoop, auto_approve
from harness_core.models import MockLLM
from harness_core.permissions import PermissionMode
from harness_core.tools import ToolRegistry
from harness_core.tools_builtin import CalculatorTool, EchoTool


def _registry():
    r = ToolRegistry()
    r.register(EchoTool())
    r.register(CalculatorTool())
    return r


def test_loop_completes_with_no_tools():
    llm = MockLLM(scripted_outputs=["hello"])
    loop = AgentLoop(llm=llm, tools=_registry())
    result = loop.run("say hi")
    assert result.final_text == "hello"
    assert result.stop_reason == "StopReason.END_TURN"
    assert result.tool_calls_count == 0


def test_loop_executes_tool_and_continues():
    llm = MockLLM(
        scripted_outputs=[
            {"text": "", "tool_calls": [{"name": "calculator", "args": {"expression": "1+1"}}]},
            "result is 2",
        ]
    )
    loop = AgentLoop(llm=llm, tools=_registry())
    result = loop.run("what's 1+1")
    assert result.final_text == "result is 2"
    assert result.tool_calls_count == 1


def test_loop_stops_at_max_steps():
    # script that never terminates normally — each turn asks for another tool
    llm = MockLLM(
        scripted_outputs=[
            {"text": "", "tool_calls": [{"name": "echo", "args": {"text": "x"}}]}
        ]
        * 25  # more than max_steps default of 20
    )
    loop = AgentLoop(llm=llm, tools=_registry(), max_steps=5)
    result = loop.run("loop forever")
    assert result.stop_reason == "max_steps"
    assert result.steps == 5


def test_plan_mode_blocks_writes_but_script_still_completes():
    # EchoTool is read-only (writes=False), but we'll simulate a write tool here by
    # using a tool whose writes=True. Calculator/Echo are both reads so test behavior
    # by forcing denial via a deny rule.
    from harness_core.permissions import PermissionPolicy

    llm = MockLLM(
        scripted_outputs=[
            {"text": "", "tool_calls": [{"name": "calculator", "args": {"expression": "1"}}]},
            "done",
        ]
    )
    policy = PermissionPolicy(deny=["calculator"])
    loop = AgentLoop(llm=llm, tools=_registry(), policy=policy)
    result = loop.run("calc")
    assert result.blocked_calls_count == 1
    # the tool result was "blocked by policy", conversation still ends cleanly
    assert result.final_text == "done"


def test_approval_rejection_blocks_call():
    llm = MockLLM(
        scripted_outputs=[
            {"text": "", "tool_calls": [{"name": "calculator", "args": {"expression": "1"}}]},
            "done",
        ]
    )
    from harness_core.permissions import PermissionPolicy

    # force this call to "ask" via policy
    policy = PermissionPolicy(ask=["calculator"])

    def always_reject(_call):
        return False

    loop = AgentLoop(
        llm=llm,
        tools=_registry(),
        policy=policy,
        approval=always_reject,
    )
    result = loop.run("calc")
    assert result.blocked_calls_count == 1


def test_hook_can_block_tool():
    def deny_echo(call, result):
        if call.name == "echo":
            return HookDecision(block=True, reason="echo forbidden")
        return HookDecision()

    hooks = HookRegistry()
    hooks.register(Hook("deny-echo", HookEvent.PRE_TOOL_USE, matcher="*", handler=deny_echo))

    llm = MockLLM(
        scripted_outputs=[
            {"text": "", "tool_calls": [{"name": "echo", "args": {"text": "hi"}}]},
            "wrapped up",
        ]
    )
    loop = AgentLoop(llm=llm, tools=_registry(), hooks=hooks)
    result = loop.run("hi")
    assert result.blocked_calls_count == 1


def test_post_hook_annotates_result():
    def add_suffix(call, result):
        return HookDecision(annotation="[validated]")

    hooks = HookRegistry()
    hooks.register(Hook("annotate", HookEvent.POST_TOOL_USE, matcher="*", handler=add_suffix))

    llm = MockLLM(
        scripted_outputs=[
            {"text": "", "tool_calls": [{"name": "echo", "args": {"text": "hi"}}]},
            "bye",
        ]
    )
    loop = AgentLoop(llm=llm, tools=_registry(), hooks=hooks)
    result = loop.run("hi")
    # transcript's tool message should carry the annotation
    tool_msg = next(m for m in result.transcript if m.role == "tool")
    assert "[hook] [validated]" in tool_msg.tool_results[0].content


def test_default_approval_is_auto_allow():
    assert auto_approve(None) is True  # type: ignore[arg-type]


def test_permission_mode_plan_denies_destructive_in_loop():
    """Plan mode + a write=True tool should result in blocking."""
    from pydantic import BaseModel
    from harness_core.tools import Tool

    class WriteTool(Tool):
        name = "write"
        description = "writes"
        writes = True

        class ArgsModel(BaseModel):
            data: str

        def run(self, args):
            return "wrote"

    reg = ToolRegistry()
    reg.register(WriteTool())

    llm = MockLLM(
        scripted_outputs=[
            {"text": "", "tool_calls": [{"name": "write", "args": {"data": "x"}}]},
            "done",
        ]
    )
    loop = AgentLoop(llm=llm, tools=reg, permission_mode=PermissionMode.PLAN)
    result = loop.run("plan something")
    assert result.blocked_calls_count == 1
