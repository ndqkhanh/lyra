"""
Agent Loop v2 — real execution (not simulated).

Replaces asyncio.sleep() with actual LLM calls, tool dispatch, memory
operations, and hook integration.
"""

from src.agent_loop.executor import AgentLoopExecutor

__all__ = [
    "AgentLoopExecutor",
]
