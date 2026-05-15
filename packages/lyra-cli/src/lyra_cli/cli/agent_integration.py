"""Agent Loop Integration for Lyra TUI.

Connects the TUI to actual LLM providers with streaming output.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from lyra_core.agent import AgentLoop
from lyra_core.tools import ToolKernel


class TUIAgentIntegration:
    """Integrates AgentLoop with TUI."""

    def __init__(self, model: str, repo_root, budget_cap_usd: float | None = None):
        self.model = model
        self.repo_root = repo_root
        self.budget_cap_usd = budget_cap_usd
        self._agent_loop = None

    async def initialize(self):
        """Initialize agent loop."""
        from lyra_cli.llm_factory import build_llm_auto

        # Build LLM provider
        llm = build_llm_auto(model_hint=self.model)

        # Initialize tool kernel
        tool_kernel = ToolKernel(repo_root=self.repo_root)

        # Create agent loop
        self._agent_loop = AgentLoop(
            llm=llm,
            tool_kernel=tool_kernel,
            budget_cap_usd=self.budget_cap_usd,
        )

    async def run_agent(
        self, user_input: str
    ) -> AsyncIterator[dict]:
        """Run agent with streaming output.

        Yields:
            dict with keys:
                - type: "text" | "tool" | "done"
                - content: str
                - metadata: dict (optional)
        """
        if not self._agent_loop:
            await self.initialize()

        async for event in self._agent_loop.run_streaming(user_input):
            if event["type"] == "text_delta":
                yield {
                    "type": "text",
                    "content": event["delta"],
                }
            elif event["type"] == "tool_use":
                yield {
                    "type": "tool",
                    "content": f"[Using {event['tool_name']}...]",
                    "metadata": event,
                }
            elif event["type"] == "tool_result":
                yield {
                    "type": "tool",
                    "content": " done",
                    "metadata": event,
                }
            elif event["type"] == "usage":
                yield {
                    "type": "usage",
                    "content": "",
                    "metadata": event,
                }

    def get_usage_stats(self) -> dict:
        """Get usage statistics."""
        if not self._agent_loop:
            return {
                "total_tokens": 0,
                "total_cost": 0.0,
                "context_tokens": 0,
            }

        return {
            "total_tokens": self._agent_loop.total_tokens,
            "total_cost": self._agent_loop.total_cost,
            "context_tokens": self._agent_loop.context_tokens,
        }
