"""Test agent loop and hooks."""

import asyncio

from lyra_cli.agent import (
    AgentState,
    BaseAgentHook,
    Checkpointer,
    RunContext,
    run_agent_loop,
)
from lyra_cli.cli.messages import UserMessage


class TestHook(BaseAgentHook):
    """Test hook that tracks calls."""

    def __init__(self):
        self.calls = []

    async def before_agent(self, ctx: RunContext, state: AgentState):
        self.calls.append("before_agent")

    async def after_agent(self, ctx, state, last_msg):
        self.calls.append("after_agent")


async def test_agent_loop():
    """Test basic agent loop execution."""
    print("Testing agent loop...")

    # Create initial messages
    messages = [UserMessage(content="Hello, agent!")]

    # Create test hook
    hook = TestHook()

    # Create checkpointer
    checkpointer = Checkpointer()

    # Run agent loop
    config = {
        "max_iterations": 1,
        "agent_name": "test-agent",
        "session_id": "test-session",
    }

    result_messages = await run_agent_loop(
        messages=messages,
        system_prompt="You are a helpful assistant.",
        hooks=[hook],
        checkpointer=checkpointer,
        config=config,
    )

    # Verify results
    assert len(result_messages) > 1, "Should have response message"
    assert "before_agent" in hook.calls, "before_agent hook should be called"
    assert "after_agent" in hook.calls, "after_agent hook should be called"

    print("✓ Agent loop test passed")
    print(f"  Messages: {len(result_messages)}")
    print(f"  Hook calls: {hook.calls}")


if __name__ == "__main__":
    asyncio.run(test_agent_loop())
